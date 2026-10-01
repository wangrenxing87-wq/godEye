# -*- coding: utf-8 -*-
from __future__ import division
import traceback
import mod.client.extraClientApi as clientApi
from godEyeScripts import config, core

ClientSystem = clientApi.GetClientSystemCls()


class GodEyeClient(ClientSystem):
    def __init__(self, namespace, system_name):
        ClientSystem.__init__(self, namespace, system_name)
        self.factory = clientApi.GetEngineCompFactory()
        self.level_id = clientApi.GetLevelId()
        self.game = self.factory.CreateGame(self.level_id)
        self.post = self.factory.CreatePostProcess(self.level_id)
        self.board_comp = self.factory.CreateTextBoard(self.level_id)
        self.value = core.settings(None)
        self.revision = -1
        self.dimension = None
        self.tick = 0
        self.last_targets = 0
        self.ready = False
        self.registered = False
        self.hud = None
        self.menu = None
        self.entry_visible = True
        self.entry_position = None
        self.targets = []
        self.boards = {}
        self.light = 15
        self.progress = (0, 0)
        self.dead = False
        self.enhancement_owned = False
        self.enhancement_value = None
        self.visual_notice = u""
        self.pending = None
        self.pending_value = None
        self.queued_value = None
        self.apply_after = 0
        self.error = u""
        self.errors = {}
        for event, callback in (("UiInitFinished", self.on_ui),
                                ("OnLocalPlayerStopLoading", self.on_ready),
                                ("DimensionChangeFinishClientEvent", self.on_dimension),
                                ("OnKeyPressInGame", self.on_key)):
            self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(), event, self, callback)
        for event, callback in ((config.STATE_EVENT, self.on_state),
                                (config.TARGET_EVENT, self.on_targets),
                                (config.UI_EVENT, self.on_ui_command)):
            self.ListenForEvent(config.NAMESPACE, config.SERVER_SYSTEM, event, self, callback)
        print("[GodEye][Client] initialized " + config.VERSION)

    def _error(self, operation):
        if self.tick - self.errors.get(operation, -300) >= 300:
            self.errors[operation] = self.tick
            print("[GodEye][Client] " + operation + "\n" + traceback.format_exc())

    def on_ui(self, args):
        # Native dimension loading can clear registrations as well as nodes.
        clientApi.RegisterUI(config.NAMESPACE, "hud", "godEyeScripts.ui.GodEyeHUD", "mercuryx_godeye.hud")
        clientApi.RegisterUI(config.NAMESPACE, "menu", "godEyeScripts.ui.GodEyeMenu", "mercuryx_godeye.menu")
        self.registered = True
        if self.hud is None:
            self.hud = clientApi.CreateUI(config.NAMESPACE, "hud", {"isHud": 1})

    def on_ready(self, args):
        self.ready = True
        self.request_state()

    def request_state(self):
        self.NotifyToServer(config.REQUEST_EVENT, {"action": "ready"})

    def on_dimension(self, args):
        if args.get("playerId") != clientApi.GetLocalPlayerId():
            return
        self.dimension = args.get("toDimensionId")
        self.clear_targets()
        self.release_visual()
        self.ready = True
        self.request_state()

    def on_state(self, args):
        if args.get("revision", -1) < self.revision:
            return
        if args.get("dimension") != self.game.GetCurrentDimension():
            return
        self.value = core.settings(args.get("settings"))
        self.revision = args["revision"]
        self.dimension = args["dimension"]
        self.pending = None
        self.pending_value = None
        # Wait from the reply so rapid clicks also respect the server limit
        # when client and server ticks or network delivery differ.
        self.apply_after = self.tick + config.REQUEST_INTERVAL_TICKS
        self.error = args.get("error") or u""
        if self.error or self.queued_value == self.value:
            self.queued_value = None
        self.clear_targets()
        self.update_visual()
        if self.menu:
            self.menu.sync_state()

    def on_targets(self, args):
        if (args.get("revision") != self.revision or args.get("dimension") != self.dimension
                or args.get("dimension") != self.game.GetCurrentDimension()):
            return
        self.targets = args.get("targets", [])[:12]
        self.light = args.get("light", 15)
        self.dead = args.get("dead", False)
        self.progress = (args.get("complete", 0), args.get("total", 0))
        self.last_targets = self.tick
        self.update_visual()
        self.update_boards()

    def apply(self, value):
        if self.revision < 0:
            return
        self.error = u""
        # Keep the latest complete selection while one save is in flight.
        # The queue belongs to the system, so closing the menu cannot lose it.
        self.queued_value = core.settings(value)
        self.flush_settings()

    def menu_settings(self):
        return core.settings(self.queued_value or self.pending_value or self.value)

    def flush_settings(self):
        if self.pending is not None or self.queued_value is None:
            return
        if self.queued_value == self.value:
            self.queued_value = None
            if self.menu:
                self.menu.sync_state()
            return
        if self.tick < self.apply_after:
            return
        self.pending_value = self.queued_value
        self.queued_value = None
        self.pending = self.tick
        self.NotifyToServer(config.REQUEST_EVENT, {"action": "apply", "settings": dict(self.pending_value)})

    def open_menu(self, args=None):
        if self.registered and self.menu is None:
            self.menu = clientApi.PushScreen(config.NAMESPACE, "menu", {})

    def on_ui_command(self, args):
        if args.get("action") == "toggle_entry":
            self.entry_visible = not self.entry_visible
            if self.entry_visible:
                self.entry_position = None
            if self.hud:
                self.hud.cancel_drag()
                self.hud.layout_entry(force=True)
                self.hud.refresh()
        else:
            self.open_menu()

    def on_key(self, args):
        # PC shortcut; do not intercept typing in chat or another menu.
        if (str(args.get("key")) == "71" and str(args.get("isDown")) == "1"
                and args.get("screenName") == "hud_screen"):
            self.open_menu()

    def clear_targets(self):
        self.targets = []
        self.progress = (0, 0)
        for board in list(self.boards.values()):
            self.board_comp.RemoveTextBoard(board)
        self.boards.clear()

    def release_visual(self):
        if self.enhancement_owned:
            self.post.SetColorAdjustmentBrightness(1.0)
            self.post.SetColorAdjustmentContrast(1.0)
            self.post.SetColorAdjustmentSaturation(1.0)
            self.post.SetEnableColorAdjustment(False)
        self.enhancement_owned = False
        self.enhancement_value = None

    def update_visual(self):
        enabled = core.capabilities(self.value)["enhance"] and not self.dead
        if not enabled:
            self.release_visual()
            self.visual_notice = u""
            return
        if not self.enhancement_owned:
            if self.post.CheckColorAdjustmentEnabled():
                self.visual_notice = u"已有画面滤镜，保留原有效果"
                return
            if not self.post.SetEnableColorAdjustment(True):
                self.visual_notice = u"当前设备未启用画面增强"
                return
            self.enhancement_owned = True
        darkness = max(0.0, min(1.0, (12 - self.light) / 12.0))
        if self.value["level"] == 1:
            parameters = (1.0 + 0.55 * darkness, 1.0, 1.0)
        else:
            parameters = (1.0 + 0.10 * darkness, 1.0 + 0.10 * darkness, 0.96)
        if parameters != self.enhancement_value:
            results = (self.post.SetColorAdjustmentBrightness(parameters[0]),
                       self.post.SetColorAdjustmentContrast(parameters[1]),
                       self.post.SetColorAdjustmentSaturation(parameters[2]))
            if all(results):
                self.enhancement_value = parameters
                self.visual_notice = u""
            else:
                self.release_visual()
                self.visual_notice = u"画面增强不可用，其他能力继续生效"

    def player_view(self):
        player = clientApi.GetLocalPlayerId()
        pos = self.factory.CreatePos(player).GetFootPos()
        rot = self.factory.CreateRot(player).GetRot()
        return pos, rot or (0, 0)

    def target_text(self, target, pos, rotation):
        label = target.get("label", u"目标")
        if target.get("coarse"):
            return u"◇ %s  %s\n   约 %d 格" % (label, target["direction"], target["distance"])
        direction, distance = core.bearing(pos, target["pos"], rotation[1])
        suffix = u" · 已探测 %d 块" % target["count"] if target["category"] == "ore" else u""
        return u"◆ %s%s\n   %s · %.0f 格" % (label, suffix, direction, distance)

    def update_boards(self):
        caps = core.capabilities(self.value)
        player_pos, unused_rotation = self.player_view()
        selected = self.targets[:caps["limit"]] if caps["markers"] and not self.dead else []
        selected = [t for t in selected if "pos" in t]
        keep = set(t["id"] for t in selected)
        for key in list(self.boards):
            if key not in keep:
                self.board_comp.RemoveTextBoard(self.boards.pop(key))
        for target in selected:
            key = target["id"]
            color = (0.35, 0.9, 1.0, 1.0) if target["category"] == "ore" else (1.0, 0.78, 0.35, 1.0)
            if key not in self.boards:
                board = self.board_comp.CreateTextBoardInWorld(
                    u"◆ " + target["label"], color, (0.02, 0.04, 0.08, 0.65), True)
                if board is None:
                    continue
                self.boards[key] = board
                self.board_comp.SetBoardDepthTest(board, False)
            # Keep distant labels readable while retaining their world position.
            distance = core.distance2(player_pos, target["pos"]) ** 0.5 if core.valid_pos(player_pos) else 8
            scale = max(2.5, min(8.0, distance * 0.4))
            self.board_comp.SetBoardScale(self.boards[key], (scale, scale))
            self.board_comp.SetBoardPos(self.boards[key], tuple(target["pos"]))

    def Update(self):
        self.tick += 1
        if self.tick % 60 == 0 and self.ready and self.revision < 0:
            self.request_state()
        if self.pending is not None and self.tick - self.pending >= 150:
            self.pending = None
            self.pending_value = None
            self.queued_value = None
            self.error = u"连接超时，请重试。"
            if self.menu:
                self.menu.sync_state()
        self.flush_settings()
        if self.tick % 6 == 0:
            try:
                current_dimension = self.game.GetCurrentDimension()
                if current_dimension != self.dimension or self.tick - self.last_targets > 90:
                    self.clear_targets()
                # Dimension loading destroys HUD screens without another
                # UiInitFinished event. Recreate after the world is usable.
                if (self.tick % 30 == 0 and self.ready and self.registered
                        and self.hud is None and current_dimension >= 0):
                    self.on_ui({})
                if self.hud:
                    self.hud.refresh()
            except Exception:
                self._error("hud")

    def Destroy(self):
        self.UnListenAllEvents()
        self.clear_targets()
        self.release_visual()
        if self.hud:
            self.hud.SetRemove()
        self.hud = self.menu = None
