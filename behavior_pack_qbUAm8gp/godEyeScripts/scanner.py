# -*- coding: utf-8 -*-
"""Native palette reader with bounded, complete handling of empty regions."""
import time
from godEyeScripts import config, core


class TileReader(object):
    def __init__(self, block, block_info, chunks, catalog, clock=None):
        self.block, self.info, self.chunks = block, block_info, chunks
        self.catalog = catalog
        self.clock = clock or time.time
        self.loaded = {}
        self.columns = {}
        self.work = {}

    def retain(self, keys):
        active = set(keys)
        columns = set((k[0], k[1], k[3]) for k in active)
        dimensions = set(k[0] for k in active)
        self.work = dict((k, v) for k, v in self.work.items() if k in active)
        self.columns = dict((k, v) for k, v in self.columns.items() if k in columns)
        self.loaded = dict((k, v) for k, v in self.loaded.items() if k in dimensions)

    def invalidate(self, key):
        self.work.pop(key, None)
        self.columns.pop((key[0], key[1], key[3]), None)

    def read(self, key):
        start, end = core.tile_bounds(key)
        dimension = key[0]
        now = self.clock()
        loaded = self.loaded.get(dimension)
        if loaded is None or now - loaded[0] >= 1:
            loaded = (now, set(tuple(p) for p in self.chunks.GetLoadedChunks(dimension) or []))
            self.loaded[dimension] = loaded
        if (start[0] // 16, start[2] // 16) not in loaded[1]:
            self.work.pop(key, None)
            return None
        column_key = (dimension, key[1], key[3])
        heights = self.columns.get(column_key)
        if heights and now - heights[0] < config.CACHE_TTL and start[1] > heights[1]:
            return []
        task = self.work.get(key)
        if task is None:
            palette = self.block.GetBlockPaletteBetweenPos(dimension, start, end)
            if palette is not None:
                found = []
                for name in self.catalog:
                    for relative in palette.GetLocalPosListOfBlocks(name) or []:
                        found.append((tuple(start[i] + relative[i] for i in range(3)), name))
                return found
            # The real engine also returns None for all-air palettes. Certify
            # above-surface air using ALL 64 columns, never just the corners.
            task = {"mode": "columns", "cursor": 0, "heights": [], "found": []}
            self.work[key] = task
        if task["mode"] == "columns":
            for _ in range(32):
                cursor = task["cursor"]
                if cursor >= 64:
                    break
                height = self.info.GetTopBlockHeight((start[0] + cursor % 8, start[2] + cursor // 8), dimension)
                if height is None:
                    self.work.pop(key, None)
                    return None
                task["heights"].append(height)
                task["cursor"] += 1
            if task["cursor"] < 64:
                return core.PENDING
            highest = max(task["heights"])
            self.columns[column_key] = (now, highest)
            if start[1] > highest:
                self.work.pop(key, None)
                return []
            task["mode"], task["cursor"] = "blocks", 0
            return core.PENDING
        # Underground empty cavities and other palette failures get a complete
        # point-query fallback, amortized over ticks. Never report a failed read
        # as an empty successful result.
        for _ in range(64):
            cursor = task["cursor"]
            if cursor >= 512:
                break
            point = (start[0] + cursor % 8, start[1] + (cursor // 8) % 8, start[2] + cursor // 64)
            block = self.info.GetBlockNew(point, dimension)
            if not isinstance(block, dict) or not block.get("name"):
                self.work.pop(key, None)
                return None
            if block["name"] in self.catalog:
                task["found"].append((point, block["name"]))
            task["cursor"] += 1
        if task["cursor"] < 512:
            return core.PENDING
        self.work.pop(key, None)
        return task["found"]
