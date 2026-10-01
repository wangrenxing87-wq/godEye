# -*- coding: utf-8 -*-
import mod.client.extraClientApi as clientApi
from godEyeScripts import config, core

ScreenNode = clientApi.GetScreenNodeCls()


class GodEyeScreen(ScreenNode):
    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.system = clientApi.GetSystem(config.NAMESPACE, config.CLIENT_SYSTEM)
        self.created = False

    def text(self, path, value):
        self.GetBaseUIControl(path).asLabel().SetText(value)

    def bind(self, path, callback):
        button = self.GetBaseUIControl(path).asButton()
        button.AddTouchEventParams({"isSwallow": True})
        button.SetButtonTouchUpCallback(callback)


class GodEyeHUD(GodEyeScreen):
    def Create(self):
        self.created = True
        self.system.hud = self
        self.drag_start = None
        self.dragged = False
        self.entry_bounds = None
        button = self.GetBaseUIControl("/root/entry").asButton()
        button.AddTouchEventParams({"isSwallow": True})
        button.SetButtonTouchDownCallback(self.on_entry_down)
        button.SetButtonTouchMoveCallback(self.on_entry_move)
        button.SetButtonTouchMoveOutCallback(self.on_entry_move)
        button.SetButtonTouchUpCallback(self.on_entry_up)
        button.SetButtonTouchCancelCallback(self.on_entry_cancel)
        button.SetButtonScreenExitCallback(self.cancel_drag)
        button.SetAnchorFrom("top_left")
        button.SetAnchorTo("top_left")
        self.refresh()

    def layout_entry(self, force=False):
        button = self.GetBaseUIControl("/root/entry")
        size = self.GetBaseUIControl("/root").GetSize()
        button_size = button.GetSize()
        if size[0] <= 0 or size[1] <= 0:
            return
        bounds = tuple(max(0.0, size[i] - button_size[i]) for i in range(2))
        if not force and bounds == self.entry_bounds:
            return
        self.cancel_drag()
        self.entry_bounds = bounds
        position = self.system.entry_position
        if position is None:
            position = (max(0, bounds[0] - 10), min(28, bounds[1]))
        else:
            position = tuple(position[i] * bounds[i] for i in range(2))
        button.SetPosition(position)

    def touch_position(self, args):
        x, y = args.get("TouchPosX"), args.get("TouchPosY")
        if x is None or y is None:
            return None
        return (x, y)

    def on_entry_down(self, args):
        self.cancel_drag()
        if not self.system.entry_visible or self.system.menu is not None:
            return
        self.layout_entry()
        touch = self.touch_position(args)
        if touch is not None and self.entry_bounds is not None:
            self.drag_start = (touch, self.GetBaseUIControl("/root/entry").GetPosition())

    def on_entry_move(self, args):
        touch = self.touch_position(args)
        if self.drag_start is None or touch is None:
            return
        origin, position = self.drag_start
        delta = (touch[0] - origin[0], touch[1] - origin[1])
        # Ignore normal finger jitter; once dragging, never turn release into a tap.
        if not self.dragged and delta[0] ** 2 + delta[1] ** 2 < 25:
            return
        self.dragged = True
        bounds = self.entry_bounds
        position = tuple(max(0.0, min(bounds[i], position[i] + delta[i])) for i in range(2))
        self.GetBaseUIControl("/root/entry").SetPosition(position)
        # Fractions survive changes to resolution, GUI scale and HUD recreation.
        self.system.entry_position = tuple(position[i] / float(bounds[i]) if bounds[i] else 0.0
                                           for i in range(2))

    def on_entry_up(self, args):
        if self.drag_start is None:
            return
        self.on_entry_move(args)
        activate = not self.dragged
        self.cancel_drag()
        if activate:
            self.system.open_menu()

    def on_entry_cancel(self, args):
        self.on_entry_move(args)
        self.cancel_drag()

    def cancel_drag(self, args=None):
        self.drag_start = None
        self.dragged = False

    def refresh(self):
        if not self.created:
            return
        system = self.system
        level = system.value["level"]
        self.layout_entry()
        self.text("/root/entry/level", u"LV.%d" % level)
        self.GetBaseUIControl("/root/entry").SetVisible(system.entry_visible and system.menu is None)
        visible = level >= 4 and not system.dead and system.menu is None
        self.GetBaseUIControl("/root/radar").SetVisible(visible)
        if not visible:
            return
        pos, rotation = system.player_view()
        if not core.valid_pos(pos):
            return
        complete, total = system.progress
        if total and complete < total:
            status = u"探测中 %d%%" % int(complete * 100 / total)
        elif system.targets:
            status = u"附近发现 %d 处目标" % len(system.targets)
        else:
            status = u"已探测区域暂无目标"
        self.text("/root/radar/status", u"%s · %s" % (config.LEVELS[level][0], status))
        self.GetBaseUIControl("/root/radar").SetSize((252, 32 + 36 * min(4, len(system.targets))))
        # Four readable cards; the world markers can display more targets.
        for index in range(4):
            path = "/root/radar/target%d" % index
            self.GetBaseUIControl(path).SetVisible(index < len(system.targets))
            if index < len(system.targets):
                self.text(path, system.target_text(system.targets[index], pos, rotation))

    def Destroy(self):
        self.cancel_drag()
        self.created = False
        if self.system and self.system.hud is self:
            self.system.hud = None


