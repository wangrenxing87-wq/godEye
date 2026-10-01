# -*- coding: utf-8 -*-
"""Conservative lease for the shared vanilla night_vision effect slot."""
import math
import time
from godEyeScripts import config


class NightVisionLease(object):
    def __init__(self, component, clock=None, save=None):
        self.component = component
        self.clock = clock or time.time
        self.owned_until = 0
        self.owned_amplifier = 0
        self.external = None
        self.writing = False
        self.save = save
        self.restore_deadline = 0

    def _persist(self):
        if self.save:
            self.save(self.export_state())

    def export_state(self):
        current = self.current()
        if not self._ours(current):
            return None
        return {"duration": current.get("duration", 0),
                "amplifier": self.owned_amplifier,
                "external_remaining": max(0, self.external[0] - self.clock()) if self.external else 0,
                "external_amplifier": self.external[1] if self.external else 0}

    def restore(self, saved):
        """Recover a lease from the persisted engine duration, not wall time.

        Effects pause while a world is closed. External effect events invalidate
        the saved lease. If the saved signature no longer matches, leave it alone.
        """
        current = self.current()
        if not isinstance(saved, dict) or not current:
            return
        duration = current.get("duration", 0)
        remaining = saved.get("external_remaining", 0)
        external_amplifier = saved.get("external_amplifier", 0)
        if (not isinstance(saved.get("duration"), (int, float)) or
                not 0 < saved["duration"] <= config.EFFECT_SECONDS + 1 or
                not isinstance(remaining, (int, float)) or not 0 <= remaining < float("inf") or
                type(external_amplifier) is not int or not 0 <= external_amplifier <= 255 or
                current.get("amplifier", 0) != saved.get("amplifier") or
                not 0 < duration <= saved["duration"] + 1):
            return
        elapsed = max(0, saved["duration"] - duration)
        self.owned_until = self.clock() + duration
        self.owned_amplifier = current.get("amplifier", 0)
        # Native loading replays AddEffect shortly after the ready handshake.
        # Accept one matching replay, without treating it as an external effect.
        self.restore_deadline = self.clock() + 2
        remaining -= elapsed
        if remaining > 0:
            self.external = (self.clock() + remaining, external_amplifier)

    def current(self):
        for effect in self.component.GetAllEffects() or []:
            if effect.get("effectName") == "night_vision":
                return effect
        return None

    def observe(self, duration, amplifier):
        if not self.writing:
            current = self.current()
            replay = (self.restore_deadline > self.clock() and self._ours(current)
                      and amplifier == self.owned_amplifier
                      and abs(duration - current.get("duration", 0)) <= 1)
            self.restore_deadline = 0
            if replay:
                return
            self.external = (self.clock() + duration, amplifier)
            self.owned_until = 0
            self._persist()

    def removed(self):
        if not self.writing:
            self.restore_deadline = 0
            self.external = None
            self.owned_until = 0
            self._persist()

    def _ours(self, current):
        return (current is not None and self.owned_until > self.clock()
                and current.get("amplifier", 0) == self.owned_amplifier
                and abs(current.get("duration", 0) - (self.owned_until - self.clock())) <= 2.0)

    def maintain(self):
        current = self.current()
        now = self.clock()
        if current and not self._ours(current):
            was_owned = self.owned_until > 0
            self.external = (now + current.get("duration", 0), current.get("amplifier", 0))
            self.owned_until = 0
            if was_owned:
                self._persist()
        if current and current.get("duration", 0) > config.EFFECT_REFRESH_AT:
            return
        amplifier = current.get("amplifier", 0) if current else 0
        self.writing = True
        try:
            success = self.component.AddEffectToEntity("night_vision", config.EFFECT_SECONDS, amplifier, False)
        finally:
            self.writing = False
        if success:
            self.owned_until = now + config.EFFECT_SECONDS
            self.owned_amplifier = amplifier
            self._persist()

    def release(self):
        current = self.current()
        # Unknown / externally replaced effects are left intact.
        if self._ours(current):
            self.writing = True
            try:
                self.component.RemoveEffectFromEntity("night_vision")
                if self.external:
                    left = int(math.ceil(self.external[0] - self.clock()))
                    if left > 0:
                        self.component.AddEffectToEntity("night_vision", left, self.external[1], True)
            finally:
                self.writing = False
        self.owned_until = 0
        self.external = None
        self.restore_deadline = 0
        self._persist()
