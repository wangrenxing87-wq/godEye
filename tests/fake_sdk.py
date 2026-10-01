# -*- coding: utf-8 -*-
"""Small documented ModSDK simulation; not a replacement for device testing."""
from __future__ import division
import copy
import json
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "behavior_pack_qbUAm8gp"))
from godEyeScripts import config


class Engine(object):
    def __init__(self):
        self.actors = {"p1": self.actor(), "p2": self.actor((10, 4, 4))}
        self.data = {}
        self.blocks = {}
        self.listeners = []
        self.messages = []
        self.systems = {}
        self.ui_defs = {}
        self.ui_nodes = []
        self.ui_stack = []
        self.local_player = "p1"
        self.dimension = 0
        self.now = 100.0
        self.next_board = 0
        self.boards = {}
        self.post_enabled = False
        self.post_values = {}
        self.fail_save = False
        self.palette_calls = 0
        self.entity_calls = 0
        self.light = 0
        self.screen_size = (640, 360)
        self.factory = Factory(self)

    @staticmethod
    def actor(pos=(4, 4, 4), kind="minecraft:player", tags=None):
        return {"pos": pos, "dimension": 0, "health": 20,
                "kind": kind, "tags": tags or [], "effects": {}, "name": "", "rot": (0, 0)}

    def emit(self, event, args):
        for _, _, name, instance, callback in list(self.listeners):
            if name == event:
                callback(dict(args))

    def tick(self, count=1):
        for _ in range(count):
            self.now += 1 / 30
            for system in list(self.systems.values()):
                system.Update()


ENGINE = None


class BaseSystem(object):
    def __init__(self, namespace, name):
        self.namespace, self.name = namespace, name
        ENGINE.systems[name] = self

    def ListenForEvent(self, namespace, system, event, instance, callback):
        ENGINE.listeners.append((namespace, system, event, instance, callback))

    def UnListenAllEvents(self):
        ENGINE.listeners[:] = [entry for entry in ENGINE.listeners if entry[3] is not self]

    def NotifyToClient(self, player, event, data):
        ENGINE.messages.append((player, event, copy.deepcopy(data)))
        if player == ENGINE.local_player:
            ENGINE.emit(event, data)

    def NotifyToServer(self, event, data):
        args = dict(data)
        args["__id__"] = ENGINE.local_player
        ENGINE.emit(event, args)


