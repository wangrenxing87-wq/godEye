"""Build reproducible code-drawn UI assets and JSON. Run with Python 3."""
import json
import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RP = ROOT / "resource_pack_F1LzIf84"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def png(path, size, pixel):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    rows = b"".join(b"\0" + bytes(v for x in range(size) for v in pixel(x, y)) for y in range(size))
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def texture(name, fill, border):
    def pixel(x, y):
        dx, dy = max(4 - x, 0, x - 27), max(4 - y, 0, y - 27)
        if dx * dx + dy * dy > 16:
            return (0, 0, 0, 0)
        if x < 2 or y < 2 or x > 29 or y > 29 or dx * dx + dy * dy > 5:
            return border
        return fill
    png(RP / "textures/ui/mercuryx_godeye" / (name + ".png"), 32, pixel)


def node(kind, size, offset=(0, 0), anchor="top_left", **extra):
    value = {"type": kind, "size": list(size), "offset": list(offset),
             "anchor_from": anchor, "anchor_to": anchor}
    value.update(extra)
    return value


def label(text, size, offset=(0, 0), scale=1.0, **extra):
    return node("label", size, offset, text=text, color=[0.86, 0.92, 0.98],
                font_size="normal", font_scale_factor=scale, text_alignment="left",
                shadow=False, layer=5, **extra)


def background(name):
    return node("image", ("100%", "100%"), texture="textures/ui/mercuryx_godeye/" + name,
                nineslice_size=4, layer=0)


def button(text, size, offset=(0, 0), accent=False):
    return node("button", size, offset, default_control="default", hover_control="hover",
                pressed_control="pressed", button_mappings=[], controls=[
                    {"default": background("accent" if accent else "button")},
                    {"hover": background("hover")}, {"pressed": background("accent")},
                    {"label": dict(label(text, ("100%-16px", 16), (8, "20%")),
                                   anchor_from="left_middle", anchor_to="left_middle")},
                ])


def entry_button():
    # Dedicated compact launcher: eye emblem, title, level and a subtle drag grip.
    return node("button", (88, 36), (-10, 28), anchor="top_right",
                is_handle_button_move_event=True, layer=20,
                default_control="default", hover_control="hover", pressed_control="pressed",
                button_mappings=[], controls=[
                    {"default": background("entry")},
                    {"hover": background("entry_hover")},
                    {"pressed": background("entry_pressed")},
                    {"eye": node("image", (26, 26), (5, 5),
                                 texture="textures/ui/mercuryx_godeye/eye", layer=3)},
                    {"label": dict(label("天眼", (38, 14), (35, 5)),
                                   color=[0.87, 0.99, 1.0], shadow=True)},
                    {"level": dict(label("LV.0", (38, 14), (35, 20)),
                                   color=[0.62, 0.93, 0.96], shadow=True)},
                    {"grip": node("image", (6, 14), (77, 11),
                                  texture="textures/ui/mercuryx_godeye/grip", layer=3)},
                ])


def entry_textures():
    texture("entry", (12, 29, 43, 236), (46, 111, 132, 255))
    texture("entry_hover", (18, 47, 62, 248), (96, 222, 225, 255))
    texture("entry_pressed", (24, 65, 79, 255), (157, 247, 241, 255))

    def eye(x, y):
        dx, dy = (x - 31.5) / 32, (y - 31.5) / 32
        radius = math.sqrt(dx * dx + dy * dy)
        if 0.87 < radius < 0.94:
            return (49, 123, 143, 220)
        if abs(dx) < 0.76 and abs(dy) < 0.36 * (1 - (dx / 0.76) ** 2):
            if (dx + 0.07) ** 2 + (dy + 0.07) ** 2 < 0.004:
                return (233, 255, 251, 255)
            if radius < 0.13:
                return (9, 27, 40, 255)
            if radius < 0.24:
                return (128, 255, 233, 255)
            return (60, 185, 198, 255)
        if abs(dx) < 0.035 and 0.55 < abs(dy) < 0.72:
            return (113, 223, 217, 255)
        return (0, 0, 0, 0)

    def grip(x, y):
        if any((x - px) ** 2 + (y - py) ** 2 <= 2
               for px in (4, 11) for py in (3, 8, 13)):
            return (86, 143, 159, 210)
        return (0, 0, 0, 0)

    png(RP / "textures/ui/mercuryx_godeye/eye.png", 64, eye)
    png(RP / "textures/ui/mercuryx_godeye/grip.png", 16, grip)


