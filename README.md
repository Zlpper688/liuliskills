# liuliskills

设计向 Skills 集合。每个 skill 是一份可被 AI 助手直接加载的设计规范（标准 `SKILL.md` 格式：frontmatter 触发条件 + 正文规则）。

## Skills

| Skill | 内容 |
| --- | --- |
| [capsule-interface-design](skills/capsule-interface-design/SKILL.md) | 前端胶囊层与外放接口设计规范：回执 = 一句话 + 胶囊；动词胶囊点即生效，变量胶囊只留接口、打开原生选择器；胶囊不内置内容，决策权留给用户 |

## 使用

- **作为技能加载**：把 `skills/<name>/` 放进你的 AI 助手技能目录（如 `.agents/skills/`、`~/.agents/skills/` 等），它会按 frontmatter 里的 description 自动触发。
- **作为评审清单**：直接把 `SKILL.md` 当作前端交互评审的检查表——重点看「四条核心规则」和「反例」两节。

## 目录结构

```text
skills/capsule-interface-design/
├── SKILL.md                    # 规范正文
└── references/
    └── research.md             # 与通用设计学知识的对照与出处
```

## License

[MIT](LICENSE)
