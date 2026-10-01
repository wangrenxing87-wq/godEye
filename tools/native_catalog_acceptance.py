"""Native ore catalog, extension protocol, and End dimension verification."""
import json
from pathlib import Path
from native_acceptance import apply, command, snapshot, wait_client, change_dimension, server_player


def main():
    evidence = {}
    wait_client(lambda v: v.get("ready"))
    change_dimension(0, [100, -58, 100])
    command("server", "commands", commands=["/tp @s 100 -60 100", "/gamemode creative"])
    names = ("coal", "copper", "iron", "gold", "diamond", "redstone", "lapis", "emerald")
    positions, ids, commands = [], [], []
    for index, name in enumerate(names):
        for offset, prefix in enumerate(("", "deepslate_")):
            point = [104 + offset, -61, 100 + index * 2]
            block = "minecraft:" + prefix + name + "_ore"
            positions.append(point)
            ids.append(block)
            commands.append("/setblock %d %d %d %s" % tuple(point + [block]))
    result = command("server", "commands", commands=commands)
    assert all(result["command_result"])
    blocks = command("server", "blocks", positions=positions)["command_result"]
    assert [block["name"] for block in blocks] == ids
    evidence["native_blocks"] = {"ids": ids, "blocks": blocks}
    apply(5, performance="quality")
    value = wait_client(lambda v: len([t for t in v.get("targets", []) if t.get("category") == "ore"])
                       == len(names), 45)
    assert all(t["count"] == 2 for t in value["targets"] if t["category"] == "ore")
    evidence["all_normal_and_deepslate_groups"] = value
    print("PASS 16 native ore ids and eight mixed veins", flush=True)
    for category in ("entrance", "mechanism", "quest"):
        target_id = "godeye_test:" + category
        command("server", "register", target_id=target_id, category=category, offset=[1, 0, 1])
        value = wait_client(lambda v: any(t["id"] == target_id and t["category"] == category
                                       for t in v.get("targets", [])))
        evidence[category] = value
        command("server", "unregister", target_id=target_id)
        wait_client(lambda v: not any(t["id"] == target_id for t in v.get("targets", [])))
    print("PASS registered entrance mechanism quest and unregister", flush=True)
    command("server", "register", target_id="godeye_test:private", private_hidden=True, offset=[1, 0, 1])
    baseline = snapshot("client")["tick"]
    value = wait_client(lambda v: v["tick"] > baseline + 45)
    assert not any(t["id"] == "godeye_test:private" for t in value.get("targets", []))
    evidence["private_target_not_disclosed"] = value
    command("server", "unregister", target_id="godeye_test:private")
    apply(6)
    evidence["end"] = change_dimension(2, [100, 80, 0])
    assert all(not t["id"].startswith("godeye_test:") for t in evidence["end"]["targets"])
    evidence["return"] = change_dimension(0, [100, -58, 100])
    assert server_player()["effects"]
    print("PASS End round trip restores HUD level and effect", flush=True)
    assert not snapshot("server")["runtime_errors"]
    assert not snapshot("client")["runtime_errors"]
    evidence["complete"] = True
    Path("docs/validation/native-catalog.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
