"""Save/reopen the owned native test world and verify effect ownership."""
import json
import subprocess
import sys
import time
from pathlib import Path

from native_acceptance import ROOT, apply, command, snapshot, server_player, wait_client, wait_for


def run(args):
    return subprocess.run(args, cwd=str(ROOT), check=True, capture_output=True,
                          creationflags=0x08000000)


def main():
    result_path = ROOT / ".runtime/world-result.json"
    record = json.loads(json.loads(result_path.read_text(encoding="utf-8"))["content"][0]["text"])
    if record.get("main_component_uuid") != "6c81fa43f2cd416a824fe258aa560dfa":
        raise ValueError("Only the session-owned validation world may be restarted")
    process_id = int(record["process_id"])
    wait_client(lambda v: v.get("ready"))
    apply(6)
    wait_for(lambda: server_player().get("lease") is not None)
    evidence = {"before": {"client": snapshot("client"), "server": snapshot("server")}}
    run(["powershell", "-NoProfile", "-Command", "(Get-Process -Id %d).CloseMainWindow()" % process_id])
    until = time.monotonic() + 30
    while True:
        value = run(["powershell", "-NoProfile", "-Command",
                     "[bool](Get-Process -Id %d -ErrorAction SilentlyContinue)" % process_id])
        if value.stdout.strip() == b"False":
            break
        if time.monotonic() >= until:
            raise RuntimeError("Test game did not close gracefully")
        time.sleep(.5)
    run([sys.executable, "-X", "utf8", "tools/studio_rpc.py", "launch_world",
         "--arguments-file", ".runtime/launch.json", "--output", str(result_path)])
    before_time = evidence["before"]["client"]["time"]
    wait_client(lambda v: v.get("ready") and v.get("time", 0) > before_time + 3, 45)
    time.sleep(2)
    evidence["reopened"] = {"client": snapshot("client"), "server": snapshot("server")}
    path = ROOT / "docs/validation/native-reopen.json"
    def save():
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    save()
    assert snapshot("client")["settings"]["level"] == 6
    print("Reopened saved level 6", flush=True)
    apply(0)
    try:
        evidence["disabled"] = wait_for(lambda: v if not (v := server_player()).get("effects") else None, 5)
    finally:
        evidence["after_disable_server"] = snapshot("server")
        save()
    print("PASS immediate disable after reopening", flush=True)
    command("server", "commands", commands=["/effect @s night_vision 180 0 true"])
    apply(6)
    apply(0)
    evidence["external_after_disable"] = server_player()
    assert any(e["effectName"] == "night_vision" and e["duration"] > 150
               for e in evidence["external_after_disable"]["effects"])
    evidence["complete"] = True
    save()
    print("PASS external effect preserved", flush=True)
    command("server", "commands", commands=["/effect @s clear"])
    apply(6)


if __name__ == "__main__":
    main()
