# 其他模组接入天眼

所有注册接口在**服务端**调用。实例获取方式：

```python
# -*- coding: utf-8 -*-
import mod.server.extraServerApi as serverApi

vision = serverApi.GetSystem("mercuryx_godeye", "GodEyeServer")
if vision:
    vision.RegisterTarget(
        "my_addon:door_001", "entrance", 0, (100, 20, 50),
        u"遗迹入口", players=None, ttl=0)
```

系统初始化顺序不固定。在本模组和目标世界准备好后注册；实例暂不可用时延后重试。注册表仅在当前世界运行期间存在，退出后由来源模组重新注册。目标移动或任务阶段改变时，以相同 ID 更新；销毁时注销。

## RegisterTarget

`RegisterTarget(target_id, category, dimension, pos, label, players=None, ttl=0)` 返回 `True`，非法参数抛出 `ValueError`。

| 参数 | 约束 |
|---|---|
| target_id | 含命名空间的稳定字符串，最多 128 字符；同 ID 注册覆盖旧值 |
| category | `special`、`spirit`、`hidden`、`quest`、`container`、`mechanism`、`entrance` |
| dimension | 整数维度 ID |
| pos | 三个有限数值的 tuple/list，世界坐标 |
| label | 1～80 字符，中文推荐 Unicode 字符串 |
| players | `None` 表示所有玩家；list/tuple/set 指定可见玩家 ID；空集合无人可见 |
| ttl | 非负秒数，0 表示直至注销；运行时实时时钟计算 |

最多 2,048 个注册目标。只有同维度、范围内且具备对应能力的玩家收到目标。`special/spirit` 从 Lv.4 可见，其余从 Lv.5 可见。注册目标不要使用 `ore` 类别；矿石需要通过 `RegisterOre` 加入真实方块扫描。

`UnregisterTarget(target_id)`：实际删除返回 `True`，未找到返回 `False`。

## 矿石和实体类型

```python
vision.RegisterOre("my_addon:magic_ore", u"魔晶矿", rare=True, group="magic")
vision.RegisterOre("my_addon:deep_magic_ore", u"魔晶矿", rare=True, group="magic")
vision.RegisterEntityType("my_addon:ghost", u"游魂")
```

`RegisterOre(block_id, label, rare=True, group=None)`：加入服务端矿石白名单。`rare` 控制是否可在 Lv.4 粗略感知；相邻、同 `group` 的普通/深层变种合并；省略 group 时使用自身 ID。矿石 ID 必须含命名空间，名称长 1～80 字符。方块目录最多 128 项，包含内置目录。注册会使扫描缓存失效。只注册规则，不生成方块。

`RegisterEntityType(entity_id, label)`：将实体类型加入特殊生命白名单。只影响实体已在查询范围内时的分类，不生成实体。

## 标签协议

| 标签 | 分类 |
|---|---|
| `nightvision:spirit` | 灵体 |
| `nightvision:special` | 特殊生命 |
| `nightvision:hidden` | Lv.4 特殊生命、Lv.5 隐藏目标 |
| `nightvision:quest_target` | 任务目标 |
| `nightvision:hidden_chest` | 隐藏容器 |
| `nightvision:hidden_mechanism` | 机关 |

同一后缀也接受 `mercuryx_godeye:*`。标签用于可访问的实体，不是任意方块的通用标签。方块任务入口使用 `RegisterTarget`。

服务端可通过 `CreateTag(entityId).AddEntityTag("nightvision:spirit")` 添加标签；Python 2 的原生字符串参数使用 UTF-8 `str`。具有原生 `invisibility` 效果的附近实体也可被 Lv.4 检出。

## 自定义维度

`RegisterDimensionBounds(dimension_id, minimum, maximum)`：整数参数，范围为 `[minimum, maximum)`，边界必须为 8 的倍数。原版默认主世界 `[-64,320)`、下界 `[0,128)`、末地 `[0,256)`。未知自定义维度不裁剪高度；有明确范围时主动注册能减少无效查询。

## 存档与通信

玩家 ExtraData 键为 `mercuryx_godeye:settings_v1`，包含 `schema_version`、`level`、四个分类/视觉开关及 `performance`。夜视归属键为 `mercuryx_godeye:night_lease_v1`，仅供内部效果管理。

客户端请求使用 `GodEyeRequest`，服务端信任引擎注入的 `__id__`，忽略请求伪造的玩家 ID。设置消息 `GodEyeState`、目标消息 `GodEyeTargets` 均携带 `revision` 和 `dimension`。接入方应使用服务端注册 API，避免直接构造这些内部消息或修改存档键。
