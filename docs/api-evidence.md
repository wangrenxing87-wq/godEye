# ModSDK API 依据

来源为开发技能附带的 ModSDK 2.4 / BE 1.18 文档快照（2022-11-08）。相对路径以 `minecraft-netease-mod-development` 技能目录为根；归档文件名存在字符编码遗留，以下保留磁盘真实路径。当前 Windows 3.10 开发包运行结果另外记录在 acceptance.md。

| API / 事件 | 本地文档相对路径 |
|---|---|
| 选项禁用：`SetTouchEnable(False)` 禁止触控，`SetTouchEnable(True)` 恢复；`asImage().SetSprite` 直接替换按钮 default/hover/pressed 子控件的背景；`SetSpriteGray(True/False)` 置灰/恢复原色 | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/Φç¬σ«ÜΣ╣ëUI/UIµÄºΣ╗╢.md` |
| 图片 JSON `grayscale`：原生图片去色，保证 UI 初始灰色状态无需新增贴图 | `references/source-docs/mcguide/18-τòîΘ¥óΣ╕ÄΣ║ñΣ║Æ/30-UIΦ»┤µÿÄµûçµíú.md` |
| JSON 按钮 `is_handle_button_move_event=true`：开启移动事件派发；控件层级 `layer` | `references/source-docs/mcguide/18-τòîΘ¥óΣ╕ÄΣ║ñΣ║Æ/30-UIΦ»┤µÿÄµûçµíú.md` |
| 悬浮按钮：`AddTouchEventParams`、`SetButtonTouchDownCallback`、`SetButtonTouchMoveCallback`、`SetButtonTouchMoveOutCallback`、`SetButtonTouchUpCallback`、`SetButtonTouchCancelCallback`、`SetButtonScreenExitCallback`、`SetAnchorFrom`、`SetAnchorTo`、`GetPosition`、`SetPosition`、`GetSize` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/Φç¬σ«ÜΣ╣ëUI/UIµÄºΣ╗╢.md` |
| `ServerChatEvent`：`message`、`playerId`、`cancel` | `references/source-docs/mcdocs/1-ModAPI/Σ║ïΣ╗╢/Σ╕ûτòî.md` |
| `AddEffectToEntity` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/σ«₧Σ╜ô/τè╢µÇüµòêµ₧£.md` |
| `CreateTextBoardInWorld` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/τë╣µòê/µûçσ¡ùΘ¥óµ¥┐.md` |
| `CreateUI` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/Φç¬σ«ÜΣ╣ëUI/ΘÇÜτö¿.md` |
| `DimensionChangeFinishClientEvent` | `references/source-docs/mcdocs/1-ModAPI/Σ║ïΣ╗╢/τÄ⌐σ«╢.md` |
| `GetAllEffects` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/σ«₧Σ╜ô/τè╢µÇüµòêµ₧£.md` |
| `GetBlockPaletteBetweenPos` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/Σ╕ûτòî/µû╣σ¥ùτ╗äσÉê.md` |
| `GetEntitiesAround` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/Σ╕ûτòî/σ£░σ¢╛.md` |
| `GetEntityTags` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/σ«₧Σ╜ô/µáçτ¡╛.md` |
| `GetExtraData` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/Σ╕ûτòî/Φç¬σ«ÜΣ╣ëµò░µì«.md` |
| `GetExtraData` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/σ«₧Σ╜ô/Φç¬σ«ÜΣ╣ëµò░µì«.md` |
| `GetLoadedChunks` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/Σ╕ûτòî/σ£░σ¢╛.md` |
| `GetLocalPosListOfBlocks` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/µû╣σ¥ù/µû╣σ¥ùΦ░âΦë▓µ¥┐.md` |
| `GetTopBlockHeight` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/Σ╕ûτòî/µû╣σ¥ùτ«íτÉå.md` |
| `GetUI` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/Φç¬σ«ÜΣ╣ëUI/ΘÇÜτö¿.md` |
| `NotifyToServer` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/ΘÇÜτö¿/Σ║ïΣ╗╢.md` |
| `PlayerRespawnFinishServerEvent` | `references/source-docs/mcdocs/1-ModAPI/Σ║ïΣ╗╢/τÄ⌐σ«╢.md` |
| `SetBoardDepthTest` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/τë╣µòê/µûçσ¡ùΘ¥óµ¥┐.md` |
| `SetEnableColorAdjustment` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/σÉÄσñäτÉå/Φë▓σ╜⌐.md` |
| `SetExtraData` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/Σ╕ûτòî/Φç¬σ«ÜΣ╣ëµò░µì«.md` |
| `SetExtraData` | `references/source-docs/mcdocs/1-ModAPI/µÄÑσÅú/σ«₧Σ╜ô/Φç¬σ«ÜΣ╣ëµò░µì«.md` |
