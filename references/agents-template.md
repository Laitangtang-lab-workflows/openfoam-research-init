# Work-level AGENTS.md template

> At scaffold time, generate the first version from this template; from then on the file is an **instance** (rules written by humans, work-specific), with directory-structure drift reconciled by `structure_audit.py` as a backstop. Replace `<>` placeholders at creation.

# AGENTS.md

> One-sentence overview of <work name> (physics problem / method). The generic canon for directory structure lives in the `openfoam-research-init` skill (agents-template / top-level-conventions); major revisions sync both ways.

## 1. Directory structure (four-line layering)

> **Four-line layering** (code separated from data, one-way flow `raw →(code)→ derived → research docs`):
>
> | Line | Directory | Rule |
> |---|---|---|
> | Code | `代码\` (per-research-part code (`工况生成\` → post-processing toolchain), …; cross-work shared libraries at the layer level `公共库\`) | pure scripts and libraries, zero data; scripts anchor to the work root via `__file__` |
> | Data | `数据\原始\` (read-only) / `数据\衍生\` (regenerable) | two-bucket rule, see the skill quick reference |
> | Documents | `研究文档\` (narrative mainline) + work-root `AI记录\` (AI free-maintenance zone; `AI纪律.md` created at scaffold time, template in the skill's audit-and-tooling onboarding checklist); body text written by humans (AI annotations/extensions go to `AI记录\`, never referenced by other documents); `00-索引.html` fully auto-generated (never hand-edit; engine and rules in the skill's audit-and-tooling); writing rules in the layer-level AGENTS research-docs section |
> | Cases | `算例集合\` | frozen archive of computation inputs; **a case must be frozen and locked before entering a compute environment** (freeze before running); `00-算例台账.md` registry + `00-运行台账.md` run log |
>
> `手稿\`, `AI分析\`, `operations\` stay at the top level; this work has no private tools directory (generic tools shared at the layer level `工具脚本\`). Top-level and asset-library conventions: see the skill's top-level-conventions.md.

## 2. Canonical-copy discipline (Win ↔ run side)

- **The Win repo is the single canonical copy**; run sides (WSL / cluster) hold running copies only.
- **Downstream pushes come from Win only**; **upstream must be copied back** (a closing condition of every session).
- **Audit**: `replica_audit.ps1 -Config <layer>\工具脚本\副本巡检.config.json` (three-way hash reconciliation; pending back-copies are exactly the audit's remote-only items).

<!-- Add sections as needed: work-specific condition families, scale conventions, devices/paths, etc. -->
