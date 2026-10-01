"""Build the local review page and hash-based provenance for release materials."""
import hashlib
import html
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'release'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_page():
    items = [
        ('icon-992x558.png', '横版宣传ICON', '992 × 558'),
        ('icon-1000x1000.png', '方版宣传ICON', '1000 × 1000'),
        ('icon-900x580.png', '卡片宣传ICON', '900 × 580'),
        ('home-940x450.png', '首页推广图', '940 × 450'),
        ('carousel-01.png', '实机 01 · 七级设置', '992 × 558'),
        ('carousel-02.png', '实机 02 · 洞穴夜视', '992 × 558'),
        ('carousel-03.png', '实机 03 · 目标标记', '992 × 558'),
        ('video-cover.png', '视频封面 · 成片第3秒', '992 × 558'),
    ]
    cards = ''.join('<a class="card" href="images/{0}" target="_blank"><div class="image"><img src="images/{0}" alt="{1}" loading="lazy"></div><div class="caption"><b>{1}</b><span>{2} ↗</span></div></a>'.format(*item) for item in items)
    details = html.escape((OUT/'copy/details.txt').read_text(encoding='utf-8'))
    package_sha256 = digest(OUT/'package/GodEye-1.0.0-review.zip')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>天眼 · 发布材料预览</title>