class Component(object):
    def __init__(self, engine, actor):
        self.engine, self.actor_id = engine, actor

    @property
    def actor(self): return self.engine.actors[self.actor_id]
    def GetFootPos(self): return self.actor["pos"]
    def GetRot(self): return self.actor["rot"]
    def GetEntityDimensionId(self): return self.actor["dimension"]
    def GetAttrValue(self, value): return self.actor["health"]
    def GetEngineTypeStr(self): return self.actor["kind"]
    def GetEntityTags(self): return list(self.actor["tags"])
    def GetName(self): return self.actor["name"]

    def GetExtraData(self, key):
        return copy.deepcopy(self.engine.data.get((self.actor_id, key)))

    def SetExtraData(self, key, value, autoSave=True):
        if self.engine.fail_save: return False
        self.engine.data[(self.actor_id, key)] = copy.deepcopy(value)
        return True

    def GetAllEffects(self):
        result = []
        for name, data in self.actor["effects"].items():
            left = int(data[0] - self.engine.now)
            if left > 0:
                result.append({"effectName": name, "duration": left, "amplifier": data[1]})
        return result

    def AddEffectToEntity(self, name, duration, amplifier, particles):
        old = self.actor["effects"].get(name)
        if old and (old[1] > amplifier or (old[1] == amplifier and old[0] > self.engine.now + duration)):
            return True
        self.actor["effects"][name] = (self.engine.now + duration, amplifier)
        self.engine.emit("RefreshEffectServerEvent" if old else "AddEffectServerEvent",
                         {"entityId": self.actor_id, "effectName": name,
                          "effectDuration": duration, "effectAmplifier": amplifier})
        return True

    def RemoveEffectFromEntity(self, name):
        self.actor["effects"].pop(name, None)
        self.engine.emit("RemoveEffectServerEvent", {"entityId": self.actor_id, "effectName": name})
        return True

    def GetEntitiesAround(self, player, radius, filters):
        self.engine.entity_calls += 1
        origin = self.engine.actors[player]
        return [key for key, actor in self.engine.actors.items()
                if actor["dimension"] == origin["dimension"] and
                all(abs(actor["pos"][i] - origin["pos"][i]) <= radius for i in range(3))]

    def GetLoadedChunks(self, dimension):
        return [(x, z) for x in range(-4, 5) for z in range(-4, 5)]

    def GetBlockPaletteBetweenPos(self, dimension, start, end):
        self.engine.palette_calls += 1
        return Palette(self.engine, dimension, start, end)

    def GetBlockLightLevel(self, pos, dimension): return self.engine.light
    def GetCurrentDimension(self): return self.engine.dimension
    def CheckColorAdjustmentEnabled(self): return self.engine.post_enabled
    def SetEnableColorAdjustment(self, value):
        self.engine.post_enabled = value
        return True
    def SetColorAdjustmentBrightness(self, value):
        self.engine.post_values["brightness"] = value
        return True
    def SetColorAdjustmentContrast(self, value):
        self.engine.post_values["contrast"] = value
        return True
    def SetColorAdjustmentSaturation(self, value):
        self.engine.post_values["saturation"] = value
        return True

    def CreateTextBoardInWorld(self, text, color, background, facing):
        self.engine.next_board += 1
        self.engine.boards[self.engine.next_board] = {"text": text}
        return self.engine.next_board
    def RemoveTextBoard(self, board): self.engine.boards.pop(board, None)
    def SetBoardPos(self, board, pos): self.engine.boards[board]["pos"] = pos
    def SetBoardDepthTest(self, board, enabled): self.engine.boards[board]["depth"] = enabled
    def SetBoardScale(self, board, size): self.engine.boards[board]["scale"] = size


class Palette(object):
    def __init__(self, engine, dimension, start, end):
        self.engine, self.dimension, self.start, self.end = engine, dimension, start, end

    def GetLocalPosListOfBlocks(self, name):
        result = []
        for (dimension, pos), block in self.engine.blocks.items():
            if block == name and dimension == self.dimension and all(self.start[i] <= pos[i] <= self.end[i] for i in range(3)):
                result.append(tuple(pos[i] - self.start[i] for i in range(3)))
        return result


class Factory(object):
    def __init__(self, engine): self.engine = engine
    def create(self, actor): return Component(self.engine, actor)
    CreateGame = CreateBlock = CreateBlockInfo = CreateChunkSource = create
    CreateExtraData = CreateEffect = CreatePos = CreateRot = CreateDimension = create
    CreateAttr = CreateEngineType = CreateTag = CreateName = create
    CreatePostProcess = CreateTextBoard = create


