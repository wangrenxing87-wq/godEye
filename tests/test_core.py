# -*- coding: utf-8 -*-
from __future__ import division
import os
import sys
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "behavior_pack_qbUAm8gp"))
from godEyeScripts import config, core
from godEyeScripts.effects import NightVisionLease


class Clock(object):
    def __init__(self): self.now = 100.0
    def __call__(self): return self.now
    def advance(self, seconds): self.now += seconds


class CoreTests(unittest.TestCase):
    def test_settings_rejects_invalid_and_mutable_values(self):
        for level in (-1, 7, True, "6", None, [], {}):
            self.assertEqual(core.settings({"level": level})["level"], 0)
        value = core.settings({"level": 6, "ore_enabled": "false", "performance": []})
        self.assertEqual(value["level"], 6)
        self.assertTrue(value["ore_enabled"])
        self.assertEqual(value["performance"], "balanced")
        value["level"] = 1
        self.assertEqual(config.DEFAULT_SETTINGS["level"], 0)

    def test_all_seven_levels_and_optional_filters(self):
        for level in range(7):
            caps = core.capabilities({"level": level})
            self.assertEqual(caps["night"], level >= 2)
            self.assertEqual(caps["entities"], level >= 4)
            self.assertEqual(caps["hidden"], level >= 5)
            self.assertEqual(caps["markers"], level == 6)
        self.assertFalse(core.capabilities({"level": 6, "ore_enabled": False})["ore"])
        self.assertEqual(core.capabilities({"level": 6, "performance": "quality"})["radius"], 32)

    def test_negative_coordinates_and_spherical_tiles(self):
        self.assertEqual(core.tile_key(2, (-0.1, -8, 8)), (2, -1, -1, 1))
        keys = core.nearby_tiles(1, (0, 0, 0), 16)
        self.assertTrue(keys)
        self.assertTrue(all(k[0] == 1 and core.tile_distance2(k, (0, 0, 0)) <= 256 for k in keys))
        self.assertNotIn((1, 2, 2, 2), keys)

    def test_mineral_clusters_cross_tiles_and_variants(self):
        blocks = [((7, 0, 0), "minecraft:diamond_ore"),
                  ((8, 0, 0), "minecraft:deepslate_diamond_ore"),
                  ((8, 1, 1), "minecraft:diamond_ore"),
                  ((0, 0, 2), "minecraft:chest")]
        targets = core.group_blocks(blocks, config.BLOCKS, (0, 0, 0))
        self.assertEqual(len(targets), 3)
        self.assertEqual(sorted(t["count"] for t in targets), [1, 1, 2])
        self.assertEqual(targets, core.group_blocks(list(reversed(blocks)), config.BLOCKS, (0, 0, 0)))

    def test_level4_does_not_leak_mineral_coordinates_or_type(self):
        targets = core.group_blocks([((8, 0, 0), "minecraft:diamond_ore"),
                                     ((2, 0, 0), "minecraft:coal_ore")], config.BLOCKS, (0, 0, 0))
        public = core.public_targets(targets, {"level": 4}, (0, 0, 0), 0)
        self.assertEqual(len(public), 1)
        self.assertTrue(public[0]["coarse"])
        self.assertNotIn("pos", public[0])
        self.assertNotIn("count", public[0])
        self.assertNotIn("diamond", repr(public))
        self.assertEqual(len(core.public_targets(targets, {"level": 5}, (0, 0, 0), 0)), 2)

    def test_bearings_rotation_and_vertical_distance(self):
        self.assertEqual(core.bearing((0, 0, 0), (0, 0, 3), 0), (u"前方", 3))
        self.assertEqual(core.bearing((0, 0, 0), (3, 0, 0), 0)[0], u"左侧")
        self.assertEqual(core.bearing((0, 0, 0), (0, 4, 3), 0)[1], 5)
        self.assertEqual(core.bearing((0, 0, 0), (-3, 0, 0), 90)[0], u"前方")

    def test_registry_dimensions_privacy_expiry_and_update(self):
        clock = Clock()
        registry = core.TargetRegistry(clock)
        registry.register("other:door", "entrance", 0, (1, 2, 3), u"入口", ["a"], 2)
        self.assertEqual(len(registry.query("a", 0, (0, 0, 0), 16)), 1)
        self.assertEqual(registry.query("b", 0, (0, 0, 0), 16), [])
        self.assertEqual(registry.query("a", 1, (0, 0, 0), 16), [])
        clock.advance(3)
        self.assertEqual(registry.query("a", 0, (0, 0, 0), 16), [])
        self.assertEqual(registry.targets, {})
        with self.assertRaises(ValueError):
            registry.register("x:bad", "quest", 0, (float("nan"), 0, 0), "bad")
        with self.assertRaises(ValueError):
            registry.register("x:ore", "ore", 0, (0, 0, 0), "use RegisterOre")


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.cache = core.ScanCache(self.clock, limit=64, ttl=10)

    def test_round_robin_shared_cache_and_budget(self):
        self.cache.watch("a", 0, (4, 4, 4), 0)
        self.cache.watch("b", 0, (4, 4, 4), 0)
        calls = []
        self.cache.pump(lambda key: calls.append(key) or [], max_jobs=10)
        self.assertEqual(len(calls), 1)
        self.cache.watch("c", 1, (4, 4, 4), 0)
        self.cache.pump(lambda key: calls.append(key) or [], max_jobs=1)
        self.assertEqual(calls[-1][0], 1)
        self.cache.watch("a", 0, (0, 0, 0), 16)
        def slow(key):
            self.clock.advance(0.005)
            return []
        self.assertEqual(self.cache.pump(slow, max_jobs=10, seconds=0.002), 1)

    def test_unloaded_is_not_empty_success_and_retries(self):
        self.cache.watch("a", 0, (4, 4, 4), 0)
        self.cache.pump(lambda key: None)
        self.assertEqual(self.cache.snapshot("a", (4, 4, 4), 1)[1:3], (0, 1))
        self.assertEqual(self.cache.pump(lambda key: []), 0)
        self.clock.advance(2)
        self.assertEqual(self.cache.pump(lambda key: []), 1)
        self.assertEqual(self.cache.snapshot("a", (4, 4, 4), 1)[1:3], (1, 1))

    def test_expiry_invalidation_movement_and_clear(self):
        self.cache.watch("a", 0, (4, 4, 4), 0)
        self.cache.pump(lambda key: [((4, 4, 4), "minecraft:diamond_ore")])
        self.assertEqual(len(self.cache.snapshot("a", (4, 4, 4), 2)[0]), 1)
        self.clock.advance(11)
        self.assertEqual(self.cache.snapshot("a", (4, 4, 4), 2)[1], 0)
        self.cache.invalidate(0, (4, 4, 4))
        self.assertEqual(len(self.cache.cache), 0)
        self.cache.pump(lambda key: [])
        self.cache.watch("a", 1, (4, 4, 4), 0)
        self.assertEqual(len(self.cache.cache), 0)
        self.cache.unwatch("a")
        self.assertFalse(self.cache.interests)

    def test_cache_memory_bound_and_spherical_result_filter(self):
        self.cache.limit = 3
        self.cache.watch("a", 0, (4, 4, 4), 16)
        self.cache.pump(lambda key: [((4, 4, 4), "a"), ((7, 7, 7), "b")], max_jobs=10)
        self.assertEqual(len(self.cache.cache), 3)
        result = self.cache.snapshot("a", (4, 4, 4), 2)
        self.assertTrue(all(item[1] == "a" for item in result[0]))