def generate():
    texture("panel", (13, 23, 38, 246), (51, 78, 97, 255))
    texture("button", (25, 41, 56, 245), (48, 70, 87, 255))
    texture("hover", (32, 66, 81, 255), (91, 191, 207, 255))
    texture("accent", (26, 87, 106, 255), (98, 216, 230, 255))
    texture("radar", (12, 22, 34, 232), (50, 83, 100, 240))
    entry_textures()
    levels = []
    for index, name in enumerate(("凡人", "微光", "夜瞳", "幽视", "灵视", "天眼", "真·夜瞳")):
        levels.append({"lv%d" % index: button("Lv.%d  %s" % (index, name),
                                             ("100%", "13.4%"), (0, "%s%%" % (index * 14.2)))})
    details = [
        {"name": label("夜瞳", ("100%", 20), scale=1.3)},
        {"description": dict(label("持续夜视，看清夜晚与洞穴。", ("100%", "20%"), (0, 24)),
                             color=[0.96, 0.98, 1.0], shadow=True)},
    ]
    for index, (key, text) in enumerate((("ore", "矿脉感知"), ("entity", "特殊生命"),
                                        ("hidden", "隐藏目标"), ("enhancement", "画面增强"),
                                        ("performance", "范围：均衡"))):
        option = button(text, ("100%", "12%"), (0, "%s%%" % (32 + index * 13.5)))
        # Use the existing button asset and native grayscale from startup;
        # disabled options must never depend on a separately loaded texture.
        for child in option["controls"]:
            for state, control in child.items():
                if state in ("default", "hover", "pressed"):
                    control["texture"] = "textures/ui/mercuryx_godeye/button"
                    control["grayscale"] = True
                elif state == "label":
                    control["text"] = "§7范围：未启用" if key == "performance" else "§7[关] " + text
        details.append({key: option})
    menu = node("panel", ("92%", "92%"), anchor="center", controls=[
        {"bg": background("panel")},
        {"title": label("天眼  /  GOD EYE", ("64%", 22), (14, 8), scale=1.2)},
        {"close": dict(button("关闭", (44, 24)), anchor_from="top_right", anchor_to="top_right", offset=[-10, 7])},
        # Full-size glyphs retain Chinese strokes at small GUI resolutions.
        {"current": dict(label("当前：凡人", ("75%", 18), (14, 32)),
                         color=[0.8, 0.97, 1.0], font_type="smooth", shadow=True)},
        {"body": node("panel", ("100%-28px", "100%-88px"), (14, 56), controls=[
            {"levels": node("panel", ("41%", "100%"), controls=levels)},
            {"detail": node("panel", ("54%", "100%"), ("46%", 0), controls=details)},
        ])},
        {"notice": dict(label("设置随世界保存", ("100%-28px", 20)),
                        color=[0.95, 0.97, 1.0], font_type="smooth", shadow=True,
                        anchor_from="bottom_left", anchor_to="bottom_left", offset=[14, -5])},
    ])
    radar = node("panel", (252, 176), (8, 59), controls=[
        {"bg": background("radar")},
        {"status": dict(label("探测中", (236, 20), (8, 6)),
                        color=[0.8, 0.97, 1.0], shadow=True)},
    ] + [{"target%d" % i: dict(label("", (236, 34), (8, 32 + i * 36)),
                              color=[0.96, 0.98, 1.0], shadow=True)} for i in range(4)])
    write_json(RP / "ui/mercuryx_godeye.json", {
        "namespace": "mercuryx_godeye",
        "hud@common.base_screen": {"is_showing_menu": False, "absorbs_input": False,
                                   "controls": [{"root": node("panel", ("100%", "100%"), controls=[
                                       {"entry": entry_button()},
                                       {"radar": radar}])}]},
        "menu@common.base_screen": {"is_showing_menu": True, "absorbs_input": True,
                                    "render_game_behind": True, "controls": [{"panel": menu}]},
    })
    write_json(RP / "ui/_ui_defs.json", {"ui_defs": ["ui/mercuryx_godeye.json"]})
    # A geometric eye symbol, drawn from code rather than a copied brand asset.
    def icon(x, y):
        dx, dy = (x - 63.5) / 64, (y - 63.5) / 64
        r = math.sqrt(dx * dx + dy * dy)
        if 0.72 < r < 0.76:
            return (54, 107, 129, 255)
        if abs(dy) < 0.33 * (1 - (dx / 0.7) ** 2) and abs(dx) < 0.7:
            if r < 0.16:
                return (12, 25, 43, 255)
            if r < 0.24:
                return (105, 244, 237, 255)
            return (56, 148, 175, 255)
        return (13, 23, 38, 255)
    for pack in (ROOT / "behavior_pack_qbUAm8gp", RP):
        png(pack / "pack_icon.png", 128, icon)


if __name__ == "__main__":
    generate()
    print("Generated GodEye UI, launcher textures, and pack icons.")