class Control(object):
    def __init__(self, value):
        self.value = copy.deepcopy(value)
        self.callback = None
    def asLabel(self):
        assert self.value["type"] == "label"
        return self
    def asButton(self):
        assert self.value["type"] == "button"
        return self
    def asImage(self):
        assert self.value["type"] == "image"
        return self
    def SetSprite(self, texture): self.value["texture"] = texture
    def SetSpriteGray(self, gray): self.value["grayscale"] = gray
    def SetText(self, text): self.value["text"] = text
    def SetVisible(self, visible): self.value["visible"] = visible
    def SetSize(self, size): self.value["size"] = size
    def GetSize(self):
        if self.value["size"] == ["100%", "100%"]:
            return ENGINE.screen_size
        return tuple(self.value["size"])
    def SetPosition(self, pos): self.value["offset"] = list(pos)
    def GetPosition(self): return tuple(self.value["offset"])
    def SetAnchorFrom(self, value): self.value["anchor_from"] = value
    def SetAnchorTo(self, value): self.value["anchor_to"] = value
    def SetTouchEnable(self, enabled): self.value["touch"] = enabled
    def AddTouchEventParams(self, params): self.value["events"] = params
    def SetButtonTouchUpCallback(self, callback): self.callback = callback
    def SetButtonTouchDownCallback(self, callback): self.down_callback = callback
    def SetButtonTouchMoveCallback(self, callback): self.move_callback = callback
    def SetButtonTouchMoveOutCallback(self, callback): self.move_out_callback = callback
    def SetButtonTouchCancelCallback(self, callback): self.cancel_callback = callback
    def SetButtonScreenExitCallback(self, callback): self.exit_callback = callback
    def touch(self, event, x, y):
        # The native engine suppresses move delivery unless JSON enables it.
        if event == "move" and not self.value.get("is_handle_button_move_event", False):
            return
        callback = {"down": self.down_callback, "move": self.move_callback,
                    "up": self.callback, "cancel": self.cancel_callback}[event]
        callback({"TouchPosX": x, "TouchPosY": y})


class ScreenNode(object):
    def __init__(self, namespace, name, params):
        self.controls = {}
        self.removed = False
        with open(os.path.join(ROOT, "resource_pack_F1LzIf84", "ui", "mercuryx_godeye.json"), "rb") as source:
            definitions = json.loads(source.read().decode("utf-8"))
        definition = definitions[name + "@common.base_screen"]
        def add(parent, value):
            for item in value.get("controls", []):
                for key, child in item.items():
                    path = parent + "/" + key.split("@")[0]
                    self.controls[path] = Control(child)
                    add(path, child)
        add("", definition)
    def GetBaseUIControl(self, path): return self.controls[path]
    def SetRemove(self):
        self.removed = True
        self.Destroy()


def install():
    global ENGINE
    ENGINE = Engine()
    for name in ("mod", "mod.server", "mod.client", "mod.server.extraServerApi", "mod.client.extraClientApi"):
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)
    server = sys.modules["mod.server.extraServerApi"]
    client = sys.modules["mod.client.extraClientApi"]
    sys.modules["mod"].server = sys.modules["mod.server"]
    sys.modules["mod"].client = sys.modules["mod.client"]
    sys.modules["mod.server"].extraServerApi = server
    sys.modules["mod.client"].extraClientApi = client
    enum = type("Enum", (), {"AttrType": type("AttrType", (), {"HEALTH": 0})})
    for module in (server, client):
        module.GetLevelId = lambda: "world"
        module.GetEngineCompFactory = lambda: ENGINE.factory
        module.GetEngineNamespace = lambda: "Minecraft"
        module.GetEngineSystemName = lambda: "Engine"
        module.GetMinecraftEnum = lambda: enum
        module.GetSystem = lambda namespace, name: ENGINE.systems.get(name)
    server.GetServerSystemCls = lambda: BaseSystem
    server.GetPlayerList = lambda: [key for key, actor in ENGINE.actors.items() if actor["kind"] == "minecraft:player"]
    client.GetClientSystemCls = lambda: BaseSystem
    client.GetLocalPlayerId = lambda: ENGINE.local_player
    client.GetScreenNodeCls = lambda: ScreenNode
    def register(namespace, key, path, definition):
        ENGINE.ui_defs[key] = path
        return True
    def create(namespace, key, params):
        path, name = ENGINE.ui_defs[key].rsplit(".", 1)
        module = __import__(path, fromlist=[name])
        node = getattr(module, name)(namespace, key, params)
        ENGINE.ui_nodes.append(node)
        node.Create()
        return node
    def push(namespace, key, params):
        node = create(namespace, key, params)
        ENGINE.ui_stack.append(node)
        return node
    def pop():
        ENGINE.ui_stack.pop().SetRemove()
        return True
    client.RegisterUI = register
    client.CreateUI = create
    client.PushScreen = push
    client.PopScreen = pop
    return ENGINE
