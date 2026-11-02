---
name: native-pptx-craft
description: 原生动画 PPT 制作技能：手写 SVG + ppt-master 管线生成带原生 PowerPoint 动画（逐条出现、点击触发、插入/变黄等编排）的真 .pptx 文件，沉淀了整套设计思想与实测经验教训——信息密度四层结构、疏密有度、去AI味、不踩一捧一、文字简约性、SVG 契约、动画 XML 验收口径、13 条管线坑。当用户要求"做PPT/改PPT/答辩PPT/汇报PPT"，且需要真 PowerPoint 文件而非 HTML，或要求"一条一条出现/点击一下再出现/插入动画"等原生动画效果时使用。前置条件：本机已克隆 hugohe3/ppt-master 仓库。
agent_created: true
---

# Native PPTX Craft

答辩/汇报 PPT 的标准打法：**手写 SVG → ppt-master 转 DrawingML → 原生动画注入 → 五道验收**。
与 HTML 幻灯片的本质区别：产物是真 .pptx，动画是 PowerPoint 原生时序树（可演示、可二次编辑），不是网页。

本技能来自一个 15 页毕业答辩 PPT 的完整实战（四轮迭代），所有规则都经过实测——包括踩过的坑。

## 环境约定（全文命令使用这两个变量）

- `$DECK` = 专用 Python 虚拟环境的解释器（需装有 `python-pptx`、`lxml`、`pillow`；不要用系统 Python 混装）。
- `$S` = ppt-master 仓库的 `scripts/` 目录（`git clone https://github.com/hugohe3/ppt-master`）。
- 项目目录结构：`build/`（页面生成脚本）、`svg_output/`（原始生成）、`svg_final/`（图标嵌入+样式归一化后）、`animations.json`、`dist/`、`preview/`。

## 设计铁律（动手前先读，细则见 references/design-principles.md）

1. **信息密度四层**：每个要点 = 小标题 + 论据/数据 + 金句 + 收束总结。密度是底线，但排布要疏密有度——分区间留白，别平均塞满。
2. **文字简约性**：一页一个主诉求。封面尤其克制（大标题 + 一行副题，不堆装饰）。
3. **不踩一捧一**：讲优势时只说"我能做什么"，绝不写"网页版做不到/别人不行"。
4. **不拆台**：讲待解决问题时不说"我们没有数据/没做完"，改说"这是下一步"。
5. **去AI味**：不用排比堆砌词、不用"赋能/抓手"，用具体数字（292 分钟、0.50/1.30/2.00）和具体行为（"点哪块进哪块"）。
6. **配图真实感，且必须与产品代码对账**：手机 mockup 画全拟真骨架（金属亮边、细 bezel、挖孔镜头环、侧键、home indicator），屏内画应用实际布局——**字段与文案取自真实代码/真实字符串，不编造功能**。PPT 里写了代码里没有的功能，答辩时被问"这个功能在哪"就穿帮。
7. **动效有叙事**：动画按"讲故事的顺序"编排，不是按图层顺序。关键交互（结果揭晓、对比、插入过程）用 on-click，其余自动级联。

## 标准管线（八步，全部要跑，顺序不可换）

1. **建页**：复制 `assets/deck_kit.py` 到 `build/`，按其 Page 类写页面模块（每页一个函数，**一个顶层 `<g>` = 一个动画步**）。
2. **写编排**：写脚本生成 `animations.json` sidecar（schema 见 references/pipeline-and-pitfalls.md）。
3. **生成 + 收尾**：
   ```bash
   $DECK build/make_deck.py && $DECK build/build_anim.py
   $DECK "$S/finalize_svg.py" <项目目录>          # 图标嵌入 → svg_final/
   $DECK "$S/compact_svg_styles.py" --inplace svg_final
   ```
4. **质检**：`$DECK "$S/svg_quality_checker.py" svg_final --quick-generate` → 0 error 才能继续（warning 逐条人工判断）。
5. **终版报告**：`$DECK "$S/svg_quality_checker.py" . --quick-generate --canonical-authoring --stage final --json`（导出闸门强制要求；改过 SVG 后必须重跑）。
6. **导出**：`$DECK "$S/svg_to_pptx.py" . -o dist/名.pptx -f ppt169 --quick-generate --animation-config animations.json`
7. **XML 级验收**（见下"验收纪律"）。
8. **OPC + 交付检查**：`pptx_opc_validation.py`（exit 0）+ `pptx_delivery_check.py`（errors:[] advisories:[]）。

## 验收纪律（不看"导出成功"四个字，看 XML 真相）

- **动画计数口径**：`p:cTn` 的 **nodeType 属性**（clickEffect/withEffect/afterEffect），不是 `p:clickEffect` 元素——后者不存在，会得出"0 动画"的误报。
- **悬空引用**：每个 `p:spTgt/@spid` 必须能在本 slide 的 `p:cNvPr/@id` 里找到，0 悬空才算过。
- **编排抽验**：把关键页的 click/after 目标名打印出来，与设计意图逐条对照。
- **视觉验收**：`assets/render.cjs`（Playwright，CommonJS）渲染 svg_final → PNG；由于 svg_final 的 `id="bg"` 会被提升为 PPT 原生背景并从 SVG 中删除，**深底页预览会变白底——这不是 bug，PPTX 里是好的**；探针只测前景元素。目检不可用时用 PIL 像素探针：描边采样要踩在 stroke 坐标上；单点探针会踩文字反锯齿造成假 FAIL，改用区域直方图判色。

## 高频坑速查（完整清单与解法见 references/pipeline-and-pitfalls.md）

- 顶层 `<g>`（含 header/footer/装饰）**必须**带 `data-pptx-bounds`；普通组重叠 >1px = error，**需重叠的动画组标 `data-pptx-role="decoration"` 即豁免**（成对短路），且 sidecar 仍可给它显式动画。
- 只有**顶层组**能成为动画目标；嵌套组不产生动画步。需要分段动画的曲线/时间轴 → 拆成多个不重叠的组（或 decoration 豁免）。
- SVG 里 `<` `>` 必须 `&lt;` `&gt;`；禁 class/style/mask/SMIL；渐变只用两停；Unicode 上下标（ₜₐᵣ）渲染异常 → 用 ASCII（S′_tar）。
- 深色底上放浅色小标签 = 白色补丁穿帮；改用图例。
- Windows 上 PowerPoint 开着旧文件（`~$` 锁 + POWERPNT 进程）会让同名导出 WinError 32 —— 换名导出，别杀进程。
- 编辑框架代码后必须 grep 复验关键行真的落盘（"编辑成功" ≠ 内容落盘；一个悬空 else 曾让整页丢背景矩形）。

## Resources

- `assets/deck_kit.py` — 可复用 SVG 页面框架（Page 类：bounds 声明/重叠校验/decoration 豁免/自定义 defs/页眉页脚/常用图元/拟真手机外框 `phone_frame()`）。
- `assets/render.cjs` — Playwright 批量渲染 svg_final → preview/*.png（CommonJS；`DECK_ROOT` 环境变量指定项目根，默认当前目录）。
- `references/design-principles.md` — 设计思想细则：密度四层、疏密节奏、配图原则、动效叙事编排、文案口径。
- `references/pipeline-and-pitfalls.md` — 管线全命令、animations.json schema、SVG 契约要点、完整踩坑清单（13 条实测教训）。
