# -*- coding: utf-8 -*-
"""Shared data only. No client/server imports. Python 2.7 compatible."""
NAMESPACE = "mercuryx_godeye"
VERSION = "1.0.0"
SERVER_SYSTEM = "GodEyeServer"
CLIENT_SYSTEM = "GodEyeClient"
DATA_KEY = "mercuryx_godeye:settings_v1"
EFFECT_DATA_KEY = "mercuryx_godeye:night_lease_v1"
STATE_EVENT = "GodEyeState"
REQUEST_EVENT = "GodEyeRequest"
TARGET_EVENT = "GodEyeTargets"
UI_EVENT = "GodEyeOpen"
REQUEST_INTERVAL_TICKS = 6

LEVELS = (
    (u"凡人", u"关闭天眼，恢复普通视觉。"),
    (u"微光", u"轻度提亮暗处，保留夜晚氛围。"),
    (u"夜瞳", u"持续夜视，看清夜晚与洞穴。"),
    (u"幽视", u"持续夜视，增强暗处辨识度。"),
    (u"灵视", u"感知特殊生命与附近稀有矿脉。"),
    (u"天眼", u"定位矿脉、容器、机关与已接入的隐藏目标。"),
    (u"真·夜瞳", u"融合全部感知，在视野中标记目标。"),
)
DEFAULT_SETTINGS = {
    "schema_version": 1, "level": 0, "ore_enabled": True,
    "entity_enabled": True, "hidden_enabled": True,
    "enhancement_enabled": True, "performance": "balanced",
}
PERFORMANCE = {
    "economy": {"radius": 16, "entity_radius": 16, "targets": 6},
    "balanced": {"radius": 24, "entity_radius": 24, "targets": 10},
    "quality": {"radius": 32, "entity_radius": 32, "targets": 12},
}
TILE_SIZE = 8
# Half-open build ranges in the supported vanilla dimensions. Custom dimensions
# can supply their own range with RegisterDimensionBounds; unknown ids are uncut.
DIMENSION_BOUNDS = {0: (-64, 320), 1: (0, 128), 2: (0, 256)}
CACHE_LIMIT = 1536
CACHE_TTL = 20.0
SCAN_JOBS_PER_TICK = 2
SCAN_SECONDS_PER_TICK = 0.002
MAX_ENTITY_CHECKS = 32
EFFECT_SECONDS = 45
EFFECT_REFRESH_AT = 25
EFFECT_CHECK_TICKS = 30

# Values: display label, rare (Lv.4), category.
BLOCKS = {}
for _name, _label, _rare in (
        ("coal", u"煤矿", False), ("copper", u"铜矿", False),
        ("iron", u"铁矿", False), ("gold", u"金矿", True),
        ("diamond", u"钻石矿", True), ("redstone", u"红石矿", False),
        ("lapis", u"青金石矿", True), ("emerald", u"绿宝石矿", True)):
    for _prefix in ("", "deepslate_"):
        BLOCKS["minecraft:" + _prefix + _name + "_ore"] = {
            "label": _label, "rare": _rare, "category": "ore", "group": _name}
for _name, _label, _rare in (
        ("nether_gold_ore", u"下界金矿", False),
        ("quartz_ore", u"下界石英", False),
        ("nether_quartz_ore", u"下界石英", False),
        ("ancient_debris", u"远古残骸", True),
        ("lit_redstone_ore", u"红石矿", False),
        ("lit_deepslate_redstone_ore", u"红石矿", False)):
    BLOCKS["minecraft:" + _name] = {
        "label": _label, "rare": _rare, "category": "ore",
        "group": "redstone" if "redstone" in _name else _name}
for _name, _label, _category in (
        ("chest", u"箱子", "container"),
        ("trapped_chest", u"陷阱箱", "container"),
        ("ender_chest", u"末影箱", "container"),
        ("barrel", u"木桶", "container"),
        ("mob_spawner", u"刷怪笼", "mechanism"),
        ("lever", u"拉杆", "mechanism"),
        ("tripwire_hook", u"绊线钩", "mechanism"),
        ("stone_pressure_plate", u"石质压力板", "mechanism"),
        ("wooden_pressure_plate", u"木质压力板", "mechanism")):
    BLOCKS["minecraft:" + _name] = {
        "label": _label, "rare": False, "category": _category, "group": _name}

ENTITY_TYPES = {
    "minecraft:evocation_illager": u"唤魔者",
    "minecraft:evoker": u"唤魔者", "minecraft:vex": u"恼鬼",
    "minecraft:witch": u"女巫", "minecraft:elder_guardian": u"远古守卫者",
    "minecraft:warden": u"监守者", "minecraft:wither": u"凋灵",
    "minecraft:ender_dragon": u"末影龙", "minecraft:npc": u"NPC",
}
TAG_CATEGORIES = {
    "nightvision:hidden": "hidden", "nightvision:spirit": "spirit",
    "nightvision:special": "special", "nightvision:quest_target": "quest",
    "nightvision:hidden_chest": "container",
    "nightvision:hidden_mechanism": "mechanism",
}
for _tag, _category in list(TAG_CATEGORIES.items()):
    TAG_CATEGORIES[NAMESPACE + ":" + _tag.split(":", 1)[1]] = _category
CATEGORY_LABELS = {
    "hidden": u"隐藏目标", "spirit": u"灵体", "special": u"特殊生命",
    "quest": u"任务目标", "container": u"隐藏容器", "mechanism": u"机关",
    "entrance": u"秘密入口", "ore": u"矿脉",
}
