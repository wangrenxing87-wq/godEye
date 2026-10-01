# -*- coding: utf-8 -*-
import unittest
from tests import fake_sdk


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = fake_sdk.install()
        from godEyeScripts.server_system import GodEyeServer
        from godEyeScripts.client_system import GodEyeClient
        from godEyeScripts import config
        self.config = config
        self.server = GodEyeServer(config.NAMESPACE, config.SERVER_SYSTEM)
        self.client = GodEyeClient(config.NAMESPACE, config.CLIENT_SYSTEM)
        self.server.scan.clock = lambda: self.engine.now
        self.server.registry.clock = lambda: self.engine.now
        self.engine.emit("UiInitFinished", {})
        self.engine.emit("OnLocalPlayerStopLoading", {"playerId": "p1"})
        for state in self.server.players.values():
            state["lease"].clock = lambda: self.engine.now
        self.engine.tick(7)

    def apply(self, level, **options):
        value = dict(self.client.value, level=level, **options)
        self.client.apply(value)
        self.engine.tick(16)

    def test_ui_seven_levels_apply_on_click_and_zero_turns_off(self):
        self.client.open_menu()
        menu = self.client.menu
        self.assertNotIn("/panel/apply", menu.controls)
        self.assertNotIn("/panel/off", menu.controls)
        for level in range(7):
            menu.controls["/panel/body/levels/lv%d" % level].callback({})
            self.engine.tick(16)
            self.assertEqual(self.client.value["level"], level)
            self.assertEqual(self.server.players["p1"]["settings"]["level"], level)
        menu.controls["/panel/body/levels/lv0"].callback({})
        self.engine.tick(16)
        self.assertEqual(self.client.value["level"], 0)
        self.assertFalse(self.engine.boards)
        self.assertFalse(self.engine.post_enabled)
        menu.controls["/panel/close"].callback({})
        self.assertIsNone(self.client.menu)

    def test_ui_unavailable_options_are_gray_and_cannot_change_settings(self):
        self.client.open_menu()
        menu = self.client.menu
        allowed = {"ore": (4, 5, 6), "entity": (4, 5, 6), "hidden": (5, 6),
                   "enhancement": (1, 3, 4, 5, 6), "performance": (4, 5, 6)}
        for level in range(7):
            menu.controls["/panel/body/levels/lv%d" % level].callback({})
            self.engine.tick(7)
            for key, levels in allowed.items():
                path = "/panel/body/detail/" + key
                usable = level in levels
                self.assertEqual(menu.controls[path].value["touch"], usable)
                self.assertNotIn(path + "/disabled", menu.controls)
                text = menu.controls[path + "/label"].value["text"]
                if not usable:
                    self.assertTrue(text.startswith(u"§7"))
                    self.assertIn(u"未启用" if key == "performance" else u"[关]", text)
                    self.assertNotIn(u"[开]", text)
                    for state in ("default", "hover", "pressed"):
                        self.assertEqual(menu.controls[path + "/" + state].value["texture"],
                                         "textures/ui/mercuryx_godeye/button")
                        self.assertTrue(menu.controls[path + "/" + state].value["grayscale"])
                    before, revision = dict(menu.draft), self.client.revision
                    # Call directly as well as disabling native touch delivery.
                    menu.controls[path].callback({})
                    self.assertEqual(menu.draft, before)
                    self.assertEqual(self.client.revision, revision)
                    self.assertIsNone(self.client.queued_value)
                else:
                    for state in ("default", "hover", "pressed"):
                        self.assertFalse(menu.controls[path + "/" + state].value["grayscale"])

    def test_ui_switches_and_range_save_immediately_and_restore_preferences(self):
        self.client.open_menu()
        menu = self.client.menu
        menu.select(6)
        self.engine.tick(7)
        for key in ("ore", "entity", "hidden", "enhancement"):
            button = menu.controls["/panel/body/detail/" + key]
            for expected in (False, True, False):
                button.callback({})
                self.engine.tick(7)
                self.assertEqual(self.client.value[key + "_enabled"], expected)
                self.assertEqual(self.server.players["p1"]["settings"][key + "_enabled"], expected)
                self.assertTrue(button.value["touch"])
                self.assertEqual(menu.controls["/panel/body/detail/" + key + "/default"].value["texture"],
                                 "textures/ui/mercuryx_godeye/" + ("accent" if expected else "button"))
        for expected in ("quality", "economy", "balanced"):
            menu.controls["/panel/body/detail/performance"].callback({})
            self.engine.tick(7)
            self.assertEqual(self.client.value["performance"], expected)
            self.assertEqual(self.engine.data[("p1", self.config.DATA_KEY)]["performance"], expected)
        for level, usable in ((1, True), (2, False), (3, True), (0, False), (6, True)):
            menu.select(level)
            self.engine.tick(7)
            self.assertEqual(menu.controls["/panel/body/detail/enhancement"].value["touch"], usable)
            self.assertFalse(menu.draft["enhancement_enabled"])
            self.assertFalse(self.engine.post_enabled)
        for key in ("ore", "entity", "hidden", "enhancement"):
            self.assertFalse(menu.draft[key + "_enabled"])
            self.assertIn(u"[关]", menu.controls["/panel/body/detail/" + key + "/label"].value["text"])
        menu.controls["/panel/body/detail/enhancement"].callback({})
        self.engine.tick(7)
        self.assertTrue(self.engine.post_enabled)

    def test_ui_rapid_changes_keep_latest_selection_after_menu_closes(self):
        self.client.open_menu()
        menu = self.client.menu
        menu.select(6)
        menu.toggle_ore({})
        menu.toggle_entity({})
        menu.toggle_performance({})
        menu.select(0)
        desired = dict(menu.draft)
        self.assertIn(u"正在保存", menu.controls["/panel/notice"].value["text"])
        menu.close({})
        self.engine.tick(7)
        self.assertEqual(self.client.value, desired)
        self.assertEqual(self.engine.data[("p1", self.config.DATA_KEY)], desired)
        self.assertFalse(self.client.error)
        self.assertIsNone(self.client.queued_value)
        self.assertFalse(self.engine.post_enabled)
        self.assertFalse(self.server.scan.interests)

    def test_ui_delayed_reply_preserves_newer_clicks_and_reopened_menu(self):
        self.client.open_menu()
        menu = self.client.menu
        requests = []
        self.client.NotifyToServer = lambda event, args: requests.append(dict(args))
        menu.select(6)
        self.assertEqual(self.client.value["level"], 0)
        self.assertTrue(menu.controls["/panel/body/detail/ore"].value["touch"])
        menu.toggle_ore({})
        menu.toggle_hidden({})
        menu.toggle_performance({})
        menu.select(5)
        desired = dict(menu.draft)
        self.assertEqual(len(requests), 1)
        menu.close({})
        self.client.open_menu()
        menu = self.client.menu
        self.assertEqual(menu.draft, desired)
        self.server.on_request(dict(requests[0], __id__="p1"))
        self.assertEqual(self.client.value["level"], 6)
        self.assertEqual(menu.draft, desired)
        self.engine.tick(self.config.REQUEST_INTERVAL_TICKS - 1)
        self.assertEqual(len(requests), 1)
        self.engine.tick(1)
        self.assertEqual(len(requests), 2)
        self.server.on_request(dict(requests[1], __id__="p1"))
        self.assertEqual(self.client.value, desired)
        self.assertEqual(self.engine.data[("p1", self.config.DATA_KEY)], desired)
        self.assertFalse(self.client.error)
        self.assertIsNone(self.client.pending)
        self.assertIsNone(self.client.queued_value)
        self.assertNotIn(u"正在保存", menu.controls["/panel/notice"].value["text"])

    def test_ui_failed_save_restores_saved_state_and_can_retry(self):
        self.client.open_menu()
        menu = self.client.menu
        self.engine.fail_save = True
        menu.select(6)
        self.assertEqual(menu.draft["level"], 0)
        self.assertFalse(menu.controls["/panel/body/detail/ore"].value["touch"])
        self.assertIn(u"保存失败", menu.controls["/panel/notice"].value["text"])
        self.assertIsNone(self.client.pending)
        self.engine.fail_save = False
        menu.select(6)
        self.engine.tick(7)
        self.assertEqual(self.client.value["level"], 6)
        self.assertFalse(self.client.error)

    def test_ui_save_timeout_restores_confirmed_selection_and_can_retry(self):
        self.client.open_menu()
        menu = self.client.menu
        send = self.client.NotifyToServer
        self.client.NotifyToServer = lambda event, args: None
        menu.select(6)
        menu.toggle_ore({})
        self.engine.tick(150)
        self.assertEqual(menu.draft, self.client.value)
        self.assertEqual(menu.draft["level"], 0)
        self.assertIn(u"超时", menu.controls["/panel/notice"].value["text"])
        self.assertIsNone(self.client.pending)
        self.assertIsNone(self.client.queued_value)
        self.client.NotifyToServer = send
        menu.select(4)
        self.engine.tick(7)
        self.assertEqual(self.client.value["level"], 4)
        self.assertFalse(self.client.error)

    def test_ui_waits_for_initial_settings_before_accepting_changes(self):
        self.client.revision = -1
        self.client.open_menu()
        menu = self.client.menu
        menu.select(6)
        menu.toggle_performance({})
        menu.toggle_enhancement({})
        self.assertEqual(menu.draft["level"], 0)
        self.assertFalse(menu.controls["/panel/body/levels/lv6"].value["touch"])
        self.assertIn(u"正在同步", menu.controls["/panel/notice"].value["text"])
        self.server._sync("p1")
        self.assertTrue(menu.controls["/panel/body/levels/lv6"].value["touch"])
        menu.select(6)
        self.engine.tick(7)
        self.assertEqual(self.client.value["level"], 6)

    def test_player_settings_are_independent_and_persist_on_rejoin(self):
        self.apply(5)
        self.server.on_request({"__id__": "p2", "playerId": "p1", "action": "apply", "settings": {"level": 2}})
        self.assertEqual(self.server.players["p1"]["settings"]["level"], 5)
        self.assertEqual(self.server.players["p2"]["settings"]["level"], 2)
        self.server.on_leave({"id": "p1"})
        self.server.on_request({"__id__": "p1", "action": "ready"})
        self.assertEqual(self.server.players["p1"]["settings"]["level"], 5)

    def test_save_failure_and_invalid_request_do_not_change_state(self):
        self.apply(2)
        self.engine.fail_save = True
        self.apply(6)
        self.assertEqual(self.client.value["level"], 2)
        self.assertTrue(self.client.error)
        self.server.on_request({"__id__": "p1", "action": "apply", "settings": {"level": 99}})
        self.assertEqual(self.server.players["p1"]["settings"]["level"], 2)
        self.server.on_request({"playerId": "p1", "action": "apply", "settings": {"level": 6}})
        self.assertEqual(self.server.players["p1"]["settings"]["level"], 2)

    def test_diamond_sense_then_precise_markers_then_stop(self):
        self.engine.blocks[(0, (6, 4, 4))] = "minecraft:diamond_ore"
        self.engine.blocks[(0, (7, 4, 4))] = "minecraft:diamond_ore"
        self.apply(4)
        self.engine.tick(30)
        sensed = [t for t in self.client.targets if t["category"] == "ore"]
        self.assertEqual(len(sensed), 1)
        self.assertNotIn("pos", sensed[0])
        self.apply(6)
        self.engine.tick(30)
        self.assertTrue(self.engine.boards)
        self.assertEqual(self.client.targets[0]["count"], 2)
        self.assertTrue(all(not board["depth"] for board in self.engine.boards.values()))
        self.apply(0)
        previous = self.engine.palette_calls
        self.engine.tick(60)
        self.assertEqual(self.engine.palette_calls, previous)
        self.assertFalse(self.engine.boards)
        self.assertFalse(self.server.scan.interests)

    def test_invisible_tagged_and_registered_targets(self):
        self.engine.actors["spirit"] = self.engine.actor((5, 4, 4), "other:ghost", ["nightvision:spirit"])
        invisible = self.engine.actor((6, 4, 4), "minecraft:zombie")
        invisible["effects"]["invisibility"] = (self.engine.now + 99, 0)
        self.engine.actors["invisible"] = invisible
        self.server.RegisterTarget("quest:entrance", "entrance", 0, (7, 4, 4), u"秘密入口", ["p1"])
        self.apply(4)
        self.assertTrue(any(t["category"] == "spirit" for t in self.client.targets))
        self.assertTrue(any(t["id"] == "entity:invisible" for t in self.client.targets))
        self.assertFalse(any(t["id"] == "quest:entrance" for t in self.client.targets))
        self.apply(5)
        self.assertTrue(any(t["id"] == "quest:entrance" for t in self.client.targets))
        self.server.UnregisterTarget("quest:entrance")
        self.engine.tick(16)
        self.assertFalse(any(t["id"] == "quest:entrance" for t in self.client.targets))

    def test_utf8_engine_name_and_external_ore_label(self):
        self.engine.actors["spirit"] = self.engine.actor((5, 4, 4), "other:ghost", ["nightvision:spirit"])
        self.engine.actors["spirit"]["name"] = u"守夜人".encode("utf-8")
        self.server.RegisterOre(u"other:magic_ore", u"魔法矿")
        self.engine.blocks[(0, (6, 4, 4))] = "other:magic_ore"
        self.apply(6)
        self.engine.tick(30)
        spirit = next(t for t in self.client.targets if t["category"] == "spirit")
        self.assertEqual(spirit["label"], u"守夜人")
        self.assertIn(u"守夜人", self.client.target_text(spirit, (0, 0, 0), (0, 0)))
        self.assertTrue(any(t["label"] == u"魔法矿" for t in self.client.targets))
    def test_dimension_and_old_packets_cannot_restore_previous_markers(self):
        self.server.RegisterTarget("q:x", "quest", 0, (5, 4, 4), "target")
        self.apply(6)
        old = [m[2] for m in self.engine.messages if m[1] == self.config.TARGET_EVENT][-1]
        self.engine.dimension = 1
        self.engine.actors["p1"]["dimension"] = 1
        args = {"playerId": "p1", "fromDimensionId": 0, "toDimensionId": 1}
        self.engine.emit("DimensionChangeFinishServerEvent", args)
        self.engine.emit("DimensionChangeFinishClientEvent", args)
        self.engine.tick(16)
        self.client.on_targets(old)
        self.assertEqual(self.client.dimension, 1)
        self.assertFalse(self.client.targets)
        self.assertFalse(self.engine.boards)
        self.assertTrue(all(key[0] == 1 for key in self.server.scan.interests["p1"]))

    def test_death_respawn_and_effect_restoration(self):
        self.apply(6)
        actor = self.engine.actors["p1"]
        actor["health"] = 0
        actor["effects"].clear()
        self.engine.tick(30)
        self.assertFalse(self.server.scan.interests)
        self.assertTrue(self.client.dead)
        actor["health"] = 20
        self.engine.emit("PlayerRespawnFinishServerEvent", {"playerId": "p1"})
        self.engine.tick(30)
        self.assertIn("night_vision", actor["effects"])
        self.assertFalse(self.client.dead)
        self.assertEqual(self.client.value["level"], 6)

    def test_existing_post_process_is_preserved(self):
        self.engine.post_enabled = True
        self.engine.post_values["brightness"] = 2.5
        self.apply(3)
        self.assertEqual(self.engine.post_values["brightness"], 2.5)
        self.assertTrue(self.client.visual_notice)
        self.apply(0)
        self.assertTrue(self.engine.post_enabled)

    def test_hud_recreated_after_dimension_loading_destroys_screen(self):
        self.apply(6)
        old_hud = self.client.hud
        old_hud.Destroy()
        self.engine.ui_defs.clear()
        self.assertIsNone(self.client.hud)
        self.engine.dimension = -1
        self.engine.tick(30)
        self.assertIsNone(self.client.hud)
        self.engine.dimension = 1
        self.engine.actors["p1"]["dimension"] = 1
        self.engine.emit("DimensionChangeFinishClientEvent", {"playerId": "p1", "toDimensionId": 1})
        self.engine.tick(30)
        self.assertIsNotNone(self.client.hud)
        self.assertIsNot(self.client.hud, old_hud)
        self.assertTrue(self.client.hud.created)

    def test_leaving_preserves_saved_effect_ownership_for_rejoin(self):
        self.apply(6)
        before = self.engine.data[("p1", self.config.EFFECT_DATA_KEY)]
        self.engine.tick(90)
        self.server.on_leave({"id": "p1"})
        saved = self.engine.data[("p1", self.config.EFFECT_DATA_KEY)]
        self.assertIsNotNone(saved)
        self.assertEqual(saved, before)
        self.server.on_request({"__id__": "p1", "action": "ready"})
        state = self.server.players["p1"]
        state["lease"].release()
        self.assertFalse(self.engine.actors["p1"]["effects"])

    def test_custom_ore_and_block_change_invalidation(self):
        self.server.RegisterOre("other:magic_ore", u"魔法矿", True)
        self.engine.blocks[(0, (6, 4, 4))] = "other:magic_ore"
        self.apply(5)
        self.engine.tick(30)
        self.assertTrue(any(t["label"] == u"魔法矿" for t in self.client.targets))
        self.engine.blocks.clear()
        self.engine.emit("ServerPlayerTryDestroyBlockEvent", {"dimensionId": 0, "x": 6, "y": 4, "z": 4})
        self.engine.tick(30)
        self.assertFalse(self.client.targets)

    def test_teardown_removes_only_owned_resources(self):
        self.server.RegisterTarget("q:x", "quest", 0, (5, 4, 4), "target")
        self.apply(6)
        self.client.Destroy()
        self.server.Destroy()
        self.assertFalse(self.engine.boards)
        self.assertFalse(self.engine.post_enabled)
        self.assertFalse(self.engine.listeners)
        self.assertFalse(self.server.players)

    def test_pc_shortcut_does_not_open_from_chat(self):
        self.client.on_key({"key": "71", "isDown": "1", "screenName": "chat_screen"})
        self.assertIsNone(self.client.menu)
        self.client.on_key({"key": "71", "isDown": "1", "screenName": "hud_screen"})
        self.assertIsNotNone(self.client.menu)

    def test_launcher_tap_jitter_opens_but_drag_release_does_not(self):
        button = self.client.hud.controls["/root/entry"]
        self.assertEqual(button.GetPosition(), (542, 28))
        button.down_callback({"TouchPosX": 560, "TouchPosY": 40})
        button.move_callback({"TouchPosX": 562, "TouchPosY": 41})
        button.callback({"TouchPosX": 562, "TouchPosY": 41})
        self.assertIsNotNone(self.client.menu)
        self.client.menu.close({})
        button.touch("down", 560, 40)
        button.touch("move", 260, 190)
        # Check movement while held, before release can provide final coordinates.
        self.assertEqual(button.GetPosition(), (242, 178))
        button.touch("up", 260, 190)
        button.callback({"TouchPosX": 260, "TouchPosY": 190})
        self.assertEqual(button.GetPosition(), (242, 178))
        self.assertIsNone(self.client.menu)

    def test_launcher_drag_clamps_and_survives_resize_and_recreation(self):
        button = self.client.hud.controls["/root/entry"]
        button.down_callback({"TouchPosX": 560, "TouchPosY": 40})
        button.move_callback({"TouchPosX": -100, "TouchPosY": 1000})
        button.cancel_callback({"TouchPosX": -100, "TouchPosY": 1000})
        self.assertEqual(button.GetPosition(), (0, 324))
        self.assertIsNone(self.client.menu)
        self.engine.screen_size = (320, 180)
        self.client.hud.refresh()
        self.assertEqual(button.GetPosition(), (0, 144))
        self.client.hud.SetRemove()
        self.engine.ui_defs.clear()
        self.client.on_ui({})
        self.assertEqual(self.client.hud.controls["/root/entry"].GetPosition(), (0, 144))

    def test_launcher_command_utf8_toggle_reset_and_player_isolation(self):
        self.apply(6)
        self.client.entry_position = (0.25, 0.75)
        self.client.hud.layout_entry(force=True)
        other = {"playerId": "p2", "message": u">天眼归位", "cancel": False}
        self.server.on_chat(other)
        self.assertTrue(other["cancel"])
        self.assertTrue(self.client.entry_visible)
        args = {"playerId": "p1", "message": u" >天眼归位 ".encode("utf-8"), "cancel": False}
        self.server.on_chat(args)
        self.assertTrue(args["cancel"])
        self.assertFalse(self.client.entry_visible)
        self.assertFalse(self.client.hud.controls["/root/entry"].value["visible"])
        self.assertEqual(self.client.value["level"], 6)
        self.client.hud.SetRemove()
        self.client.on_ui({})
        self.assertFalse(self.client.hud.controls["/root/entry"].value["visible"])
        self.server.on_chat(args)
        self.assertTrue(self.client.entry_visible)
        self.assertEqual(self.client.hud.controls["/root/entry"].GetPosition(), (542, 28))
        self.assertIsNone(self.client.menu)
        self.server.on_chat({"playerId": "p1", "message": u"天眼".encode("utf-8"), "cancel": False})
        self.assertIsNotNone(self.client.menu)

    def test_launcher_interrupted_gesture_and_unrelated_chat_are_ignored(self):
        button = self.client.hud.controls["/root/entry"]
        button.down_callback({"TouchPosX": 560, "TouchPosY": 40})
        button.exit_callback({})
        button.callback({"TouchPosX": 560, "TouchPosY": 40})
        self.assertIsNone(self.client.menu)
        args = {"playerId": "p1", "message": u">天眼归位其他", "cancel": False}
        self.server.on_chat(args)
        self.assertFalse(args["cancel"])
        self.assertTrue(self.client.entry_visible)


if __name__ == "__main__":
    unittest.main()
