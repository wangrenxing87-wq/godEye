# -*- coding: utf-8 -*-
"""Engine independent algorithms; exercised under Python 2.7 and Python 3."""
from __future__ import division
import math
import time
from collections import OrderedDict, deque
from godEyeScripts import config

PENDING = object()

try:
    INTEGER_TYPES = (int, long)
    STRING_TYPES = (basestring,)
    TEXT_TYPE = unicode
except NameError:
    INTEGER_TYPES = (int,)
    STRING_TYPES = (str,)
    TEXT_TYPE = str


def display_text(value):
    """Engine names may be UTF-8 bytes on Python 2; UI composition uses Unicode."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value if isinstance(value, TEXT_TYPE) else TEXT_TYPE(value)


def native_id(value):
    """C++ string arguments use UTF-8 str on the Python 2 ModSDK runtime."""
    return value.encode("utf-8") if TEXT_TYPE is not str and isinstance(value, TEXT_TYPE) else value


def settings(value):
    result = dict(config.DEFAULT_SETTINGS)
    if not isinstance(value, dict):
        return result
    level = value.get("level")
    if type(level) in INTEGER_TYPES and 0 <= level <= 6:
        result["level"] = level
    for key in ("ore_enabled", "entity_enabled", "hidden_enabled", "enhancement_enabled"):
        if type(value.get(key)) is bool:
            result[key] = value[key]
    if isinstance(value.get("performance"), STRING_TYPES) and value["performance"] in config.PERFORMANCE:
        result["performance"] = value["performance"]
    return result


def capabilities(value):
    value = settings(value)
    level = value["level"]
    perf = config.PERFORMANCE[value["performance"]]
    return {
        "night": level >= 2,
        "enhance": value["enhancement_enabled"] and (level == 1 or level >= 3),
        "entities": level >= 4 and value["entity_enabled"],
        "ore": level >= 4 and value["ore_enabled"],
        "hidden": level >= 5 and value["hidden_enabled"],
        "precise": level >= 5, "markers": level == 6,
        "radius": min(16, perf["radius"]) if level == 4 else perf["radius"],
        "entity_radius": perf["entity_radius"], "limit": perf["targets"],
    }


def distance2(a, b):
    return sum((a[i] - b[i]) ** 2 for i in range(3))


def valid_pos(pos):
    if not isinstance(pos, (tuple, list)) or len(pos) != 3:
        return False
    try:
        return all(not isinstance(v, bool) and isinstance(v, INTEGER_TYPES + (float,))
                   and not math.isnan(v) and not math.isinf(v) for v in pos)
    except (TypeError, ValueError, OverflowError):
        return False


def tile_key(dimension, pos):
    return (dimension,) + tuple(int(math.floor(v / config.TILE_SIZE)) for v in pos)


def tile_bounds(key):
    start = tuple(v * config.TILE_SIZE for v in key[1:])
    return start, tuple(v + config.TILE_SIZE - 1 for v in start)


def tile_distance2(key, pos):
    start, end = tile_bounds(key)
    return sum(max(start[i] - pos[i], 0, pos[i] - (end[i] + 1)) ** 2 for i in range(3))


def nearby_tiles(dimension, pos, radius, bounds=None):
    low = tile_key(dimension, tuple(v - radius for v in pos))
    high = tile_key(dimension, tuple(v + radius for v in pos))
    keys = []
    for x in range(low[1], high[1] + 1):
        for y in range(low[2], high[2] + 1):
            for z in range(low[3], high[3] + 1):
                key = (dimension, x, y, z)
                if bounds and (y * config.TILE_SIZE >= bounds[1] or (y + 1) * config.TILE_SIZE <= bounds[0]):
                    continue
                if tile_distance2(key, pos) <= radius * radius:
                    keys.append(key)
    return sorted(keys, key=lambda key: (tile_distance2(key, pos), key))


class ScanCache(object):
    """Small native queries, shared tiles, round robin players, bounded memory.

    reader returns a list of (world_position, block_id), or None if not loaded.
    A failed read is never an empty successful scan. Time budget is checked
    between native calls; a single native call cannot be interrupted.
    """
    def __init__(self, clock=None, limit=config.CACHE_LIMIT, ttl=config.CACHE_TTL):
        self.clock = clock or time.time
        self.limit, self.ttl = limit, ttl
        self.cache = OrderedDict()
        self.interests = OrderedDict()
        self.failed_until = {}
        self.cursor = 0
        self.last_cost = 0.0

    def watch(self, player, dimension, pos, radius, bounds=None):
        self.interests[player] = nearby_tiles(dimension, pos, radius, bounds)
        active = set(k for keys in self.interests.values() for k in keys)
        for key in list(self.cache):
            if key not in active:
                del self.cache[key]
        self.failed_until = dict((k, v) for k, v in self.failed_until.items() if k in active)

    def unwatch(self, player):
        self.interests.pop(player, None)
        if not self.interests:
            self.cache.clear()
            self.failed_until.clear()

    def invalidate(self, dimension, pos):
        key = tile_key(dimension, pos)
        self.cache.pop(key, None)
        self.failed_until.pop(key, None)

    def clear(self):
        self.cache.clear()
        self.interests.clear()
        self.failed_until.clear()

    def _next(self, now):
        players = list(self.interests)
        for _ in players:
            player = players[self.cursor % len(players)]
            self.cursor += 1
            for key in self.interests[player]:
                entry = self.cache.get(key)
                if (entry is None or now - entry[0] >= self.ttl) and self.failed_until.get(key, 0) <= now:
                    return key
        return None

    def pump(self, reader, max_jobs=config.SCAN_JOBS_PER_TICK,
             seconds=config.SCAN_SECONDS_PER_TICK):
        begin = self.clock()
        count = 0
        while count < max_jobs:
            now = self.clock()
            if count and now - begin >= seconds:
                break
            key = self._next(now)
            if key is None:
                break
            result = reader(key)
            count += 1
            if result is PENDING:
                continue
            elif result is None:
                self.failed_until[key] = now + 2.0
                self.cache.pop(key, None)
            else:
                self.cache.pop(key, None)
                self.cache[key] = (now, result)
                self.failed_until.pop(key, None)
                while len(self.cache) > self.limit:
                    self.cache.popitem(last=False)
        self.last_cost = self.clock() - begin
        return count

    def snapshot(self, player, pos, radius, max_blocks=4096):
        now = self.clock()
        keys = self.interests.get(player, [])
        blocks, completed = [], 0
        truncated = False
        for key in keys:
            entry = self.cache.get(key)
            if entry is None or now - entry[0] >= self.ttl:
                continue
            completed += 1
            for block in entry[1]:
                center = tuple(v + 0.5 for v in block[0])
                if distance2(center, pos) <= radius * radius:
                    if len(blocks) < max_blocks:
                        blocks.append(block)
                    else:
                        truncated = True
        return blocks, completed, len(keys), truncated


def group_blocks(blocks, catalog, pos, include_ore=True, include_hidden=True):
    ores, targets = {}, []
    for point, name in blocks:
        meta = catalog.get(name)
        if not meta:
            continue
        point = tuple(point)
        if meta["category"] == "ore":
            if include_ore:
                ores[point] = (name, meta)
        elif include_hidden:
            targets.append({"id": "block:%s:%s" % (name, point),
                            "category": meta["category"], "label": meta["label"],
                            "pos": [v + 0.5 for v in point], "count": 1})
    for seed in sorted(ores):  # Stable ids; avoid repeated O(n) minimum searches.
        if seed not in ores:
            continue
        name, meta = ores.pop(seed)
        todo, members = [seed], []
        while todo:
            point = todo.pop()
            members.append(point)
            for axis in range(3):
                for step in (-1, 1):
                    neighbor = list(point)
                    neighbor[axis] += step
                    neighbor = tuple(neighbor)
                    item = ores.get(neighbor)
                    if item and item[1]["group"] == meta["group"]:
                        ores.pop(neighbor)
                        todo.append(neighbor)
        center = tuple(sum(p[i] + 0.5 for p in members) / len(members) for i in range(3))
        # Choose an actual ore block near the centroid, not an empty cavity.
        anchor = min(members, key=lambda p: distance2(tuple(v + 0.5 for v in p), center))
        targets.append({"id": "ore:%s:%s" % (meta["group"], seed),
                        "category": "ore", "label": meta["label"],
                        "pos": [v + 0.5 for v in anchor], "count": len(members),
                        "rare": meta["rare"]})
    return sorted(targets, key=lambda t: (distance2(t["pos"], pos), t["id"]))


def bearing(origin, target, yaw):
    dx, dy, dz = (target[i] - origin[i] for i in range(3))
    angle = (math.degrees(math.atan2(-dx, dz)) - yaw + 180) % 360 - 180
    names = (u"前方", u"右前方", u"右侧", u"右后方", u"后方", u"左后方", u"左侧", u"左前方")
    direction = names[int(math.floor((angle + 22.5) / 45.0)) % 8]
    if abs(dy) >= 4:
        direction += u"·上方" if dy > 0 else u"·下方"
    return direction, math.sqrt(dx * dx + dy * dy + dz * dz)


def public_targets(targets, value, pos, yaw):
    caps = capabilities(value)
    result = []
    for target in targets:
        category = target["category"]
        if category == "ore":
            if not caps["ore"] or (not caps["precise"] and not target.get("rare")):
                continue
        elif category in ("special", "spirit"):
            if not caps["entities"]:
                continue
        elif not caps["hidden"]:
            continue
        item = dict(target)
        if not caps["precise"] and category == "ore":
            direction, distance = bearing(pos, item["pos"], yaw)
            # Do not leak position, mineral type, size or coordinate-based id.
            item = {"id": "sense:%d" % len(result), "category": "ore",
                    "label": u"稀有矿脉", "direction": direction,
                    "distance": max(4, int(math.ceil(distance / 4.0)) * 4), "coarse": True}
        result.append(item)
        if len(result) >= caps["limit"]:
            break
    return result


class TargetRegistry(object):
    """Server-only public extension point; never accepts client registrations."""
    def __init__(self, clock=None):
        self.clock = clock or time.time
        self.targets = {}

    def register(self, target_id, category, dimension, pos, label, players=None, ttl=0):
        if not isinstance(target_id, STRING_TYPES) or ":" not in target_id or len(target_id) > 128:
            raise ValueError("Target id must be namespaced and at most 128 characters")
        if category not in config.CATEGORY_LABELS or category == "ore" or not valid_pos(pos):
            raise ValueError("Invalid category or position")
        if type(dimension) not in INTEGER_TYPES:
            raise ValueError("Invalid dimension")
        if not isinstance(label, STRING_TYPES) or not label or len(label) > 80:
            raise ValueError("Label must contain 1..80 characters")
        if not isinstance(ttl, INTEGER_TYPES + (float,)) or ttl < 0 or math.isnan(ttl) or math.isinf(ttl):
            raise ValueError("Invalid TTL")
        if players is not None and (not isinstance(players, (list, tuple, set)) or
                                   not all(isinstance(p, STRING_TYPES) for p in players)):
            raise ValueError("players must be player id list or None")
        if len(self.targets) >= 2048 and target_id not in self.targets:
            raise ValueError("Target registry full")
        self.targets[target_id] = {
            "id": target_id, "category": category, "dimension": dimension,
            "pos": tuple(pos), "label": display_text(label), "players": None if players is None else set(players),
            "expires": self.clock() + ttl if ttl else 0,
        }

    def unregister(self, target_id):
        return self.targets.pop(target_id, None) is not None

    def query(self, player, dimension, pos, radius):
        now = self.clock()
        result = []
        for key, item in list(self.targets.items()):
            if item["expires"] and item["expires"] <= now:
                del self.targets[key]
                continue
            if item["dimension"] != dimension or distance2(item["pos"], pos) > radius * radius:
                continue
            if item["players"] is not None and player not in item["players"]:
                continue
            result.append(dict((k, item[k]) for k in ("id", "category", "pos", "label")))
        return result
