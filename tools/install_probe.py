"""Update our isolated Studio component and install a development-only probe."""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install(destination):
    destination = destination.resolve()
    if destination == ROOT or destination.name != "6c81fa43f2cd416a824fe258aa560dfa":
        raise ValueError("Probe may only be installed into this session's isolated validation component")
    for name in ("behavior_pack_qbUAm8gp", "resource_pack_F1LzIf84"):
        shutil.copytree(ROOT / name, destination / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("*.pyc", "__pycache__", ".gitkeep"))
    scripts = destination / "behavior_pack_qbUAm8gp/godEyeScripts"
    old_keep = destination / "behavior_pack_qbUAm8gp/entities/.gitkeep"
    if old_keep.exists():
        old_keep.unlink()
    probe_source = (ROOT / "tools/runtime_probe.py").read_text(encoding="utf-8")
    prelude, classes = probe_source.split("class ServerProbe", 1)
    server_class, client_class = classes.split("class ClientProbe", 1)
    (scripts / "runtime_probe_server.py").write_text(
        prelude.replace("import mod.client.extraClientApi as clientApi\n", "") + "class ServerProbe" + server_class,
        encoding="utf-8")
    (scripts / "runtime_probe_client.py").write_text(
        prelude.replace("import mod.server.extraServerApi as serverApi\n", "") + "class ClientProbe" + client_class,
        encoding="utf-8")
    if (scripts / "runtime_probe.py").exists():
        (scripts / "runtime_probe.py").unlink()
    entry = scripts / "modMain.py"
    source = entry.read_text(encoding="utf-8")
    for side, cls in (("server", "Server"), ("client", "Client")):
        needle = '"godEyeScripts.%s_system.GodEye%s")' % (side, cls)
        addition = '\n        %sApi.RegisterSystem("mercuryx_godeye_probe", "%sProbe", "godEyeScripts.runtime_probe_%s.%sProbe")' % (side, cls, side, cls)
        source = source.replace(needle, needle + addition)
    entry.write_text(source, encoding="utf-8")
    print("Installed probe into isolated validation component:", destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    install(parser.parse_args().destination)
