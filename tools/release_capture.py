"""Capture genuine gameplay in the session-owned validation world only."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import time

from native_acceptance import ROOT, apply, command, snapshot, wait_client

OUT = ROOT / 'release/sources/gameplay'
OUT.mkdir(parents=True, exist_ok=True)
record = json.loads(json.loads((ROOT / '.runtime/release-launch-result.json').read_text(encoding='utf-8'))['content'][0]['text'])
assert record['main_component_uuid'] == '6c81fa43f2cd416a824fe258aa560dfa'
PID = record['process_id']
user = ctypes.windll.user32
user.SetProcessDPIAware()
for name in ('GetWindowRect', 'GetClientRect'):
    getattr(user, name).argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user.SetForegroundWindow.argtypes = [wintypes.HWND]
query = "$p = Get-Process -Id %d; if ($p.ProcessName -ne 'Minecraft.Windows') { throw 'Wrong process' }; $p.MainWindowHandle.ToInt64()" % PID
HWND = int(subprocess.check_output(['powershell', '-NoProfile', '-Command', query], text=True).strip())


def size():
    window, client = wintypes.RECT(), wintypes.RECT()
    user.GetWindowRect(HWND, ctypes.byref(window))
    user.GetClientRect(HWND, ctypes.byref(client))
    user.SetWindowPos(HWND, None, 50, 50, 1280 + window.right-window.left-client.right,
                      720 + window.bottom-window.top-client.bottom, 0x0040)
    user.SetForegroundWindow(HWND)
    time.sleep(.5)


def capture(name):
    dest = OUT / (name + '.png')
    subprocess.run(['powershell', '-NoProfile', '-File', str(ROOT / 'tools/capture_game.ps1'),
                    '-GameProcessId', str(PID), '-OutputPath', str(dest.relative_to(ROOT)), '-ClientOnly'],
                   cwd=str(ROOT), check=True, capture_output=True, creationflags=0x08000000)
    (OUT / (name + '.json')).write_text(json.dumps({'client': snapshot('client'), 'server': snapshot('server')},
                                                  ensure_ascii=False, indent=2), encoding='utf-8')
    print('Captured', name, flush=True)


def key(code):
    user.SetForegroundWindow(HWND)
    user.keybd_event(code, 0, 0, 0)
    time.sleep(.08)
    user.keybd_event(code, 0, 2, 0)


def click(x, y):
    user.SetForegroundWindow(HWND)
    point = wintypes.POINT(x, y)
    user.ClientToScreen(HWND, ctypes.byref(point))
    user.SetCursorPos(point.x, point.y)
    user.mouse_event(2, 0, 0, 0, 0)
    time.sleep(.10)
    user.mouse_event(4, 0, 0, 0, 0)


def recording(name, duration, actions=()):
    origin = wintypes.POINT()
    user.ClientToScreen(HWND, ctypes.byref(origin))
    user.SetForegroundWindow(HWND)
    path = OUT / (name + '.mp4')
    log = open(OUT / (name + '-ffmpeg.log'), 'w', encoding='utf-8')
    proc = subprocess.Popen(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning',
        '-f', 'gdigrab', '-framerate', '30', '-draw_mouse', '0',
        '-offset_x', str(origin.x), '-offset_y', str(origin.y), '-video_size', '1280x720', '-i', 'desktop',
        '-t', str(duration), '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-pix_fmt', 'yuv420p', str(path)], stdout=log, stderr=log, creationflags=0x08000000)
    started = time.monotonic()
    evidence = []
    for at, label, action in actions:
        time.sleep(max(0, started + at - time.monotonic()))
        action()
        evidence.append({'at': time.monotonic()-started, 'action': label, 'client': snapshot('client')})
    result = proc.wait(timeout=duration + 15)
    log.close()
    if result:
        raise RuntimeError('Recording failed: ' + name)
    (OUT / (name + '-events.json')).write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Recorded', name, flush=True)


def setup():
    size()
    command('client', 'view', perspective=0)
    command('client', 'touch_mode', enabled=False)
    command('client', 'hud', hidden=False)
    command('client', 'close')
    # Purpose-built demonstration cave, all blocks rendered by the actual game.
    commands = [
        '/tp @s 90 -60 1 0 5', '/time set midnight', '/gamerule dodaylightcycle false',
        '/gamerule sendcommandfeedback false', '/gamerule domobspawning false',
        '/fill 77 -62 -7 110 -47 28 stone', '/fill 81 -60 -4 106 -51 24 air',
        '/fill 81 -61 -4 106 -61 24 cobbled_deepslate',
        '/fill 81 -60 -4 106 -53 -4 air',
        '/fill 81 -60 18 106 -53 21 stone_bricks',
        '/fill 93 -60 18 95 -55 21 air',
        '/fill 86 -60 9 86 -51 9 stone_bricks',
        '/fill 101 -60 9 101 -51 9 stone_bricks',
        '/fill 86 -52 9 101 -51 9 stone_bricks',
        '/fill 102 -60 14 103 -59 15 diamond_ore',
        '/fill 102 -60 13 104 -58 13 stone',
        '/fill 83 -60 12 84 -59 13 gold_ore',
        '/fill 83 -60 11 85 -58 11 stone',
        '/setblock 99 -60 19 chest', '/setblock 99 -60 18 stone_bricks',
        '/setblock 95 -60 16 lever',
        '/setblock 87 -60 8 redstone_torch', '/setblock 100 -60 8 redstone_torch',
        '/effect @s clear', '/kill @e[type=villager]',
        '/summon villager 96 -60 12', '/effect @e[type=villager] invisibility 99999 0 true',
        '/effect @e[type=villager] slowness 99999 255 true',
        '/tag @e[type=villager] add nightvision:spirit',
        '/tp @s 92 -60 2 0 3',
    ]
    result = command('server', 'commands', commands=commands)
    (OUT / 'scene-setup.json').write_text(json.dumps({'commands': commands, 'result': result}, ensure_ascii=False, indent=2), encoding='utf-8')
    command('server', 'register', target_id='godeye_demo:entrance', category='entrance', offset=[2, 1, 19], label='遗迹入口')
    command('server', 'register', target_id='godeye_demo:quest', category='quest', offset=[4, 1, 23], label='探索目标')
    apply(6, performance='quality')
    time.sleep(8)
    capture('scene-check')


if __name__ == '__main__':
    import sys
    if sys.argv[-1] == 'setup':
        setup()
    elif sys.argv[-1] == 'stills':
        size()
        apply(0)
        time.sleep(1)
        capture('night-off')
        apply(2)
        time.sleep(1)
        capture('night-on')
        apply(5)
        time.sleep(3)
        command('client', 'menu')
        time.sleep(1)
        capture('menu')
        command('client', 'close')
        time.sleep(1)
        capture('sense')
        apply(6)
        time.sleep(2)
        capture('markers')
    elif sys.argv[-1] == 'record':
        size()
        command('client', 'close')
        apply(6, performance='quality')
        time.sleep(3)
        recording('01-intro', 6)
        apply(0)
        recording('02-vision', 15, [
            (4, 'Lv.1 微光', lambda: apply(1)),
            (8, 'Lv.2 夜瞳', lambda: apply(2)),
            (12, 'Lv.3 幽视', lambda: apply(3)),
        ])
        apply(4)
        time.sleep(2)
        recording('03-sense', 12, [(6, 'Lv.5 精确感知', lambda: apply(5))])
        apply(6)
        time.sleep(2)
        recording('04-markers', 10)
        command('client', 'menu')
        time.sleep(1)
        recording('05-controls', 16, [
            (2, '实际鼠标点击Lv.0', lambda: click(280, 175)),
            (5, '实际鼠标点击Lv.5', lambda: click(280, 520)),
            (8, '实际鼠标关闭矿脉', lambda: click(860, 327)),
            (10, '实际鼠标恢复矿脉', lambda: click(860, 327)),
            (12, '实际鼠标切换范围', lambda: click(860, 590)),
            (14, '实际鼠标点击Lv.6', lambda: click(280, 588)),
        ])
        command('client', 'close')
        time.sleep(1)
        recording('06-outro', 6)
        capture('recording-final')
