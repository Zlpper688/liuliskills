# 依据：与通用设计知识的对照

本规范的每条规则都不是凭空来的——它们与公开的设计学研究和平台规范一致。下表是对照关系，用于说明"为什么这样设计站得住"，不改变规范本身。

| 本规范的规则 | 通用依据 | 出处 |
| --- | --- | --- |
| 胶囊分动词 / 变量两种形态 | Material Design 3 把 chips 分为 assist / filter / input / suggestion 四类，用于紧凑承载操作与选项；本规范按"是否承载变量"二分，粒度更少 | [M3 Chips](https://m3.material.io/components/chips/overview) |
| 变量胶囊点开才出现选择器 | 渐进披露（Progressive Disclosure）：先给最小入口，细节与输入按需展开，降低首次认知负担 | [NN/g: Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) |
| 二元出口（搁置 / 下一个空闲；完成 / 未完成） | Hick's Law：选项越多决策越慢；Schwartz《选择的悖论》：过多选项降低行动率。被发现的明确问题只需要出口，不需要报告 | Hick, W. E. (1952); Schwartz, B. (2004) |
| 什么都不点 = 保持现状，永不追问 | Microsoft Human-AI Interaction 指南 G8「支持高效关闭」、G9「支持高效纠正」：用户能轻松忽略或纠正 AI 的输出 | [HAX Toolkit](https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines)、[Amershi et al., CHI 2019](https://dl.acm.org/doi/10.1145/3290605.3300233) |
| 不预填、推荐不上表面、决策权留给用户 | Shneiderman 的 Human-Centered AI 框架：在提高自动化程度的同时确保人的控制；智能默认值可以在系统内部生效，但关键决策的入口必须交还用户 | [Shneiderman, Human-Centered AI（OUP 2022）](https://books.google.ca/books?id=YS9VEAAAQBAJ) |
| 少写字、界面安静 | Calm Technology：最核心的信息以最平静的方式呈现，技术退到边缘 | Weiser & Brown, "The Coming Age of Calm Technology" (1996) |

## 一句话总结

胶囊层 = **动作即界面**（动词胶囊）+ **接口即自由**（变量胶囊打开原生编辑器）。前者承接决策，后者承接变量；两者共同保证"系统有耐心，用户说了算"。
