# openfoam-research-init

**仿真类科研项目（面向 OpenFOAM 与 CFD）的组织方法论与配套工具链：代码、数据、文档、算例四线分离，全程可溯源，零机器路径。**

> [!NOTE]
> 本仓**全部内容由 AI 维护**，人类定方向、做决策，详见 [AI 维护声明](#ai-维护声明)。英文说明见 [README.md](README.md)。

## 解决什么问题

仿真科研做久了必然积攒混乱：结果没人能复现、算例与实际跑的对不上、数据被误写覆盖、文档引用的东西早已不存在。本仓是一套从真实 CFD 研究项目里提炼的约定，配三个引擎强制执行：

- **四线分层**——代码、数据、研究文档、算例冻结归档各占一棵目录树，数据流单向：原始 →（代码）→ 衍生 →（写入）→ 研究文档。输出永不反馈改输入。
- **数据两桶**——`原始\`（一手来源，只读）与 `衍生\`（脚本可再生的产物）。能跑出来的就是衍生，整桶可删可重建。
- **算例台账与跑前冻结**——算例放入计算环境前必须先冻结锁定并登记台账。没冻结的运行证明不了它是什么。
- **参数显式生成**——算例 = 共享生成库加工况驱动脚本，每个工况的全部参数显式写在脚本头部。一个文件即一个算例，不追查默认值链。
- **索引全自动生成**——零依赖的 HTML+SVG 索引（依赖科技树、体检报告、流向图、借用图、文档清单）由引擎再生，永不手改。
- **三方副本巡检**——Win 正本对 WSL 与集群做 hash 对账：识别同名漂移、改名部署、只存在于运行侧的待回传文件。
- **AGENTS 结构审计**——把各项目 `AGENTS.md` 声称的目录结构与实际存在的目录双向对账。

## skill 形态与安装

本仓核心是一个 **`SKILL.md` 格式的 agent skill**（Claude Code、DeepSeek Harness 等 agent 框架通用的技能约定）。把仓 clone 进技能目录，AI 会话即可带着整套方法论工作：

```
git clone https://github.com/Laitangtang-lab-workflows/openfoam-research-init ~/.agents/skills/openfoam-research-init
# 或按项目装：<你的仓>/.agents/skills/openfoam-research-init
```

也可以把 `SKILL.md` 与 `references/` 当普通文档读，或直接运行引擎，不需要任何 agent 框架。

## 引擎

三引擎全部**报告或生成、不代改规则**，项目差异走 JSON config，零机器路径。输出缺省中文，config 设 `"lang": "en"` 可切英文（含生成的索引页面）。

| 引擎 | 职责 |
|---|---|
| `scripts/index_generator.py` | 再生 HTML 索引；`--apply-sort` 按依赖计算结果重排课题目录；`--init <根>` 为新项目生成 config 模板 |
| `scripts/replica_audit.ps1` | Win 正本对 WSL 与集群三方 hash 巡检：同名漂移、改名部署、待回传项 |
| `scripts/structure_audit.py` | 工作级 AGENTS.md 目录结构漂移对账 |

新项目快速上手：

```powershell
python scripts/index_generator.py --init <项目根>       # 生成两份 config 模板
python scripts/index_generator.py --config <cfg.json>   # 再生索引
python scripts/structure_audit.py --config <cfg.json>   # 结构漂移报告
pwsh -File scripts/replica_audit.ps1 -Config <cfg.json> # 三方巡检
```

## 仓库结构

| 路径 | 内容 |
|---|---|
| `SKILL.md` | skill 入口与方法论速查 |
| `references/` | 约定全集：分层、两桶、算例生成、AGENTS 模板、引擎规则 |
| `scripts/` | 三个引擎 |

## AI 维护声明

本仓全部内容（代码、文档、本 README）由 AI 会话在人类监督下编写与更新。方法论本身提炼自 AI 作为主要维护者的真实研究项目。提交均由机器生成，人类把关方向与决策，不逐行审码。

## 证书

[CC0-1.0](LICENSE)——公有领域贡献。可任意使用、fork、并入任何项目，无须署名（注明出处是善意但非义务）。

提交 PR 即表示同意你的贡献同样以 CC0 贡献。