class FakeEffect(object):
    def __init__(self, clock):
        self.clock = clock
        self.expires = 0
        self.amplifier = 0
        self.lease = None
        self.removals = 0

    def GetAllEffects(self):
        duration = int(self.expires - self.clock())
        return [{"effectName": "night_vision", "duration": duration, "amplifier": self.amplifier}] if duration > 0 else []

    def AddEffectToEntity(self, name, seconds, amplifier, particles):
        self.expires = self.clock() + seconds
        self.amplifier = amplifier
        if self.lease:
            self.lease.observe(seconds, amplifier)
        return True

    def RemoveEffectFromEntity(self, name):
        self.expires = 0
        self.removals += 1
        if self.lease:
            self.lease.removed()
        return True


class EffectTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.component = FakeEffect(self.clock)
        self.lease = NightVisionLease(self.component, self.clock)
        self.component.lease = self.lease

    def test_continuous_refresh_and_immediate_own_disable(self):
        for _ in range(300):
            self.lease.maintain()
            self.assertGreater(self.component.GetAllEffects()[0]["duration"], 20)
            self.clock.advance(1)
        self.lease.release()
        self.assertEqual(self.component.GetAllEffects(), [])

    def test_long_external_effect_is_untouched(self):
        self.component.AddEffectToEntity("night_vision", 180, 0, True)
        self.lease.maintain()
        self.lease.release()
        self.assertEqual(self.component.removals, 0)
        self.assertEqual(self.component.GetAllEffects()[0]["duration"], 180)

    def test_short_external_effect_restored_with_elapsed_time(self):
        self.component.AddEffectToEntity("night_vision", 20, 1, True)
        self.lease.maintain()
        self.clock.advance(3)
        self.lease.release()
        self.assertEqual(self.component.GetAllEffects()[0]["duration"], 17)
        self.assertEqual(self.component.amplifier, 1)

    def test_external_replacement_during_active_lease_is_not_removed(self):
        self.lease.maintain()
        self.component.AddEffectToEntity("night_vision", 180, 0, True)
        self.lease.release()
        self.assertEqual(self.component.removals, 0)

    def test_milk_or_death_then_reapply(self):
        self.lease.maintain()
        self.component.RemoveEffectFromEntity("night_vision")
        self.lease.maintain()
        self.assertTrue(self.component.GetAllEffects())

    def test_persisted_effect_lease_can_be_disabled_after_world_reopen(self):
        saved = []
        self.lease.save = saved.append
        self.lease.maintain()
        self.clock.advance(7)
        # The engine saves 38 seconds and freezes effects while the world is off.
        current_duration = self.component.GetAllEffects()[0]["duration"]
        self.clock.advance(600)
        self.component.expires = self.clock() + current_duration
        recovered = NightVisionLease(self.component, self.clock)
        recovered.restore(saved[-1])
        recovered.release()
        self.assertEqual(self.component.GetAllEffects(), [])

    def test_external_replacement_invalidates_persisted_ownership(self):
        saved = []
        self.lease.save = saved.append
        self.lease.maintain()
        self.component.AddEffectToEntity("night_vision", 180, 0, True)
        self.assertIsNone(saved[-1])

    def test_reopen_delayed_native_effect_replay_keeps_ownership(self):
        self.lease.maintain()
        saved = self.lease.export_state()
        self.clock.advance(7)
        recovered = NightVisionLease(self.component, self.clock)
        recovered.restore(saved)
        self.clock.advance(0.2)
        recovered.observe(self.component.GetAllEffects()[0]["duration"], 0)
        recovered.release()
        self.assertEqual(self.component.GetAllEffects(), [])

    def test_reopen_external_replacement_is_not_a_native_replay(self):
        self.lease.maintain()
        saved = self.lease.export_state()
        recovered = NightVisionLease(self.component, self.clock)
        recovered.restore(saved)
        self.component.lease = recovered
        self.component.AddEffectToEntity("night_vision", 180, 0, True)
        recovered.release()
        self.assertEqual(self.component.GetAllEffects()[0]["duration"], 180)


if __name__ == "__main__":
    unittest.main()
