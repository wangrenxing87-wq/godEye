# 天眼 1.0.0 发布材料

日期：2026-10-01。通用发布文案、宣传图与实机视频已制作；正式提交仍受命名空间要求、设备实测和人工审阅限制。打开[index.html](index.html)浏览图片、播放视频和复制详情。

| 材料 | 路径 | 规格 |
|---|---|---|
| 通用活动说明 | [copy/activity.md](copy/activity.md) | 玩法、亮点、安装、实测范围与素材来源 |
| 详情纯文本/图文 | [copy/details.txt](copy/details.txt)、[copy/details.md](copy/details.md) | 去空白745字，含标点 |
| 横版ICON | [images/icon-992x558.png](images/icon-992x558.png) | 992×558 |
| 方版ICON | [images/icon-1000x1000.png](images/icon-1000x1000.png) | 1000×1000 |
| 卡片ICON | [images/icon-900x580.png](images/icon-900x580.png) | 900×580 |
| 三张实机轮播 | images/carousel-01.png至03.png | 每张992×558 |
| 首页图 | [images/home-940x450.png](images/home-940x450.png) | 940×450 |
| 宣传片 | [video/promo.mp4](video/promo.mp4) | 65秒，1280×720，H.264/AAC，5,863,705字节 |
| 视频封面 | [images/video-cover.png](images/video-cover.png) | 成片第3秒截帧，992×558 |
| 当前工程复核包 | [package/GodEye-1.0.0-review.zip](package/GodEye-1.0.0-review.zip) | 25个运行文件，BP/RP结构，非规范通过的正式包 |

复核包SHA256：`fcacab1c6f19d358acc391a7ee4fcd3072ea46d44696c92158c9f14e028deb7f`。CRC及全部文件与当前源码一致性通过。最低引擎均为[1,18,0]。

正式导出因`mercuryx`命名空间要求未通过。当前系统域、历史存档键及实体标签的关系见[发布前清单](copy/preflight.md)。没有修改运行时源码来绕过检查，也未将复核包重命名为通过验收的正式包。

画面来自Windows开发包3.10.0.420447真实录制。洞穴演示区由测试命令搭建，入口/任务通过公开接口注册；这些场景不属于组件附送内容。所有轮播保留原图和采集状态，宣传图独立排版；无AI生成游戏画面。视频配有原创合成环境音乐，未采集游戏原声，尚需完整播放试听。

复现工具：工程根目录`tools/release_capture.py`负责独立测试世界拍摄，`tools/release_design.py`负责四版宣传设计、说明条及配乐。`sources/`保留原始录屏、截图、状态与剪辑中间片；`build-records.json`记录来源哈希。包内没有拍摄探针或工作区账号配置。

机器报告见[validation-report.json](validation-report.json)，人工审阅见[review.json](review.json)，实际分镜见[copy/storyboard.md](copy/storyboard.md)。`ready_to_submit=false`为真实状态；手机/多人、旧引擎、活动表单及成片完整试听未通过前，不宣称已可提交。

## UUID冲突修正（2026-10-01）

按用户要求重建两包主UUID和模块UUID，同步行为包对资源包的依赖；版本保持1.0.0。新行为包UUID为`7f2753ea-bb6b-4292-8192-a93944e663c1`。重新生成MCAddon、复核ZIP、SHA256及完整素材包。包内仅两份manifest变化，其余23个运行文件逐字节一致。映射与检查见[UUID记录](package/uuid-regeneration.json)和[完整性检查](package/uuid-check.json)。新身份按独立包导入。