class GodEyeMenu(GodEyeScreen):
    def __init__(self, namespace, name, param):
        GodEyeScreen.__init__(self, namespace, name, param)
        self.draft = self.system.menu_settings()

    def Create(self):
        self.created = True
        self.system.menu = self
        for index, callback in enumerate((self.level0, self.level1, self.level2, self.level3,
                                          self.level4, self.level5, self.level6)):
            self.bind("/panel/body/levels/lv%d" % index, callback)
        self.bind("/panel/close", self.close)
        for key, callback in (("ore", self.toggle_ore), ("entity", self.toggle_entity),
                              ("hidden", self.toggle_hidden), ("enhancement", self.toggle_enhancement),
                              ("performance", self.toggle_performance)):
            self.bind("/panel/body/detail/" + key, callback)
        self.render()

    def sync_state(self):
        self.draft = self.system.menu_settings()
        self.render()

    def select(self, level):
        if self.system.revision < 0:
            return
        self.draft["level"] = level
        self.commit()

    def level0(self, args): self.select(0)
    def level1(self, args): self.select(1)
    def level2(self, args): self.select(2)
    def level3(self, args): self.select(3)
    def level4(self, args): self.select(4)
    def level5(self, args): self.select(5)
    def level6(self, args): self.select(6)

    def available_options(self):
        # Ask the same capability rules used by gameplay, with preferences on.
        # An available option that the player disabled must remain clickable.
        caps = core.capabilities(dict(self.draft, ore_enabled=True, entity_enabled=True,
                                      hidden_enabled=True, enhancement_enabled=True))
        return {"ore_enabled": caps["ore"], "entity_enabled": caps["entities"],
                "hidden_enabled": caps["hidden"], "enhancement_enabled": caps["enhance"],
                "performance": caps["ore"] or caps["entities"] or caps["hidden"]}

    def toggle(self, key):
        if self.system.revision < 0 or not self.available_options().get(key, False):
            return
        self.draft[key] = not self.draft[key]
        self.commit()

    def toggle_ore(self, args): self.toggle("ore_enabled")
    def toggle_entity(self, args): self.toggle("entity_enabled")
    def toggle_hidden(self, args): self.toggle("hidden_enabled")
    def toggle_enhancement(self, args): self.toggle("enhancement_enabled")

    def toggle_performance(self, args):
        if self.system.revision < 0 or not self.available_options()["performance"]:
            return
        values = ("economy", "balanced", "quality")
        self.draft["performance"] = values[(values.index(self.draft["performance"]) + 1) % len(values)]
        self.commit()

    def commit(self):
        self.system.apply(self.draft)
        self.render()

    def close(self, args):
        clientApi.PopScreen()

    def style_option(self, path, usable, enabled=False):
        self.GetBaseUIControl(path).SetTouchEnable(usable)
        # Reuse the already-loaded button texture for locked options. A new
        # disabled texture can remain missing in the engine's resource cache.
        for state, texture in (("default", "accent" if enabled else "button"),
                               ("hover", "hover"), ("pressed", "accent")):
            image = self.GetBaseUIControl(path + "/" + state).asImage()
            image.SetSprite("textures/ui/mercuryx_godeye/" + (texture if usable else "button"))
            image.SetSpriteGray(not usable)

    def render(self):
        if not self.created:
            return
        level = self.draft["level"]
        current = self.system.value["level"]
        ready = self.system.revision >= 0
        for index, (label, description) in enumerate(config.LEVELS):
            prefix = u"§b● " if index == level else u"§7○ "
            self.text("/panel/body/levels/lv%d/label" % index,
                      prefix + u"Lv.%d  %s" % (index, label))
            self.GetBaseUIControl("/panel/body/levels/lv%d" % index).SetTouchEnable(ready)
        self.text("/panel/body/detail/name", u"§b%s" % config.LEVELS[level][0])
        self.text("/panel/body/detail/description", config.LEVELS[level][1])
        available = self.available_options()
        for key, label in (("ore", u"矿脉感知"), ("entity", u"特殊生命"),
                           ("hidden", u"隐藏目标"), ("enhancement", u"画面增强")):
            path = "/panel/body/detail/" + key
            usable = ready and available[key + "_enabled"]
            # Show the effective state: an ineligible feature is always off,
            # even if its saved preference was on at a higher level.
            enabled = usable and self.draft[key + "_enabled"]
            state = u"§b[开] " if enabled else u"§7[关] "
            self.text(path + "/label", state + label)
            self.style_option(path, usable, enabled)
        perf = {"economy": u"省电", "balanced": u"均衡", "quality": u"高范围"}
        path = "/panel/body/detail/performance"
        usable = ready and available["performance"]
        self.text(path + "/label", u"范围：" + perf[self.draft["performance"]]
                  if usable else u"§7范围：未启用")
        self.style_option(path, usable)
        self.text("/panel/current", u"当前：Lv.%d %s" % (current, config.LEVELS[current][0]))
        saving = self.system.pending is not None or self.system.queued_value is not None
        notice = (self.system.error or (u"正在同步设置…" if not ready else
                  u"正在保存…" if saving else self.system.visual_notice or
                  u"点击即生效 · Lv.0 关闭 · 随世界保存"))
        self.text("/panel/notice", notice)

    def Destroy(self):
        self.created = False
        if self.system and self.system.menu is self:
            self.system.menu = None
