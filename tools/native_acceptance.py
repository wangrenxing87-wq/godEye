"""Drive the isolated in-engine probe and preserve native verification evidence.

Requires the validation world started with install_probe.py. This script never
talks to an arbitrary world: the probe exists only in our isolated component.
"""
import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"


def snapshot(side):
    try:
        value = json.loads((RUNTIME / ("probe_%s.json" % side)).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if time.time() - value.get("time", 0) > 3:
        return {}
    return value


def wait_for(predicate, timeout=30):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        value = predicate()
        if value:
            return value
        time.sleep(0.2)
    raise RuntimeError("Timed out waiting for native probe condition")


def command(side, operation, **arguments):
    request = dict(arguments, side=side, operation=operation, id=time.time())
    (RUNTIME / "probe_command.json").write_text(json.dumps(request), encoding="utf-8")
    value = wait_for(lambda: (v if v.get("last_command") == request["id"] else None)
                     if (v := snapshot(side)) else None)
    if value.get("error"):
        raise RuntimeError(value["error"])
    return value


def apply(level, **options):
    command("client", "apply", settings=dict(options, level=level))
    return wait_for(lambda: v if (v := snapshot("client")).get("settings", {}).get("level") == level
                    and v.get("pending") is None else None)


def wait_client(predicate, timeout=30):
    def check():
        value = snapshot("client")
        return value if value and predicate(value) else None
    return wait_for(check, timeout)


def server_player():
    value = snapshot("server")
    return next(iter(value.get("players", {}).values()), {})


def change_dimension(dimension, pos):
    # The native API can reject a second teleport while the previous dimension
    # still settles, even after the dimension id has changed. Retry only False.
    until = time.monotonic() + 45
    while snapshot("client").get("dimension") != dimension:
        result = command("server", "dimension", dimension=dimension, pos=pos)
        if result.get("command_result") is not False:
            break
        if time.monotonic() >= until:
            raise RuntimeError("Native dimension API kept rejecting transition")
        time.sleep(2)
    return wait_client(lambda v: v.get("dimension") == dimension
                       and v.get("engine_dimension") == dimension and v.get("hud"), 45)


def save_check(checks, name, value):
    checks.append({"name": name, "time": time.time(), "evidence": value})
    (RUNTIME / "native-acceptance.json").write_text(
        json.dumps({"checks": checks, "complete": False}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PASS " + name, flush=True)


def main():
    checks = []
    wait_for(lambda: snapshot("client").get("ready"))
    save_check(checks, "native UI initialized and persistent settings loaded", snapshot("client"))
    change_dimension(0, [0, -58, 0])
    # Deterministic flat-world test area, containing adjacent ores, a container,
    # and a stone layer hiding the ore from normal sight.
    value = command("server", "commands", commands=[
        "/tp @s 0 -60 0", "/time set midnight", "/gamerule dodaylightcycle false", "/kill @e[type=villager]",
        "/setblock 5 -61 0 diamond_ore", "/setblock 6 -61 0 diamond_ore",
        "/setblock 5 -61 1 diamond_ore", "/setblock 8 -60 0 chest",
        "/setblock 5 -60 0 stone", "/setblock 6 -60 0 stone", "/setblock 5 -60 1 stone"])
    save_check(checks, "test blocks and nighttime setup commands completed", value)
    apply(0)
    value = wait_for(lambda: v if not (v := server_player()).get("effects") and v.get("settings", {}).get("level") == 0 else None)
    assert not snapshot("client").get("boards")
    save_check(checks, "Lv0 removes owned night vision and markers", value)
    apply(1)
    value = wait_for(lambda: v if (v := snapshot("client")).get("enhancement_owned")
                    and v.get("enhancement_value", [1])[0] > 1 else None)
    save_check(checks, "Lv1 native post-processing brightness responds to darkness", value)
    apply(2)
    value = wait_for(lambda: v if (v := server_player()).get("effects") else None)
    assert not snapshot("client")["enhancement_owned"]
    save_check(checks, "Lv2 vanilla night vision without post-processing", value)
    apply(3)
    value = wait_for(lambda: v if (v := snapshot("client")).get("enhancement_owned") else None)
    save_check(checks, "Lv3 enhanced visual settings", value)
    apply(4)
    value = wait_client(lambda v: any(t.get("coarse") for t in v.get("targets", [])))
    ore = next(t for t in value["targets"] if t.get("coarse"))
    assert "pos" not in ore and "count" not in ore and "diamond" not in str(ore)
    save_check(checks, "Lv4 coarse sensing with no coordinate or type disclosure", value)
    apply(5)
    value = wait_client(lambda v: any(t.get("count") == 3 and t.get("category") == "ore"
                                     for t in v.get("targets", [])))
    assert any(t["category"] == "container" for t in value["targets"])
    save_check(checks, "Lv5 merges covered ore blocks and locates container", value)
    apply(6)
    value = wait_for(lambda: v if (v := snapshot("client")).get("boards", 0) >= 2 else None)
    save_check(checks, "Lv6 creates world markers", value)
    value = wait_for(lambda: v if (v := snapshot("client")).get("progress", [0, 0])[0] > 0
                    and v["progress"][0] == v["progress"][1] else None, timeout=45)
    save_check(checks, "scan completes including all-air regions and build limit", value)
    command("server", "register", offset=[3, 1, 3])
    value = wait_client(lambda v: any(t["id"] == "godeye_test:quest" for t in v.get("targets", [])))
    save_check(checks, "cross-mod registered task target", value)
    # Nearby passive entity remains present in peaceful mode.
    command("server", "commands", commands=["/summon villager 4 -60 4", "/effect @e[type=villager] invisibility 300 0 true"])
    value = wait_client(lambda v: any(t["id"].startswith("entity:") for t in v.get("targets", [])))
    save_check(checks, "invisible entity detected", value)
    command("server", "commands", commands=["/tag @e[type=villager] add nightvision:spirit"])
    value = wait_client(lambda v: any(t["category"] == "spirit" for t in v.get("targets", [])))
    save_check(checks, "cross-mod spirit tag detected", value)
    baseline = next(e["duration"] for e in server_player()["effects"] if e["effectName"] == "night_vision")
    durations = []
    until = time.monotonic() + 48
    while time.monotonic() < until:
        time.sleep(0.5)
        value = server_player()
        effect = next((e for e in value.get("effects", []) if e["effectName"] == "night_vision"), None)
        assert effect is not None, "Night vision disappeared during renewal"
        durations.append(effect["duration"])
    assert min(durations) >= 20 and any(durations[i] > durations[i-1] for i in range(1, len(durations)))
    save_check(checks, "native effect renewal over a full 45-second lease", {"baseline": baseline, "durations": durations})
    # Dimension completion must remove previous-world targets and restore effects.
    value = change_dimension(1, [0, 70, 0])
    assert not any(t.get("id") == "godeye_test:quest" for t in value.get("targets", []))
    save_check(checks, "dimension transition clears old targets", value)
    change_dimension(0, [0, -58, 0])
    value = wait_for(lambda: v if (v := server_player()).get("effects") else None)
    save_check(checks, "return dimension restores night vision", value)
    old_revision = snapshot("client")["revision"]
    command("server", "commands", commands=["/gamerule doimmediaterespawn true",
            "/gamerule keepinventory true", "/spawnpoint @s 0 -60 0", "/gamemode survival", "/kill @s"])
    value = wait_client(lambda v: v.get("revision", 0) > old_revision and not v.get("dead")
                        and v.get("hud") and v.get("settings", {}).get("level") == 6, 45)
    wait_for(lambda: server_player().get("health", 0) > 0 and server_player().get("effects"))
    save_check(checks, "native death and respawn restore level effect and HUD", value)
    command("server", "commands", commands=["/gamemode creative"])
    assert not snapshot("server").get("runtime_errors"), snapshot("server")
    assert not snapshot("client").get("runtime_errors"), snapshot("client")
    save_check(checks, "native runtime diagnostics", {"server": snapshot("server"), "client": snapshot("client")})
    (RUNTIME / "native-acceptance.json").write_text(json.dumps({"checks": checks, "complete": True},
                                                              ensure_ascii=False, indent=2), encoding="utf-8")
    print("Native acceptance completed (%d checks)." % len(checks), flush=True)


if __name__ == "__main__":
    main()
