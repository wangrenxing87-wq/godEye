"""Validate launcher callbacks against native UI controls in the isolated test world.

This checks native coordinate/layout behavior, not physical Android touch input.
"""
import json
from pathlib import Path

from native_acceptance import command, snapshot, wait_client, change_dimension

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []

    def record(name, value):
        assert not value.get("error") and not value.get("runtime_errors")
        checks.append({"name": name, "evidence": value})
        print("PASS " + name, flush=True)

    command("client", "close")
    value = wait_client(lambda v: v.get("ready") and v.get("entry_position"))
    if value["entry_visible"]:
        command("server", "entry_chat")
        wait_client(lambda v: not v["entry_visible"])
    command("server", "entry_chat")
    value = wait_client(lambda v: v["entry_visible"] and v["entry_relative"] is None
                        and v["entry_position"] == [v["root_size"][0] - v["entry_size"][0] - 10, 28])
    default = [value["root_size"][0] - value["entry_size"][0] - 10, 28]
    assert value["entry_position"] == default
    record("default top-right native layout", value)

    x, y = default
    value = command("client", "entry_gesture", events=[
        ["down", x + 20, y + 15], ["move", x + 22, y + 16], ["up", x + 22, y + 16]])
    assert value["menu"]
    record("native tap callback tolerates jitter and opens menu", value)
    command("client", "close")

    command("client", "entry_gesture", events=[
        ["down", x + 20, y + 15], ["move", x - 150, y + 125], ["up", x - 150, y + 125]])
    value = wait_client(lambda v: v["entry_position"] == [x - 170, y + 110])
    assert value["entry_position"] == [x - 170, y + 110] and not value["menu"]
    record("native drag moves control without opening menu", value)
    moved = value["entry_relative"]
    dimension = value["dimension"]
    server = snapshot("server")
    position = next(iter(server["players"].values()))["pos"]
    change_dimension(1 if dimension != 1 else 0, [0, 70, 0])
    change_dimension(dimension, position)
    value = wait_client(lambda v: v["entry_relative"] == moved and v.get("hud"))
    assert not value["menu"]
    record("dragged position survives native dimension round trip", value)

    x, y = value["entry_position"]
    command("client", "entry_gesture", events=[
        ["down", x + 20, y + 15], ["move", -1000, 1000], ["cancel", -1000, 1000]])
    value = wait_client(lambda v: v["entry_position"] == [0, v["root_size"][1] - v["entry_size"][1]])
    assert value["entry_position"] == [0, value["root_size"][1] - value["entry_size"][1]]
    assert not value["menu"]
    record("native out-of-bounds drag clamps and cancels without menu", value)

    level = value["settings"]["level"]
    result = command("server", "entry_chat")
    assert result["command_result"]["cancel"]
    value = wait_client(lambda v: not v["entry_visible"])
    assert value["settings"]["level"] == level
    record("UTF-8 chat callback hides launcher without disabling ability", value)
    command("server", "entry_chat")
    value = wait_client(lambda v: v["entry_visible"] and v["entry_relative"] is None
                        and v["entry_position"] == default)
    assert value["entry_position"] == default
    record("second chat callback restores top-right launcher", value)

    report = {"complete": True, "method": "Native UI controls driven through documented callbacks",
              "android_touch_verified": False, "checks": checks}
    hidden = ROOT / ".runtime/launcher-chat-hidden.json"
    restored = ROOT / ".runtime/launcher-chat-restored.json"
    if hidden.exists() and restored.exists():
        report["actual_chat_input"] = {"hidden": json.loads(hidden.read_text(encoding="utf-8")),
                                       "restored": json.loads(restored.read_text(encoding="utf-8"))}
    pointer_files = ("launcher-touch-drag.json", "launcher-touch-tap.json", "launcher-touch-over-radar.json")
    if all((ROOT / ".runtime" / name).exists() for name in pointer_files):
        report["actual_pointer_input"] = {
            "method": "Windows development client SimulateTouchWithMouse, OS mouse down/move/up",
            "checks": {name: json.loads((ROOT / ".runtime" / name).read_text(encoding="utf-8"))
                       for name in pointer_files}}
    (ROOT / "docs/validation/native-launcher.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
