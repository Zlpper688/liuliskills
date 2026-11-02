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
- 已验证可用 effect：`entrance_fade / fly / wipe / rise_up / faded_zoom / glide / appear / expand`。
- **`entrance_fly`/`entrance_wipe` 支持 `direction`；`entrance_glide` 不支持 direction**（配了会校验报错）。
- 先跑 `$DECK "$S/animation_config.py" validate <项目目录>` 自检（输出 "Animation config validated successfully." / "全部匹配"）。

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
