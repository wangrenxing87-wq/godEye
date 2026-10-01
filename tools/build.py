"""Export only the two runtime packs as a deterministic .mcaddon archive."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = ("behavior_pack_qbUAm8gp", "resource_pack_F1LzIf84")


def build(output):
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifests = [json.loads((ROOT / p / "manifest.json").read_text(encoding="utf-8")) for p in PACKS]
    version = manifests[0]["header"]["version"]
    if any(m["header"]["version"] != version or m["modules"][0]["version"] != version for m in manifests):
        raise ValueError("Pack versions must agree")
    if manifests[0]["dependencies"] != [{"uuid": manifests[1]["header"]["uuid"], "version": version}]:
        raise ValueError("Behavior pack must depend on matching resource pack")
    files = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        # China Edition requires the directory, but parses every file in it.
        # A .gitkeep is treated as an entity definition and produces an error.
        directory = zipfile.ZipInfo(PACKS[0] + "/entities/", (2026, 9, 30, 0, 0, 0))
        archive.writestr(directory, b"")
        for pack in PACKS:
            for path in sorted((ROOT / pack).rglob("*")):
                if not path.is_file() or path.name.startswith(".") or "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
                    continue
                relative = path.relative_to(ROOT).as_posix()
                info = zipfile.ZipInfo(relative, (2026, 9, 30, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                data = path.read_bytes()
                archive.writestr(info, data)
                files.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest()})
    report = {"archive": output.name, "version": version, "files": files,
              "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    output.with_suffix(".sha256.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Built %s (%d files, %d bytes)" % (output, len(files), output.stat().st_size))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/MercuryX_GodEye_1.0.0.mcaddon")
    build(parser.parse_args().output)
