# 管线全命令与踩坑清单（native-pptx-craft）

## 0. 环境

- `$DECK` = 专用 Python 虚拟环境的解释器（`python -m venv` 自建即可），装有 python-pptx、lxml、pillow。**不要用系统 Python 混装依赖。**
- `$S` = [ppt-master](https://github.com/hugohe3/ppt-master) 仓库的 `scripts/` 目录（git clone 后直接用）。
- Node 渲染：`npm i playwright`（CommonJS require；ESM 的 import 会忽略 NODE_PATH，所以渲染脚本用 .cjs）。
- 项目结构：`build/`（deck_kit.py、pages_*.py、make_deck.py、build_anim.py、render.cjs）、`svg_output/`（原始生成）、`svg_final/`（图标嵌入+样式归一化后）、`animations.json`、`dist/`、`preview/`。

## 1. 全流程命令（按序执行）

```bash
# ① 生成 SVG + 动画 sidecar（make_deck 里含重叠/越界自检，输出"布局校验通过"才继续）
$DECK build/make_deck.py
$DECK build/build_anim.py

# ② 图标嵌入（→ svg_final/）与样式归一化
$DECK "$S/finalize_svg.py" <项目目录>
$DECK "$S/compact_svg_styles.py" --inplace svg_final

# ③ 质检：0 error 才继续
$DECK "$S/svg_quality_checker.py" svg_final --quick-generate

# ④ 终版报告（导出闸门强制）
$DECK "$S/svg_quality_checker.py" . --quick-generate --canonical-authoring --stage final --json

# ⑤ 导出（PowerPoint 若开着同名旧文件会 WinError 32 → 换新文件名）
$DECK "$S/svg_to_pptx.py" <项目目录> -o dist/<名>.pptx -f ppt169 --quick-generate --animation-config animations.json

# ⑥ 验收：XML 动画树 + 悬空引用（脚本见 §4）、OPC、交付检查
$DECK "$S/pptx_opc_validation.py" dist/<名>.pptx          # exit 0
$DECK "$S/pptx_delivery_check.py" dist/<名>.pptx          # errors:[] advisories:[]

# ⑦ 预览渲染 + 总览拼图
node build/render.cjs                                      # → preview/*.png
# PIL 拼 3×5 总览（640×360 缩略），存 dist/总览-15页.png
```

改动 SVG 后再导出时，④必须重跑（报告过期会被导出闸门拒绝）。

## 2. animations.json sidecar schema

```json
{
  "settings": { "canvas": { "width": 1280, "height": 720 } },
  "pages": [
    {
      "svg": "03-scene.svg",
      "groups": {
        "header":      { "effect": "entrance_fade",  "order": 1, "duration": 0.6 },
        "scene-left":  { "effect": "entrance_wipe",  "order": 2, "duration": 0.8, "trigger": "after-previous", "delay": 0.2, "effect_options": { "direction": "left" } },
        "scene-right": { "effect": "entrance_wipe",  "order": 3, "trigger": "on-click", "effect_options": { "direction": "left" } }
      }
    }
  ]
}
```

要点：
- `trigger` 取值：缺省（自动，首组）/ `after-previous` / `on-click` / `with-previous`。
- **效果全集 = 203 种原生动画**（注册表：`$S/pptx_animation_presets.json`，key 为 snake_case）：
  - 53 入场（`entrance_fade / fly / wipe / rise_up / faded_zoom / glide / appear / expand / zoom / dissolve / circle / box / diamond / wheel …`）
  - **33 强调**（`emphasis_change_fill_color / grow_shrink / spin / transparency / pulse / shimmer …`）——"变黄""高亮""放大"这类语义，用强调类比"退出再入场"干净得多
  - **64 路径**（`path_circle / path_right_triangle / path_diamond …`）——元素沿轨迹移动
  - **53 退出**（`exit_fade / fly / dissolve …`）——真正的"插入动画"需要它：旧行退出 + 新行入场
- **`effect_options` 按效果严格校验，名字错一个字都导不出**（如 `emphasis_change_fill_color` 的颜色选项叫 `color`，不叫 `amount`——报错时会列出该效果支持的全部选项名）；`entrance_fly`/`entrance_wipe` 支持 `direction`，`entrance_glide` 不支持 direction。**动用没验证过的效果前，先跑一次最小 PoC 读回 XML**（presetClass：entr/emph/path/exit；presetID 与 manifest 的 preset_id 一致）。
- 先跑 `$DECK "$S/animation_config.py" validate <项目目录>` 自检（输出 "Animation config validated successfully." / "全部匹配"）。

### 转场（slides[].transition）

- 支持 **58 种 PowerPoint 原生转场**：`morph / fade / push / wipe / reveal / split / cut / uncover / cover / cube / zoom / flip / orbit / fly_through / dissolve / checkerboard / …`（完整列表：`pptx_animations.get_available_transitions()`）。
- **morph**（平滑）是最值得用的一个：写入 `<p159:morph option="byObject"/>`，两页间的同名/同形状对象会自动补间。用法：把"变化前/变化后"拆成两页，两页里放**同 id、同几何近似的对象**，其余对象不动——得到 Copilot "Morph-ready 版式"的效果。
- 其余转场一页配一次即可；答辩场景建议全片统一 1–2 种，别一页一个花样。

## 3. SVG 编写契约（ppt-master shared-standards-core 要点）

- 根 `<svg>` 带 `lang="zh-CN"` 与 `data-pptx-page-role`。
- **每个顶层 `<g>` 必须声明 `data-pptx-bounds="x y w h"`**——包括 header/footer/装饰组（只有根级原语免声明）。
- 顶层组两两重叠 >1px（双轴）= fail；**任何一方带 structural role（如 `data-pptx-role="decoration"`）这一对即豁免**（checker 成对短路）。decoration 组转换后仍是正常形状，sidecar 显式条目可给它动画（转换器只把无 sidecar 条目的 Chrome/装饰组排除在自动动画外）。
- 禁用：`class`、`<style>`、`mask`、SMIL（`<animate*>`）、`@font-face`、HTML 命名实体。
- `<` `>` 写成 `&lt;` `&gt;`（如 "< 60%"）。
- 多行文本：`<text>` 内定位 `<tspan x dy>`，不要折行空格凑数。
- 渐变直接内联两停 `<linearGradient>`；超过两停要用 svg-effects.md 的进阶写法。
- rotate 之外的 transform 先查 svg-effects.md。
- 字体：`Noto Serif SC`/`Noto Sans SC` 会被映射为 SimSun/Microsoft YaHei（数字保留 Consolas）——PPT 安全回退，可接受。
- 1 SVG px = 9,525 EMU；画布 1280×720 = ppt169。

## 4. XML 验收脚本要点

动画计数**正确口径**：遍历 `p:cTn` 元素读 **nodeType 属性**：

```python
click = len([e for e in root.findall('.//p:cTn', ns) if e.get('nodeType')=='clickEffect'])
# withEffect / afterEffect 同理
```

⚠️ `p:clickEffect` **不是真实元素**——数它会得到整齐的 0（误报"没动画"）。真正的触发语义全在属性里。

悬空引用：`p:spTgt/@spid` ⊆ 本 slide 所有 `p:cNvPr/@id`。
编排抽验：对关键页打印 `nodeType + 目标 shape name + presetClass/presetID`，与设计逐条对照。
presetClass/presetID 速查：entr/10 淡入、entr/22 擦除、entr/37 缩放、entr/2 飞入。

## 5. 踩坑清单（全部实测）

1. **bg 矩形被"背景提升"删除**：finalize 阶段把全画布 `id="bg"` 矩形提升为 PPT 原生页面背景并从 svg_final 删除 → 深底页预览全白是**预览假象**，PPTX 里正常。探针别测背景。
2. **框架代码编辑后必须 grep 复验**：deck_kit 的 svg() 曾因悬空 else（grad 分支与 extra_defs 分支嵌套错）导致 P15 既无渐变 defs 又无 bg 矩形。"编辑成功" ≠ 内容落盘。
3. **深色底上的浅色小标签** = 白色补丁穿帮（压在曲线上尤其明显）。改用空白区图例。
4. **Unicode 上下标渲染异常**（ₜₐᵣ）→ ASCII：`S′_tar`。
5. **只有顶层组可动画**。单条曲线要分阶段出现 → 拆成多个不重叠 facet 组，或用 decoration 豁免重叠。
6. **轨道/时间条宽度按分钟比例**要留标签空间（文本 y 偏移 20/36 分两行），否则文字挤出块外。
7. **组 bounds 相邻衔接**：层叠图每组 bounds 要正好衔接（`ly-6, 高94` 这类），否则自检报重叠 6px。
8. **文本超出组 bounds 11% 会被抓**：长句拆三个短行，别一条 text 拉满。
9. **Windows 文件锁**：PowerPoint 开着旧 pptx（`~$xxx` 锁文件 + POWERPNT.EXE 进程）→ 同名覆盖 WinError 32。**换名导出 v2/v3，不杀用户进程**。
10. **Playwright ESM 忽略 NODE_PATH**：渲染脚本用 CommonJS（render.cjs）+ 绝对路径 require。
11. **checker 的"段落建议"类 warning**（多段短句同区域）对"语义独立的短句"是误报，人工判断后可放行；但 bounds 越界类 warning 必须修。
12. **探针采样要踩描边**：验证"描边颜色"时坐标取边框线上的值，踩进填充区会误判 FAIL；半透明元素阈值按实际 opacity 调整，别用纯色阈值。
13. **导出前最后一次改动 SVG 后**，final 报告必须重跑；样式归一化可能改 id，动画验证（§4）也要重做。
14. **quick-generate 读的是 `svg_output/`，不是 `svg_final/`**；且强制要求当前 svg_output 的 final 质检报告，缺了会直接拒绝导出（按提示补跑即可）。
15. **强调/路径动画的选项名各有各的拼法**（`color` / `amount` / 角度…），不要凭直觉猜——报错信息会列出支持项；新效果先过一遍最小 PoC。

## 6. 可编辑性审计与讲稿（对标补充）

### 可编辑性审计（交付前最后一道）

业内通用的"压平试纸"（HTML 转图、整页截图类生成器都过不了）：

1. **双击图表** → 能弹出"编辑数据"表格 = 数据绑定的原生图表；只是形状 = SVG 绘制路线（本管线的默认）。
2. **独立改三样**：一个标题、一个数字、换一张图——三者互不影响 = 未压平。
3. 本管线的文本/形状天然过 2；但 **SVG 画的图表不含数据表**。若受众可能双击查数（财务、答辩数据页），改走 ppt-master 的 `--native-charts-and-tables` 路线（代价：跨软件渲染可能不一致，需人工复核）。

### 讲稿与备注（生成流程的第 9 步）

Anthropic/Copilot 都会写 speaker notes；本管线默认漏了这步。交付前给每页补 3–5 句讲稿写进 `p:notes`（ppt-master 支持备注→TTS 旁白音轨，可导出自放映版本）。讲稿从每页的"金句 + 论据"直接改写成口语，不另起炉灶。

### 视觉闭环（渲染→审视→修正）

DeepPresenter（PPTAgent 2.0）的核心贡献是"环境感知反思"：生成→渲染→截图→审视→修正。本管线的对应物已内建：quality checker（bounds/重叠/越界）→ render.cjs 预览 → 像素探针/直方图 → 修正重跑。**任何新页面都没有"写完就算完成"，必须过一遍这个闭环**。Anthropic pptx skill 的做法可作参照：逐页渲染 JPG 后按固定维度检查（溢出/重叠/对比度/对齐/风格一致）。

## 7. 对标与选型边界（2026-11 调研）

| 方案 | 一句话定位 | 相对本管线 |
| --- | --- | --- |
| Gamma / Canva / Beautiful.ai | 网页卡片，30 秒出稿 | **动效导出即蒸发**；导出 PPTX 失真；中文会"意译润色"数据 |
| Copilot（PowerPoint 内） | 企业合规、可改可协作 | 动画要人手在 Animation Pane 搭；设计平庸 |
| Kimi Slides | 长文档→PPT，**图表导出为原生对象** | 无逐对象动画；慢；官方声明不保证事实准确 |
| Anthropic pptx skill | 稳、改现有稿、XML 增量编辑 | "只有 60 分"（其自我定位）；无 SVG 设计感路线 |
| ppt-master 全流程 | 文档→原生 PPTX | 本管线 = 其 SVG 路线的手写精修版 |
| Marp / Slidev / Reveal | 代码化幻灯片 | **PPTX = 每页一张图**，动画只活在浏览器里 |

**本管线的结构性优势（也是存在的理由）**：

1. **原生逐对象动画编排**——市面工具几乎都不做（预设转场 ≠ 编排）；203 种效果 + morph 可用。
2. **确定性代码框架**（deck_kit 是手写代码，只有内容是 AI 生成的）——避开了"LLM 写 python-pptx 代码→执行→构建"路线的代码注入、不可复现、"修改即重构"三宗罪（WPS 灵犀内置技能被公开批评的正是这条路径）。
3. **XML 级验收**——多数工作流停在"导出成功"；本管线看 nodeType 口径、悬空引用、编排对照、OPC、交付检查。

**诚实边界（何时不用本管线）**：需要数据绑定的原生图表 → ppt-master `--native-charts-and-tables` 或 Kimi；要改别人的 .pptx → Anthropic pptx 的 XML 增量编辑；纯网页演示 → Slidev/frontend-slides。SmartArt、宏、嵌入视频本管线不支持。
