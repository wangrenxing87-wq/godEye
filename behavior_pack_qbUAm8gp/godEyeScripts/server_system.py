# -*- coding: utf-8 -*-
from __future__ import division
import math
import time
import traceback
import mod.server.extraServerApi as serverApi
from godEyeScripts import config, core
from godEyeScripts.effects import NightVisionLease
from godEyeScripts.scanner import TileReader

ServerSystem = serverApi.GetServerSystemCls()


class GodEyeServer(ServerSystem):
    def __init__(self, namespace, system_name):
        ServerSystem.__init__(self, namespace, system_name)
        self.level_id = serverApi.GetLevelId()
        self.factory = serverApi.GetEngineCompFactory()
        self.game = self.factory.CreateGame(self.level_id)
        self.block = self.factory.CreateBlock(self.level_id)
        self.block_info = self.factory.CreateBlockInfo(self.level_id)
        self.chunks = self.factory.CreateChunkSource(self.level_id)
        self.players = {}
        self.scan = core.ScanCache()
        self.registry = core.TargetRegistry()
        self.catalog = dict((k, dict(v)) for k, v in config.BLOCKS.items())
        self.reader = TileReader(self.block, self.block_info, self.chunks, self.catalog)
        self.dimension_bounds = dict(config.DIMENSION_BOUNDS)
        self.entity_types = dict(config.ENTITY_TYPES)
        self.tick = 0
        self.player_cursor = 0
        self.dirty = set()
        self.errors = {}
        self._listen()
        print("[GodEye][Server] initialized " + config.VERSION)

    def _listen(self):
        for name, handler in (
                ("AddServerPlayerEvent", self.on_join),
                ("DelServerPlayerEvent", self.on_leave),
                ("PlayerRespawnFinishServerEvent", self.on_restore),
                ("DimensionChangeFinishServerEvent", self.on_restore),
                ("ServerChatEvent", self.on_chat),
                ("AddEffectServerEvent", self.on_effect),
                ("RefreshEffectServerEvent", self.on_effect),
                ("RemoveEffectServerEvent", self.on_effect_removed),
                ("ServerPlayerTryDestroyBlockEvent", self.on_block),
                ("EntityPlaceBlockAfterServerEvent", self.on_block)):
            self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), name, self, handler)
        self.ListenForEvent(config.NAMESPACE, config.CLIENT_SYSTEM,
                            config.REQUEST_EVENT, self, self.on_request)

    def _error(self, operation):
        if self.tick - self.errors.get(operation, -300) >= 300:
            self.errors[operation] = self.tick
            print("[GodEye][Server] " + operation + "\n" + traceback.format_exc())

    def _player(self, player):
        if player not in self.players:
            extra = self.factory.CreateExtraData(player)
            saved = extra.GetExtraData(config.DATA_KEY)
            lease = NightVisionLease(self.factory.CreateEffect(player), clock=lambda: self.tick / 30.0,
                                     save=lambda value: extra.SetExtraData(config.EFFECT_DATA_KEY, value))
            lease.restore(extra.GetExtraData(config.EFFECT_DATA_KEY))
            self.players[player] = {
                "settings": core.settings(saved), "extra": extra, "revision": 1,
                "lease": lease,
                "pos_comp": self.factory.CreatePos(player),
                "rot_comp": self.factory.CreateRot(player),
                "dim_comp": self.factory.CreateDimension(player),
                "attr_comp": self.factory.CreateAttr(player),
                "dimension": None, "ready": False, "request_tick": -30,
                "last_scan": -30, "entity_cursor": 0, "entities": {},
                "last_light": -1, "dirty_settings": False,
            }
        return self.players[player]

    def on_join(self, args):
        # Player data is read on the ready handshake, when the entity is valid.
        pass

    def on_leave(self, args):
        player = args.get("id")
        self.scan.unwatch(player)
        # Keep the ownership signature written when the effect was applied.
        # A shorter shutdown checkpoint can precede/follow the engine snapshot
        # in either order and must not replace the original duration signature.
        self.players.pop(player, None)

    def on_restore(self, args):
        player = args.get("playerId")
        if player not in self.players:
            return
        state = self.players[player]
        state["revision"] += 1
        state["dimension"] = None
        state["entities"].clear()
        self.scan.unwatch(player)
        state["last_scan"] = -30
        self._sync(player)

    def on_request(self, args):
        # __id__ is injected by ModSDK; never trust a payload playerId.
        player = args.get("__id__")
        if player not in serverApi.GetPlayerList():
            return
        try:
            state = self._player(player)
            if self.tick - state["request_tick"] < config.REQUEST_INTERVAL_TICKS:
                self._sync(player, u"操作较快，请稍后重试。")
                return
            state["request_tick"] = self.tick
            state["ready"] = True
            if args.get("action") == "apply":
                candidate = args.get("settings")
                if not isinstance(candidate, dict) or type(candidate.get("level")) not in core.INTEGER_TYPES or not 0 <= candidate["level"] <= 6:
                    self._sync(player, u"设置无效，请重新选择。")
                    return
                value = core.settings(candidate)
                if not state["extra"].SetExtraData(config.DATA_KEY, value):
                    self._sync(player, u"设置保存失败，请重试。")
                    return
                state["settings"] = value
                state["revision"] += 1
                state["entities"].clear()
                self.scan.unwatch(player)
                state["last_scan"] = -30
                if not core.capabilities(value)["night"]:
                    state["lease"].release()
            self._sync(player)
            self._maintain(player)
        except Exception:
            self._error("request")

    def _sync(self, player, error=None):
        state = self.players[player]
        if not state["ready"]:
            return
        dimension = state["dim_comp"].GetEntityDimensionId()
        self.NotifyToClient(player, config.STATE_EVENT, {
            "settings": dict(state["settings"]), "revision": state["revision"],
            "dimension": dimension, "error": error,
        })

    def on_chat(self, args):
        message = core.display_text(args.get("message", "")).strip().lower()
        if message == u">天眼归位":
            args["cancel"] = True
            self.NotifyToClient(args["playerId"], config.UI_EVENT, {"action": "toggle_entry"})
        elif message in ("!godeye", u"天眼"):
            args["cancel"] = True
            self.NotifyToClient(args["playerId"], config.UI_EVENT, {})

    def on_effect(self, args):
        state = self.players.get(args.get("entityId"))
        if state and args.get("effectName") == "night_vision":
            state["lease"].observe(args.get("effectDuration", 0), args.get("effectAmplifier", 0))

    def on_effect_removed(self, args):
        state = self.players.get(args.get("entityId"))
        if state and args.get("effectName") == "night_vision":
            state["lease"].removed()

    def on_block(self, args):
        if all(k in args for k in ("dimensionId", "x", "y", "z")):
            self.dirty.add(core.tile_key(args["dimensionId"], (args["x"], args["y"], args["z"])))

    def _maintain(self, player):
        state = self.players[player]
        health = state["attr_comp"].GetAttrValue(serverApi.GetMinecraftEnum().AttrType.HEALTH)
        if health is None or health <= 0:
            self.scan.unwatch(player)
            return
        if core.capabilities(state["settings"])["night"]:
            state["lease"].maintain()

    def _read_tile(self, key):
        return self.reader.read(key)

    def _entities(self, player, state, pos, dimension, caps):
        if not (caps["entities"] or caps["hidden"]):
            state["entities"].clear()
            return []
        ids = sorted(self.game.GetEntitiesAround(player, caps["entity_radius"], {}) or [])
        seen = set(ids)
        if ids:
            for offset in range(min(config.MAX_ENTITY_CHECKS, len(ids))):
                entity = ids[(state["entity_cursor"] + offset) % len(ids)]
                if entity == player:
                    continue
                point = self.factory.CreatePos(entity).GetFootPos()
                if not core.valid_pos(point) or core.distance2(pos, point) > caps["entity_radius"] ** 2:
                    state["entities"].pop(entity, None)
                    continue
                if self.factory.CreateDimension(entity).GetEntityDimensionId() != dimension:
                    continue
                kind = self.factory.CreateEngineType(entity).GetEngineTypeStr()
                tags = self.factory.CreateTag(entity).GetEntityTags() or []
                categories = [config.TAG_CATEGORIES[t] for t in tags if t in config.TAG_CATEGORIES]
                category = None
                if caps["hidden"]:
                    for candidate in ("quest", "hidden", "container", "mechanism", "entrance"):
                        if candidate in categories:
                            category = candidate
                            break
                if category is None and caps["entities"]:
                    if "spirit" in categories:
                        category = "spirit"
                    elif "special" in categories or "hidden" in categories or kind in self.entity_types:
                        category = "special"
                    else:
                        effects = self.factory.CreateEffect(entity).GetAllEffects() or []
                        if any(e.get("effectName") == "invisibility" for e in effects):
                            category = "special"
                if category:
                    label = (self.factory.CreateName(entity).GetName() or self.entity_types.get(kind)
                             or config.CATEGORY_LABELS[category])
                    state["entities"][entity] = (self.tick, {
                        "id": "entity:" + entity, "category": category,
                        "label": core.display_text(label), "pos": list(point), "entityId": entity,
                    })
                else:
                    state["entities"].pop(entity, None)
            state["entity_cursor"] = (state["entity_cursor"] + config.MAX_ENTITY_CHECKS) % len(ids)
        for entity, item in list(state["entities"].items()):
            if entity not in seen or self.tick - item[0] > 90:
                del state["entities"][entity]
        return [dict(item[1]) for item in state["entities"].values()]

    def _scan_player(self, player):
        state = self.players[player]
        value = state["settings"]
        caps = core.capabilities(value)
        point = state["pos_comp"].GetFootPos()
        if not core.valid_pos(point):
            return
        dimension = state["dim_comp"].GetEntityDimensionId()
        if state["dimension"] != dimension:
            if state["dimension"] is not None:
                state["revision"] += 1
            state["dimension"] = dimension
            state["entities"].clear()
            self.scan.unwatch(player)
            self._sync(player)
        health = state["attr_comp"].GetAttrValue(serverApi.GetMinecraftEnum().AttrType.HEALTH)
        if health is None or health <= 0:
            self.scan.unwatch(player)
            self.NotifyToClient(player, config.TARGET_EVENT, {
                "revision": state["revision"], "dimension": dimension,
                "targets": [], "complete": 0, "total": 0, "light": 15, "dead": True})
            return
        light = 15
        if caps["enhance"]:
            block_pos = tuple(int(math.floor(v)) for v in point)
            measured = self.block_info.GetBlockLightLevel(block_pos, dimension)
            if isinstance(measured, core.INTEGER_TYPES):
                light = max(0, min(15, measured))
        total = complete = 0
        targets, truncated = [], False
        if caps["ore"] or caps["hidden"]:
            self.scan.watch(player, dimension, point, caps["radius"], self.dimension_bounds.get(dimension))
            blocks, complete, total, truncated = self.scan.snapshot(player, point, caps["radius"])
            targets = core.group_blocks(blocks, self.catalog, point, caps["ore"], caps["hidden"])
        else:
            self.scan.unwatch(player)
        targets.extend(self._entities(player, state, point, dimension, caps))
        if caps["entities"] or caps["hidden"] or caps["ore"]:
            targets.extend(self.registry.query(player, dimension, point, caps["radius"]))
        targets.sort(key=lambda item: (core.distance2(item["pos"], point), item["id"]))
        rotation = state["rot_comp"].GetRot() or (0, 0)
        self.NotifyToClient(player, config.TARGET_EVENT, {
            "revision": state["revision"], "dimension": dimension,
            "targets": core.public_targets(targets, value, point, rotation[1]),
            "complete": complete, "total": total, "truncated": truncated,
            "light": light, "dead": False,
        })

    def Update(self):
        self.tick += 1
        for key in self.dirty:
            self.scan.cache.pop(key, None)
            self.scan.failed_until.pop(key, None)
            self.reader.invalidate(key)
        self.dirty.clear()
        if self.tick % 30 == 0:
            self.reader.retain(k for keys in self.scan.interests.values() for k in keys)
        players = [p for p, state in self.players.items() if state["ready"]]
        if self.tick % config.EFFECT_CHECK_TICKS == 0:
            for player in players:
                try:
                    self._maintain(player)
                except Exception:
                    self._error("effect")
        # At most one player's expensive queries per tick, each at most 2 Hz.
        if players:
            for _ in players:
                player = players[self.player_cursor % len(players)]
                self.player_cursor += 1
                state = self.players[player]
                if self.tick - state["last_scan"] < 15:
                    continue
                state["last_scan"] = self.tick
                if state["settings"]["level"] == 0:
                    continue
                try:
                    self._scan_player(player)
                except Exception:
                    self._error("scan_player")
                break
        if self.scan.interests:
            try:
                self.scan.pump(self._read_tile)
            except Exception:
                self._error("scan_tile")

    def RegisterTarget(self, target_id, category, dimension, pos, label, players=None, ttl=0):
        """Cross-mod API. Call from another server System via GetSystem."""
        self.registry.register(target_id, category, dimension, pos, label, players, ttl)
        return True

    def UnregisterTarget(self, target_id):
        return self.registry.unregister(target_id)

    def RegisterOre(self, block_id, label, rare=True, group=None):
        if not isinstance(block_id, core.STRING_TYPES) or ":" not in block_id:
            raise ValueError("Ore id must be namespaced")
        if not isinstance(label, core.STRING_TYPES) or not 1 <= len(label) <= 80:
            raise ValueError("Invalid ore label")
        if len(self.catalog) >= 128 and block_id not in self.catalog:
            raise ValueError("Block catalog full")
        self.catalog[core.native_id(block_id)] = {"label": core.display_text(label), "rare": bool(rare),
                                                "category": "ore", "group": group or block_id}
        self.scan.cache.clear()
        return True

    def RegisterEntityType(self, entity_id, label):
        if not isinstance(entity_id, core.STRING_TYPES) or ":" not in entity_id or not isinstance(label, core.STRING_TYPES):
            raise ValueError("Invalid entity definition")
        self.entity_types[core.native_id(entity_id)] = core.display_text(label)
        return True

    def RegisterDimensionBounds(self, dimension_id, minimum, maximum):
        if any(type(v) not in core.INTEGER_TYPES for v in (dimension_id, minimum, maximum)) or minimum >= maximum:
            raise ValueError("Dimension bounds must be integers with minimum < maximum")
        if minimum % config.TILE_SIZE or maximum % config.TILE_SIZE:
            raise ValueError("Dimension bounds must align to 8-block sections")
        self.dimension_bounds[dimension_id] = (minimum, maximum)
        self.scan.cache.clear()
        return True

    def Destroy(self):
        self.UnListenAllEvents()
        self.players.clear()
        self.scan.clear()
        self.reader.retain([])
        self.registry.targets.clear()
