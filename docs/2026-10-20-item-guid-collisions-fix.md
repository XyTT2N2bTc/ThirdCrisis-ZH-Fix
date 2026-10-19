# Third Crisis 0.57.1 装备店物品名字串台：TranslationGuid 冲突

## 主体信息

- 主体：Third Crisis 0.57.1-r（Unity 2022.3.7f1，Mono）
- 被改文件：`…\ThirdCrisis_Data\resources.assets`、
  `…\ThirdCrisis_Data\StreamingAssets\Languages\translated_zh_translation.json`
- 触发：用户反馈装备店里出现一堆「渔网装」和「啦啦队乳贴」，名字明显不对。
- 定位结论：
  - `LanguageManager.GetItemTranslation(item)` 是按 **`item.TranslationGuid`** 查语言包的
    （不是按 Name）：`LanguageManager.Items.TryGetValue(item.TranslationGuid, …)`。
  - 资源里 192 个物品对象（`Apl_*` 等）实际只有 **123 个唯一 TranslationGuid**；
    多个物品资产复制时没有重新生成 GUID，导致它们共用同一条译文。
  - 10 个冲突组（组内第一个是语言包条目的所有者，其余为串台物品）：

| 共用 GUID | 语言包条目 | 组内物品数 | 需要拆分的物品 |
|---|---|---|---|
| `74063c61…` | Fishnet Suit → 渔网装 | 19 | 18 |
| `57e81d82…` | Cheerleader Pasties → 啦啦队乳贴 | 16 | 15 |
| `9694b55b…` | Jewel's Outfit → 茱尔的装束 | 9 | 8 |
| `d0a71589…` | Holiday Hat (Generic) → 节日帽（通用） | 4 | 3 |
| `90df9ea8…` | Fiend Female Rags → 恶魔女装破布 | 2 | 1 |
| `522bb453…` | Dress → 连衣裙 | 2 | 1 |
| `d7874bed…` | Latex Outfit → 乳胶装 | 2 | 1 |
| `c412f37a…` | Jewel's Rags → 茱尔的破衣 | 2 | 1 |
| `0e0a3c19…` | Rida's Outfit → 丽达的装束 | 2 | 1 |

合计 **49 个物品**需要独立 GUID。这些物品在随包英文表里本来就没有条目
（英文下 `GetItemTranslation` 查不到会回退到 `item.Name`，所以英文看不出问题）。

## 本次修改

- 脚本：`scripts/patch_item_guids.py`（资产）+ `scripts/fix_item_translations.py`（语言包）
- 映射：`translation/item_guid_map.json`（49 条：对象名、旧/新 GUID、英文名/描述、中文译文）
- 资产：把 49 个物品的 `TranslationGuid` 字符串（32 字符，等长）就地改成唯一值
  （`md5("ThirdCrisisItem:" + 资产名)`），文件大小不变。
- 语言包：`Items` 段新增 49 条（Id=新 GUID、Name/Description=资产里的英文、
  TranslatedName/TranslatedDescription=中文）。
- 顺带校正一条历史命名差异：`Pink Stomach Tattoo` → `Pink Stomach Heart Tattoo` /
  「粉色腹部爱心纹身」（Id `440c1e78…`，与资产里的名字对齐）。

## 备份与可逆性

- `…\ThirdCrisis_Data\resources.assets.bak-thirdcrisis-item-guids`
  （首次写入前状态，已包含此前全部资产补丁）。
- 语言包：`fix_item_translations.py` 幂等追加/校正；还原可删掉这 49 条并恢复名称。

## 行为影响与排查指引

- 装备店、背包、Tooltip 里这些物品会显示各自正确的名字与描述。
- 物品逻辑不受影响：`TranslationGuid` 只用于查译文，不参与存档/物品 ID。
- 若仍看到名字串台：确认 `resources.assets` 未被官方还原；重跑 `apply_all.py --apply`。
- 若某个物品显示英文：说明该物品的 GUID 在语言包里没有条目（可以再补一条）。

## 验证与文件清单

- 修后审计：171 个带翻译的物品对象 / **171 个唯一 GUID**，仍重复 0；
  物品英文名与语言包条目的 `Name` 一致 171/171。
- 语言包 `Items` 179 → 228 条；49 条新增全部有中文名。
- 资产大小不变；49 处 GUID 回读全部为新值；幂等重跑通过。
- 端到端复现：从出厂状态跑完整流水线，产出与交付状态 sha256 一致。

## 第三方工具清单

- UnityPy 1.25.4：定位对象 `byte_start` 与原始字节；写入为 32 字节等长替换。
- dnSpyEx：确认 `LanguageManager.GetItemTranslation` 的查找键是 TranslationGuid。