<style>
:root{color-scheme:dark;--fg:#e8f3f4;--muted:#a5b9c0;--cyan:#71f4ed;--line:#253d4d}*{box-sizing:border-box}body{margin:0;background:#08131e;color:var(--fg);font:16px/1.7 'Microsoft YaHei',sans-serif}a{color:var(--cyan);text-decoration:none}button{font:inherit;cursor:pointer;background:#123442;color:var(--cyan);border:1px solid #34616b;border-radius:7px;padding:8px 15px}button:hover,a:hover{filter:brightness(1.17)}header,main,footer{max-width:1160px;margin:auto;padding:30px}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);font-size:13px;letter-spacing:.08em}nav{display:flex;gap:24px}.intro{display:grid;grid-template-columns:1.5fr 1fr;gap:32px;align-items:center;margin:22px 0 36px}.intro img{width:100%;border-radius:12px;border:1px solid var(--line)}h1{font-size:38px;line-height:1.25;margin:0 0 20px}h2{font-size:24px;margin:32px 0 16px}p{color:var(--muted)}.badge{display:inline-block;color:#f0ce87;background:#3a2c19;border:1px solid #665030;border-radius:5px;padding:3px 10px;font-size:13px}.stats{display:flex;gap:23px;margin-top:22px}.stats strong{font-size:26px;display:block;color:var(--cyan)}.stats span{font-size:13px;color:var(--muted)}.notice{border:1px solid #70532d;border-left:4px solid #e4b66a;background:#211e18;padding:18px 22px;border-radius:7px;color:#e5d5b9}.notice p{margin:5px 0;color:inherit}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}.card{border:1px solid var(--line);border-radius:10px;overflow:hidden;color:var(--fg);background:#102130}.image{height:310px;background:#0b1823;display:flex;align-items:center;justify-content:center}.image img{max-width:100%;max-height:100%;object-fit:contain}.caption{padding:13px 17px;display:flex;align-items:center;justify-content:space-between;gap:12px}.caption span{font-size:13px;color:var(--muted)}video{width:100%;background:#030b10;border-radius:10px;border:1px solid var(--line)}.chapters{display:flex;gap:10px;flex-wrap:wrap;margin:15px 0}textarea{width:100%;min-height:550px;resize:vertical;border:1px solid var(--line);border-radius:8px;background:#102130;color:var(--fg);padding:22px;font:15px/1.9 'Microsoft YaHei',sans-serif}.links{display:flex;gap:18px;flex-wrap:wrap}.small{font-size:13px;color:var(--muted)}code{overflow-wrap:anywhere;color:#bcdedc}footer{border-top:1px solid var(--line);color:var(--muted);font-size:13px}@media(max-width:760px){header,main,footer{padding:18px}.intro,.grid{grid-template-columns:1fr}.image{height:260px}nav{gap:12px}h1{font-size:30px}.caption{align-items:flex-start;flex-direction:column;gap:0}}
</style><header><b>MERCURYX / GOD EYE</b><nav><a href="#images">图片</a><a href="#video">视频</a><a href="#copy">文案</a><a href="#package">包与报告</a></nav></header><main>
<div class="intro"><img src="images/icon-992x558.png" alt="天眼宣传ICON"><div><span class="badge">发布复核稿 · 尚未完成提交验收</span><h1>天眼<br>七级视觉与探索感知</h1><p>文案、宣传设计与实机视频集中预览。点击图片打开原尺寸，章节按钮可定位视频。</p><div class="stats"><div><strong>8</strong><span>规格图片</span></div><div><strong>65秒</strong><span>实机宣传片</span></div><div><strong>745字</strong><span>详情正文</span></div></div></div></div>
<div class="notice"><b>当前可用于内容复核，尚不可宣称已通过发布验收。</b><p>正式包被命名空间规范拦截。手机/真实多人、旧引擎、指定活动表单及完整播放试听仍需补齐。<a href="copy/preflight.md">查看具体清单 ↗</a></p></div>
<h2 id="images">宣传图与实机轮播</h2><p>四版宣传设计分别排版；三张轮播均来自当前组件真实运行。视频封面直接取自成片。</p><div class="grid">__CARDS__</div>
<h2 id="video">65秒实机宣传片</h2><video id="player" controls preload="metadata" poster="images/video-cover.png"><source src="video/promo.mp4" type="video/mp4">请使用支持MP4的浏览器，或直接下载视频。</video><div class="chapters"><button data-time="0">00:00 天眼</button><button data-time="6">00:06 夜视</button><button data-time="21">00:21 感知</button><button data-time="33">00:33 标记</button><button data-time="43">00:43 设置</button><button data-time="59">00:59 收尾</button></div><p class="small">1280×720 · H.264 / AAC · 5.86 MB · 原创合成环境音乐，无原游戏音轨。<a href="video/promo.mp4" download>下载成片</a> · <a href="copy/storyboard.md">分镜与来源</a></p>
<h2 id="copy">详情正文</h2><div class="links"><button id="copy-button">复制745字详情</button><a href="copy/details.txt" download>纯文本</a><a href="copy/details.md">图文版</a><a href="copy/activity.md">通用活动说明</a></div><p class="small">计数包含标点、字母与数字，忽略空白。未提供活动表单，通用稿不虚构活动关联。</p><textarea id="details" readonly aria-label="模组详情正文">__DETAILS__</textarea>
<h2 id="package">当前工程复核包</h2><p>25个运行文件，原始BP/RP结构，已校验CRC和源码一致性。正式命名空间规范未通过，请勿将此包视为已经通过提交验收。</p><p><a href="package/GodEye-1.0.0-review.zip" download>下载 GodEye-1.0.0-review.zip</a> · <a href="package/GodEye-1.0.0-review.zip.sha256">SHA256</a></p><p class="small"><code>__PACKAGE_SHA256__</code></p><div class="links"><a href="validation-report.json">机器检查报告</a><a href="review.json">人工审阅记录</a><a href="package/inspection-report.json">包规范检查</a><a href="package/import-check.json">导入实测记录</a><a href="README.md">交付说明</a></div>
</main><footer>2026-10-01 · 天眼1.0.0 · Windows开发包实机素材。演示场景及接入任务不随组件附送。</footer><script>
document.querySelectorAll('[data-time]').forEach(button=>button.addEventListener('click',()=>{const player=document.getElementById('player');player.currentTime=Number(button.dataset.time);player.play().catch(()=>{});}));
document.getElementById('copy-button').addEventListener('click',async function(){const el=document.getElementById('details');try{await navigator.clipboard.writeText(el.value);this.textContent='已复制';}catch(e){el.focus();el.select();this.textContent='正文已选中，请按 Ctrl+C';}});
</script></html>'''
    (OUT/'index.html').write_text(page.replace('__CARDS__', cards).replace('__DETAILS__', details).replace('__PACKAGE_SHA256__', package_sha256), encoding='utf-8')


def provenance():
    source_files = []
    for p in sorted((OUT/'sources').rglob('*')):
        if p.is_file() and p.suffix.lower() in ('.png','.jpg','.mp4','.wav','.json'):
            source_files.append({'path':p.relative_to(OUT).as_posix(),'sha256':digest(p),'bytes':p.stat().st_size})
    value = {'date':'2026-10-01','timezone':'Asia/Shanghai','mod_version':'1.0.0',
        'environment':'Windows开发包3.10.0.420447 / RenderDragon','capture_size':[1280,720],
        'gameplay':'原生录屏与PrintWindow截图；独立测试世界搭建的洞穴；不是AI或编辑器画面',
        'registered_targets':'遗迹入口/探索目标由测试探针经组件公开RegisterTarget接口注册，非组件附送任务',
        'graphics':'Pillow编排实机背景与原工程像素眼睛；微软雅黑字体；无AI生图',
        'audio':'自行以正弦音源合成环境音乐；无第三方采样、旁白或游戏原声；尚未实际试听',
        'raw_clip_order':['01-intro','02-vision','03-sense','04-markers','05-controls','06-outro'],
        'source_files':source_files}
    (OUT/'provenance.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def bundle():
    destination=ROOT/'dist/GodEye_release_materials_20261001.zip'
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob('*')):
            if path.is_file() and path.suffix != '.log':
                archive.write(path,path.relative_to(ROOT).as_posix())
        for name in ('release_capture.py','release_design.py','release_delivery.py'):
            archive.write(ROOT/'tools'/name, 'source-tools/'+name)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
    destination.with_suffix('.zip.sha256').write_text(digest(destination)+'  '+destination.name+'\n',encoding='ascii')
    print(destination, destination.stat().st_size, digest(destination))


if __name__=='__main__':
    build_page()
    provenance()
    bundle()
