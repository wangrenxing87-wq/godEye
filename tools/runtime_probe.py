# -*- coding: utf-8 -*-
"""Isolated test-copy probe. NEVER placed in the shipping pack by build.py.

Commands and snapshots live under the explicitly substituted WORKSPACE_PATH.
This file is installed into the separate MC Studio validation component only.
"""
from __future__ import division
import json
import os
import time
import traceback
import mod.server.extraServerApi as serverApi
import mod.client.extraClientApi as clientApi
from godEyeScripts import config

WORKSPACE_PATH = r"C:\Apps\mercuryx\godEye"
DIRECTORY = os.path.join(WORKSPACE_PATH, ".runtime")


def write_snapshot(name, value):
    with open(os.path.join(DIRECTORY, "probe_" + name + ".json"), "w") as output:
        json.dump(value, output, ensure_ascii=True, indent=2)


def command_for(side):
    try:
        with open(os.path.join(DIRECTORY, "probe_command.json"), "r") as source:
            value = json.load(source)
        return value if value.get("side") == side else {}
    except (IOError, ValueError):
        return {}


class ServerProbe(serverApi.GetServerSystemCls()):
    def __init__(self, namespace, name):
        super(ServerProbe, self).__init__(namespace, name)
        self.tick = 0
        self.last_command = None
        self.command_result = None
        self.started = time.time()
        self.timings = []
        self.error = None
        self._instrumented = False
        self.initial_players = {}
        self.lease_trace = []

    def Update(self):
        self.tick += 1
        system = serverApi.GetSystem(config.NAMESPACE, config.SERVER_SYSTEM)
        if system is None:
            return
        if not self._instrumented:
            original = system._read_tile
            def read_tile(key):
                start = time.clock()
                try:
                    return original(key)
                finally:
                    self.timings.append((time.clock() - start) * 1000)
                    self.timings = self.timings[-1200:]
            system._read_tile = read_tile
            original_player = system._player
            def read_player(player):
                if player not in self.initial_players:
                    extra = system.factory.CreateExtraData(player)
                    self.initial_players[player] = {"tick": system.tick,
                        "saved": extra.GetExtraData(config.EFFECT_DATA_KEY),
                        "effect": system.factory.CreateEffect(player).GetAllEffects()}
                result = original_player(player)
                if "restored" not in self.initial_players[player]:
                    self.initial_players[player]["restored"] = result["lease"].export_state()
                    lease = result["lease"]
                    original_observe, original_maintain = lease.observe, lease.maintain
                    def record(kind, **args):
                        self.lease_trace.append(dict(args, kind=kind, tick=system.tick,
                            now=lease.clock(), until=lease.owned_until, writing=lease.writing,
                            current=lease.current(), owned=lease.export_state()))
                        self.lease_trace = self.lease_trace[-80:]
                    def observe(duration, amplifier):
                        record("observe", duration=duration, amplifier=amplifier)
                        original_observe(duration, amplifier)
                    def maintain():
                        record("maintain_before")
                        original_maintain()
                        record("maintain_after")
                    lease.observe, lease.maintain = observe, maintain
                return result
            system._player = read_player
            self._instrumented = True
        if self.tick % 15:
            return
        try:
            command = command_for("server")
            if command and command["id"] >= self.started and command["id"] != self.last_command:
                self.last_command = command["id"]
                self.error = None
                player = serverApi.GetPlayerList()[0]
                factory = serverApi.GetEngineCompFactory()
                operation = command.get("operation")
                if operation == "commands":
                    comp = factory.CreateCommand(serverApi.GetLevelId())
                    self.command_result = [comp.SetCommand(c.encode("utf-8"), player, True) for c in command["commands"]]
                elif operation == "entry_chat":
                    args = {"playerId": player, "message": u">天眼归位".encode("utf-8"), "cancel": False}
                    system.on_chat(args)
                    self.command_result = {"cancel": args["cancel"]}
                elif operation == "register":
                    point = factory.CreatePos(player).GetFootPos()
                    position = tuple(point[i] + command.get("offset", [3, 0, 3])[i] for i in range(3))
                    self.command_result = system.RegisterTarget(command.get("target_id", "godeye_test:quest"),
                        command.get("category", "quest"), factory.CreateDimension(player).GetEntityDimensionId(),
                        position, command.get("label", u"验收任务目标"),
                        [] if command.get("private_hidden") else [player], command.get("ttl", 0))
                elif operation == "unregister":
                    self.command_result = system.UnregisterTarget(command["target_id"])
                elif operation == "blocks":
                    info = factory.CreateBlockInfo(serverApi.GetLevelId())
                    dimension = factory.CreateDimension(player).GetEntityDimensionId()
                    self.command_result = [info.GetBlockNew(tuple(p), dimension) for p in command["positions"]]
                elif operation == "dimension":
                    self.command_result = factory.CreateDimension(player).ChangePlayerDimension(command["dimension"], tuple(command["pos"]))
                elif operation == "tag":
                    entities = factory.CreateGame(serverApi.GetLevelId()).GetEntitiesAround(player, 32, {}) or []
                    tagged = []
                    for entity in entities:
                        if factory.CreateEngineType(entity).GetEngineTypeStr() == command["kind"]:
                            factory.CreateTag(entity).AddEntityTag(command["tag"].encode("utf-8"))
                            tagged.append(entity)
                    self.command_result = tagged
                elif operation == "reset_timings":
                    self.timings = []
                    self.command_result = True
            players = {}
            for player, state in system.players.items():
                point = state["pos_comp"].GetFootPos()
                players[player] = {"settings": state["settings"], "revision": state["revision"],
                    "pos": point, "dimension": state["dim_comp"].GetEntityDimensionId(),
                    "effects": state["lease"].component.GetAllEffects(), "ready": state["ready"],
                    "health": state["attr_comp"].GetAttrValue(serverApi.GetMinecraftEnum().AttrType.HEALTH),
                    "lease": state["lease"].export_state(),
                    "saved_lease": state["extra"].GetExtraData(config.EFFECT_DATA_KEY),
                    "cache": len(system.scan.cache), "interests": len(system.scan.interests.get(player, [])),
                    "last_scan_cost_ms": system.scan.last_cost * 1000}
            timings = sorted(self.timings)
            write_snapshot("server", {"time": time.time(), "tick": self.tick, "players": players,
                "last_command": self.last_command, "command_result": self.command_result,
                "error": self.error, "runtime_errors": system.errors,
                "initial_players": self.initial_players,
                "lease_trace": self.lease_trace,
                "tile_count": len(timings), "tile_p95_ms": timings[int((len(timings)-1)*0.95)] if timings else None,
                "tile_max_ms": max(timings) if timings else None})
        except Exception:
            self.error = traceback.format_exc()
            write_snapshot("server", {"error": self.error, "last_command": self.last_command})


