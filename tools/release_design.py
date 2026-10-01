"""Reproducible marketing layouts from original GodEye assets and real captures.

Python 3 + Pillow. No generated gameplay, external stock art, or AI images.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import json
import math
import subprocess
import wave
import array

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'release'
OUT = RELEASE / 'sources/design'
OUT.mkdir(parents=True, exist_ok=True)
CYAN = '#71f4ed'
WHITE = '#f1f6f5'
MUTED = '#bdd1d5'
FONT = 'C:/Windows/Fonts/msyh.ttc'
BOLD = 'C:/Windows/Fonts/msyhbd.ttc'


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def text(im, xy, value, size, color=WHITE, bold=False, anchor=None):
    ImageDraw.Draw(im).text(xy, value, font=font(size, bold), fill=color, anchor=anchor)


def background(w, h, square=False):
    scene = Image.open(RELEASE / 'sources/gameplay/night-on.png').convert('RGB')
    # Keep game HUD and the developer console icon out of promotional backgrounds.
    scene = scene.crop((0, 140, 1280, 625))
    im = ImageOps.fit(scene, (w, h), centering=(.68, .5)).convert('RGBA')
    layer = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(layer)
    for x in range(w):
        alpha = int(242 - 115 * (x / w)**1.25) if not square else 170
        d.line((x, 0, x, h), fill=(5, 17, 29, alpha))
    im = Image.alpha_composite(im, layer)
    d = ImageDraw.Draw(im)
    d.line((32, 30, w-32, 30), fill=(96, 215, 215, 70), width=1)
    d.line((32, h-31, w-32, h-31), fill=(96, 215, 215, 70), width=1)
    return im


def eye(im, cx, cy, diameter):
    # Use the shipped pixel eye as the hero, preserving its recognizable shape.
    glow = Image.new('RGBA', im.size)
    d = ImageDraw.Draw(glow)
    r = diameter*.42
    d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(27, 220, 212, 35))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(diameter*.12)))
    d = ImageDraw.Draw(im)
    for f, color, width in ((.53, (105, 236, 232, 70), 1), (.59, (105, 236, 232, 35), 1)):
        radius = diameter*f
        d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=color, width=width)
    # Pixel art scaling is intentional; it is the in-game brand asset.
    asset = Image.open(ROOT / 'resource_pack_F1LzIf84/textures/ui/mercuryx_godeye/eye.png').convert('RGBA')
    asset = asset.resize((diameter, diameter), Image.Resampling.NEAREST)
    im.alpha_composite(asset, (int(cx-diameter/2), int(cy-diameter/2)))


def footer(im, y, x=48):
    text(im, (x, y), '无需道具  ·  自由切换', 22, MUTED)
    text(im, (im.width-44, im.height-57), 'MERCURYX  /  1.0', 13, MUTED, anchor='ra')


def posters():
    im = background(992, 558)
    eye(im, 765, 263, 304)
    text(im, (48, 66), 'GOD EYE  /  Lv.0—Lv.6', 19, CYAN)
    text(im, (40, 108), '天眼', 142, bold=True)
    text(im, (48, 294), '七级视觉 · 探索感知', 31, bold=True)
    ImageDraw.Draw(im).line((48, 363, 410, 363), fill=CYAN, width=2)
    text(im, (48, 389), '夜视 / 矿脉 / 目标标记', 24, CYAN)
    footer(im, 475)
    im.convert('RGB').save(OUT / 'icon-landscape.png')

    im = background(1000, 1000, True)
    text(im, (500, 61), 'MERCURYX  /  GOD EYE', 20, CYAN, anchor='ma')
    text(im, (500, 105), '天眼', 166, bold=True, anchor='ma')
    text(im, (500, 320), '七级视觉 · 探索感知', 39, bold=True, anchor='ma')
    eye(im, 500, 610, 350)
    text(im, (500, 852), '夜视  /  矿脉  /  目标标记', 31, CYAN, anchor='ma')
    text(im, (500, 913), '无需道具 · 自由切换', 25, MUTED, anchor='ma')
    im.convert('RGB').save(OUT / 'icon-square.png')

    im = background(900, 580)
    text(im, (45, 58), 'GOD EYE / 探索多一双眼睛', 18, CYAN)
    text(im, (37, 107), '天眼', 138, bold=True)
    text(im, (46, 289), '七级视觉，随心开启', 30, bold=True)
    eye(im, 698, 244, 268)
    d = ImageDraw.Draw(im)
    for i, label in enumerate(('持续夜视', '矿脉感知', '目标标记')):
        x = 46+i*273
        d.rounded_rectangle((x, 397, x+257, 470), radius=8, fill=(8, 30, 43, 215), outline=(79, 170, 179, 130))
        text(im, (x+17, 420), '0'+str(i+1), 18, CYAN)
        text(im, (x+63, 415), label, 26, WHITE, True)
    footer(im, 501, 46)
    im.convert('RGB').save(OUT / 'icon-card.png')

    im = background(940, 450)
    eye(im, 746, 218, 258)
    text(im, (44, 55), 'MERCURYX / GOD EYE', 17, CYAN)
    text(im, (38, 101), '天眼', 128, bold=True)
    text(im, (45, 264), '七级视觉 · 探索感知', 30, bold=True)
    text(im, (46, 337), '看清暗处，感知附近的目标', 23, CYAN)
    text(im, (896, 402), 'Lv.0—Lv.6', 16, MUTED, anchor='ra')
    im.convert('RGB').save(OUT / 'home.png')


CHAPTERS = [
    ('01-intro', 6, '天眼', '七级视觉 · 探索感知', '无需道具，打开界面即可选择能力'),
    ('02-vision', 15, '01 / 看清暗处', '凡人 → 微光 → 夜瞳 → 幽视', '同一场景实机对比，按需选择画面效果'),
    ('03-sense', 12, '02 / 感知附近', '灵视：粗略感知    天眼：精确定位', '矿脉合并显示已探测数量，方向与距离随位置变化'),
    ('04-markers', 10, '03 / 视野中的目标', 'Lv.6 真·夜瞳 · 穿遮挡文字标记', '入口与任务为接口接入演示，不自带任务剧情'),
    ('05-controls', 16, '04 / 选择即生效', '七级选择 · 分类开关 · 三档范围', '低等级选项自动置灰，设置随玩家世界存档保存'),
    ('06-outro', 6, '天眼 / GOD EYE', '让探索，多一双眼睛', '点击右上角「天眼」开启 · 选择 Lv.0 关闭'),
]


def caption(name, title, main, sub):
    im = Image.new('RGBA', (1280, 720))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1280, 48), fill=(5, 17, 29, 235))
    d.rectangle((0, 614, 1280, 720), fill=(5, 17, 29, 244))
    d.rectangle((33, 14, 37, 35), fill=CYAN)
    text(im, (51, 10), title, 22, CYAN, True)
    text(im, (1246, 13), 'MERCURYX', 15, MUTED, anchor='ra')
    text(im, (640, 625), main, 29, WHITE, True, anchor='ma')
    text(im, (640, 674), sub, 20, MUTED, anchor='ma')
    im.save(OUT / (name + '-caption.png'))


def soundtrack(seconds=65):
    # Original, quiet pentatonic ambient music. No third-party samples.
    sample_rate = 32000
    samples = array.array('h')
    chords = [(130.81, 164.81, 196.00), (110.00, 130.81, 164.81),
              (87.31, 130.81, 174.61), (98.00, 146.83, 196.00)]
    melody = (523.25, 659.25, 783.99, 659.25, 440, 523.25, 659.25, 523.25)
    for i in range(int(seconds*sample_rate)):
        t = i/sample_rate
        chord = chords[int(t//8)%4]
        pad = sum(math.sin(math.tau*f*t) for f in chord)/3
        local = t%1
        bell = math.sin(math.tau*melody[int(t)%8]*t)*math.exp(-4*local)*min(1, local*80)
        envelope = min(1, t/2, max(0, (seconds-t)/3))
        value = envelope*(pad*.075 + bell*.025)
        samples.append(round(value*32767))
    with wave.open(str(OUT/'original-ambient.wav'), 'wb') as output:
        output.setparams((1, 2, sample_rate, 0, 'NONE', 'not compressed'))
        output.writeframes(samples.tobytes())


def edit():
    if not (OUT/'original-ambient.wav').exists():
        soundtrack(sum(c[1] for c in CHAPTERS))
    edited = RELEASE / 'sources/edited'
    edited.mkdir(exist_ok=True)
    offset = 0
    for name, seconds, title, main, sub in CHAPTERS:
        caption(name, title, main, sub)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
            '-i', str(RELEASE/'sources/gameplay'/(name+'.mp4')), '-i', str(OUT/(name+'-caption.png')),
            '-ss', str(offset), '-i', str(OUT/'original-ambient.wav'),
            '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto[v]', '-map', '[v]', '-map', '2:a:0',
            '-t', str(seconds), '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-ar', '48000',
            '-movflags', '+faststart', str(edited/(name+'.mp4'))], check=True, creationflags=0x08000000)
        offset += seconds
        print('Edited', name, flush=True)


def configure():
    config = json.loads((RELEASE/'release.json').read_text(encoding='utf-8'))
    config['core_features'] = [
        {'id': 'vision', 'title': '七级选择与暗处视觉', 'evidence': '../docs/acceptance.md；sources/gameplay/02-vision.mp4；05-controls.mp4'},
        {'id': 'sense', 'title': '矿脉、特殊生命、容器与机关感知', 'evidence': '../docs/validation/native-acceptance.json；sources/gameplay/03-sense.mp4'},
        {'id': 'markers', 'title': 'Lv.6穿遮挡文字标记与接入目标', 'evidence': 'sources/gameplay/04-markers.mp4；scene-setup.json；../docs/validation/native-catalog.json'},
        {'id': 'controls', 'title': '分类、范围与即时保存', 'evidence': 'sources/gameplay/05-controls.mp4；05-controls-events.json；../docs/validation/mobile-resolution/summary.json'},
    ]
    config['mod'] = {'packs': ['../behavior_pack_qbUAm8gp', '../resource_pack_F1LzIf84'], 'external_namespaces': []}
    for key, file in [('icon_landscape', 'icon-landscape'), ('icon_square', 'icon-square'), ('icon_card', 'icon-card'), ('home', 'home')]:
        config['images'][key] = {'source': 'sources/design/'+file+'.png', 'kind': 'promotional', 'focus': [.5,.5],
            'features': ['vision', 'sense', 'markers'], 'note': '实机洞穴背景 + 工程原有64px天眼图标 + 微软雅黑排版；每版独立构图，设计源tools/release_design.py；非实机截图。'}
    for key, file, features in [('carousel_01','menu',['controls','vision']), ('carousel_02','night-on',['vision']), ('carousel_03','markers',['sense','markers'])]:
        config['images'][key] = {'source': 'sources/gameplay/'+file+'.png', 'kind': 'gameplay', 'focus': [.5,.5], 'features': features,
            'note': '2026-10-01，天眼1.0.0，Windows开发包3.10.0.420447，1280×720原生实机，专建洞穴演示区；保留对应JSON状态，入口/任务由测试工具接入；输出仅等比缩小。'}
    features = [['sense','markers'],['vision'],['sense'],['markers'],['vision','controls'],['markers']]
    config['video'] = {'clips': [{'source': 'sources/edited/'+c[0]+'.mp4', 'start': 0, 'duration': c[1], 'kind': 'gameplay', 'features': f,
        'note': 'Windows开发包3.10.0.420447真实桌面录屏，原始片段sources/gameplay/'+c[0]+'.mp4；仅叠加说明字幕与原创合成背景音乐，无原游戏音轨。'} for c,f in zip(CHAPTERS,features)], 'cover_time': 3}
    (RELEASE/'release.json').write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    import sys
    if 'edit' in sys.argv:
        edit()
    else:
        posters()
        configure()
