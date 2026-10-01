"""Capture the native game UI at phone landscape sizes, then restore its window.

This checks Windows client rendering at mobile resolutions, not Android touch
or performance. Open the desired menu/HUD before running it.
"""
import argparse
import ctypes
import json
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZES = ((854, 480), (960, 540), (1280, 720), (1920, 1080),
         (1560, 720), (1600, 720), (2340, 1080), (2400, 1080))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if not args.label.replace("-", "").isalnum():
        parser.error("label must contain letters, digits and hyphens only")
    user = ctypes.windll.user32
    user.SetProcessDPIAware()
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    # Resolve the HWND from a verified game PID, never an arbitrary foreground app.
    query = ("$p = Get-Process -Id %d -ErrorAction Stop; "
             "if ($p.ProcessName -ne 'Minecraft.Windows') { throw 'Expected Minecraft.Windows' }; "
             "$p.MainWindowHandle.ToInt64()") % args.pid
    window = int(subprocess.check_output(["powershell", "-NoProfile", "-Command", query], text=True).strip())
    if not window:
        raise RuntimeError("No game window")
    original, client = wintypes.RECT(), wintypes.RECT()
    user.GetWindowRect(window, ctypes.byref(original))
    user.GetClientRect(window, ctypes.byref(client))
    frame_w = original.right - original.left - client.right
    frame_h = original.bottom - original.top - client.bottom
    out_dir = ROOT / "docs/validation/mobile-resolution"
    out_dir.mkdir(parents=True, exist_ok=True)
    checks = []
    try:
        for width, height in SIZES:
            x = max(0, (user.GetSystemMetrics(0) - width - frame_w) // 2)
            y = max(0, (user.GetSystemMetrics(1) - height - frame_h) // 2)
            if not user.SetWindowPos(window, None, x, y, width + frame_w, height + frame_h, 0x0014):
                raise ctypes.WinError()
            time.sleep(1.0)
            actual = wintypes.RECT()
            user.GetClientRect(window, ctypes.byref(actual))
            if (actual.right, actual.bottom) != (width, height):
                raise RuntimeError("Requested %sx%s, got %sx%s" % (width, height, actual.right, actual.bottom))
            name = "%s-%dx%d.png" % (args.label, width, height)
            subprocess.run(["powershell", "-NoProfile", "-File", str(ROOT / "tools/capture_game.ps1"),
                            "-GameProcessId", str(args.pid), "-OutputPath", str((out_dir / name).relative_to(ROOT)),
                            "-ClientOnly"],
                           cwd=str(ROOT), check=True, capture_output=True)
            checks.append({"size": [width, height], "image": name, "native_capture": True})
            print("Captured %s" % name, flush=True)
    finally:
        restored = bool(user.SetWindowPos(window, None, original.left, original.top,
                                         original.right - original.left, original.bottom - original.top, 0x0014))
        report = {"method": "Windows native game rendered at phone landscape resolutions",
                  "android_touch_or_performance_test": False, "label": args.label,
                  "window_restored": restored, "captures": checks}
        (out_dir / (args.label + ".json")).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