class ClientProbe(clientApi.GetClientSystemCls()):
    def __init__(self, namespace, name):
        super(ClientProbe, self).__init__(namespace, name)
        self.tick = 0
        self.last_command = None
        self.error = None
        self.started = time.time()
        self.command_result = None
        self.entry_events = []
        from godEyeScripts.ui import GodEyeHUD
        def trace(name):
            original = getattr(GodEyeHUD, name)
            def callback(hud, args):
                self.entry_events.append({"event": name, "args": dict(args)})
                self.entry_events = self.entry_events[-12:]
                return original(hud, args)
            return callback
        for name in ("on_entry_down", "on_entry_move", "on_entry_up", "on_entry_cancel"):
            setattr(GodEyeHUD, name, trace(name))

    def Update(self):
        self.tick += 1
        if self.tick % 15:
            return
        try:
            system = clientApi.GetSystem(config.NAMESPACE, config.CLIENT_SYSTEM)
            if system is None:
                return
            command = command_for("client")
            if command and command["id"] >= self.started and command["id"] != self.last_command:
                self.last_command = command["id"]
                self.error = None
                operation = command.get("operation")
                if operation == "apply":
                    value = dict(system.value)
                    value.update(command["settings"])
                    system.apply(value)
                elif operation == "menu":
                    system.open_menu()
                elif operation == "close":
                    if system.menu:
                        clientApi.PopScreen()
                elif operation == "entry_gesture":
                    for event in command["events"]:
                        callback = {"down": system.hud.on_entry_down, "move": system.hud.on_entry_move,
                                    "up": system.hud.on_entry_up, "cancel": system.hud.on_entry_cancel}[event[0]]
                        callback({"TouchPosX": event[1], "TouchPosY": event[2]})
                elif operation == "touch_mode":
                    self.command_result = system.game.SimulateTouchWithMouse(command["enabled"])
                elif operation == "view":
                    clientApi.GetEngineCompFactory().CreatePlayerView(clientApi.GetLocalPlayerId()).SetPerspective(command["perspective"])
                elif operation == "hud":
                    clientApi.HideHudGUI(command["hidden"])
                elif operation == "repair_ui":
                    existing = clientApi.GetUI(config.NAMESPACE, "hud")
                    self.command_result = {"existing": str(existing), "created": getattr(existing, "created", None)}
                    if existing:
                        system.hud = existing
                    else:
                        self.command_result["register"] = clientApi.RegisterUI(config.NAMESPACE, "hud", "godEyeScripts.ui.GodEyeHUD", "mercuryx_godeye.hud")
                        system.on_ui({})
            entry = system.hud.GetBaseUIControl("/root/entry") if system.hud else None
            write_snapshot("client", {"time": time.time(), "tick": self.tick,
                "entry_visible": system.entry_visible, "entry_relative": system.entry_position,
                "entry_events": self.entry_events,
                "entry_position": entry.GetPosition() if entry else None,
                "entry_size": entry.GetSize() if entry else None,
                "root_size": system.hud.GetBaseUIControl("/root").GetSize() if system.hud else None,
                "settings": system.value, "revision": system.revision, "dimension": system.dimension,
                "ready": system.ready, "hud": system.hud is not None, "menu": system.menu is not None,
                "engine_dimension": system.game.GetCurrentDimension(),
                "registered": system.registered, "get_ui": str(clientApi.GetUI(config.NAMESPACE, "hud")),
                "ui_created": getattr(clientApi.GetUI(config.NAMESPACE, "hud"), "created", None),
                "command_result": self.command_result,
                "targets": system.targets, "boards": len(system.boards), "light": system.light,
                "progress": system.progress, "dead": system.dead, "pending": system.pending,
                "visual_notice": system.visual_notice, "enhancement_owned": system.enhancement_owned,
                "enhancement_value": system.enhancement_value, "fps": system.game.GetFps(),
                "runtime_errors": system.errors, "error": self.error, "last_command": self.last_command})
        except Exception:
            self.error = traceback.format_exc()
            write_snapshot("client", {"error": self.error, "last_command": self.last_command})
