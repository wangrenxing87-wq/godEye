# -*- coding: utf-8 -*-
import unittest
from tests.test_core import Clock
from godEyeScripts import config, core
from godEyeScripts.scanner import TileReader


class EmptyPaletteEngine(object):
    def __init__(self):
        self.height = -61
        self.blocks = {}
        self.height_calls = 0
        self.block_calls = 0
        self.loaded = True
        self.fail_point = None

    def GetBlockPaletteBetweenPos(self, dimension, start, end): return None
    def GetLoadedChunks(self, dimension): return [(0, 0)] if self.loaded else []
    def GetTopBlockHeight(self, pos, dimension):
        self.height_calls += 1
        return self.height
    def GetBlockNew(self, pos, dimension):
        self.block_calls += 1
        return None if pos == self.fail_point else {"name": self.blocks.get(pos, "minecraft:air")}


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.native = EmptyPaletteEngine()
        self.clock = Clock()
        self.reader = TileReader(self.native, self.native, self.native, config.BLOCKS, self.clock)

    def test_empty_air_palette_completes_without_false_unloaded_state(self):
        key = (0, 0, 0, 0)
        self.assertIs(self.reader.read(key), core.PENDING)
        self.assertEqual(self.native.height_calls, 32)
        self.assertEqual(self.reader.read(key), [])
        self.assertEqual(self.native.height_calls, 64)
        self.assertEqual(self.native.block_calls, 0)
        # Higher tiles reuse the exact same column certificate.
        self.assertEqual(self.reader.read((0, 0, 1, 0)), [])
        self.assertEqual(self.native.height_calls, 64)

    def test_underground_fallback_is_bounded_and_finds_ore(self):
        self.native.height = 90
        self.native.blocks[(7, 7, 7)] = "minecraft:diamond_ore"
        key = (0, 0, 0, 0)
        for _ in range(2):
            self.assertIs(self.reader.read(key), core.PENDING)
        for _ in range(7):
            previous = self.native.block_calls
            self.assertIs(self.reader.read(key), core.PENDING)
            self.assertEqual(self.native.block_calls - previous, 64)
        result = self.reader.read(key)
        self.assertEqual(result, [((7, 7, 7), "minecraft:diamond_ore")])
        self.assertEqual(self.native.block_calls, 512)
        self.assertFalse(self.reader.work)

    def test_failed_point_query_never_reports_empty(self):
        self.native.height = 90
        self.native.fail_point = (0, 0, 0)
        key = (0, 0, 0, 0)
        self.reader.read(key)
        self.reader.read(key)
        self.assertIsNone(self.reader.read(key))
        self.assertNotIn(key, self.reader.work)

    def test_height_certificate_invalidates_on_world_edits(self):
        key = (0, 0, 0, 0)
        self.reader.read(key)
        self.reader.read(key)
        self.reader.invalidate(key)
        self.native.height = 90
        self.assertIs(self.reader.read(key), core.PENDING)
        self.reader.retain([])
        self.assertFalse(self.reader.columns)
        self.assertFalse(self.reader.work)
        self.assertFalse(self.reader.loaded)

    def test_build_bounds_clip_void_and_pending_respects_job_budget(self):
        keys = core.nearby_tiles(0, (0, -60, 0), 24, (-64, 320))
        self.assertTrue(keys)
        self.assertTrue(all(k[2] >= -8 for k in keys))
        cache = core.ScanCache(self.clock)
        cache.watch("a", 0, (4, 4, 4), 0)
        self.assertEqual(cache.pump(lambda key: core.PENDING, max_jobs=2), 2)
        self.assertFalse(cache.failed_until)
        self.assertEqual(cache.snapshot("a", (4, 4, 4), 1)[1:3], (0, 1))


if __name__ == "__main__":
    unittest.main()
