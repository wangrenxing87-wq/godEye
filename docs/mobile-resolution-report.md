# 手机横屏分辨率测试

测试时间：2026-09-30。使用当前 Windows 原生开发客户端，实际调整游戏渲染窗口，保留现有 GUI 缩放与触控模拟布局。截图为实际游戏画面，仅裁去 Windows 边框，没有重新排版或重绘。共检查 8 种分辨率、3 个界面状态，保存 24 张截图。

**设置页在 960×540 及本次更高分辨率下布局正常；854×480 字体过小。主界面探测面板在无目标时仍有大块空白，与方向键区域重叠，需要调整。**

[打开截图对比页](validation/mobile-resolution/index.html)，可切换分辨率、界面状态及原始像素显示。

| 分辨率 | 比例 | 设置页结果 | 实际截图 |
|---|---|---|---|
| 854×480 | 约 16:9 | 控件完整，但文字过小，不建议按当前样式交付 | [凡人](validation/mobile-resolution/lv0-854x480.png) / [天眼](validation/mobile-resolution/lv5-854x480.png) |
| 960×540 | 16:9 | 无模组控件重叠，说明完整，文字可辨 | [凡人](validation/mobile-resolution/lv0-960x540.png) / [天眼](validation/mobile-resolution/lv5-960x540.png) |
| 1280×720 | 16:9 | 无模组控件重叠，说明完整 | [凡人](validation/mobile-resolution/lv0-1280x720.png) / [天眼](validation/mobile-resolution/lv5-1280x720.png) |
| 1920×1080 | 16:9 | 无模组控件重叠，说明完整 | [凡人](validation/mobile-resolution/lv0-1920x1080.png) / [天眼](validation/mobile-resolution/lv5-1920x1080.png) |
| 1560×720 | 19.5:9 | 长屏布局完整 | [凡人](validation/mobile-resolution/lv0-1560x720.png) / [天眼](validation/mobile-resolution/lv5-1560x720.png) |
| 1600×720 | 20:9 | 长屏布局完整 | [凡人](validation/mobile-resolution/lv0-1600x720.png) / [天眼](validation/mobile-resolution/lv5-1600x720.png) |
| 2340×1080 | 19.5:9 | 长屏布局完整 | [凡人](validation/mobile-resolution/lv0-2340x1080.png) / [天眼](validation/mobile-resolution/lv5-2340x1080.png) |
| 2400×1080 | 20:9 | 长屏布局完整 | [凡人](validation/mobile-resolution/lv0-2400x1080.png) / [天眼](validation/mobile-resolution/lv5-2400x1080.png) |

## 已确认

- 凡人等级四个开关显示灰色「关」，范围显示「未启用」；8 种尺寸均未再出现紫黑缺失贴图。此次补齐了上一轮灰色背景修复的原生画面验证。
- Lv.5 的较长说明完整显示；开启开关为青色，范围按钮保持深色。等级切换可在当前原生客户端直接生效。
- 等级列表、关闭按钮、底部提示均留在设置面板内，没有发现模组自己的按钮互相覆盖。
- 测试后窗口恢复为开始时的 986×470 客户区，天眼恢复 Lv.0，范围恢复省电。

## 发现的问题

1. **854×480 的文字过小。** 当前客户端在这个窗口尺寸使用较小的 GUI 缩放，等级文字、说明和 HUD 状态都明显小于 960×540。建议针对小 GUI 缩放设置最低可读字号，不能只看是否越界。
2. **HUD 无目标时背景未收紧。** [1280×720 实际画面](validation/mobile-resolution/hud6-1280x720.png) 中，只有一行「已探测区域暂无目标」，背景仍保留大块空白并进入触控方向键区域；[1920×1080](validation/mobile-resolution/hud6-1920x1080.png) 和 [2400×1080](validation/mobile-resolution/hud6-2400x1080.png) 更明显。需要检查原生子背景是否跟随动态高度更新，并为方向键留出空间。本次没有验证方向键触摸是否被拦截。

截图中灰白色列表小图标属于开发客户端调试入口，位置会随窗口变化；它在部分截图中遮住局部内容，不计为天眼自身按钮重叠。

## 验证范围

此次为**桌面原生客户端在手机分辨率下的适配检查**。ADB 没有连接设备，未完成 Android/真实手机触控、多指、挖孔安全区、不同 DPI 设置或性能测试。HUD 的 8 张对比图覆盖暂无目标/探测中的状态；完整目标列表仅在当前 986×470 窗口另有观察，没有完成所有尺寸下的满列表验收。

本轮只新增测试工具、截图和记录，没有修改运行时模组或重新导出组件包。上述两个问题仍未修复。

复现：在原生客户端打开对应界面后执行 `py -3 -B -X utf8 tools/check_mobile_resolutions.py --pid <游戏进程ID> --label <截图名称>`。工具调整窗口、逐尺寸截图并在结束时恢复窗口；它不会替换当前世界或自动改变等级。
