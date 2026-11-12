# Research docs, index and audits: canon + engine usage + onboarding checklist

> Canon lives with the openfoam-research-init skill; the research-docs section of a project's layer-level AGENTS is an instance (major revisions sync both ways).
> Three engines: `scripts\index_generator.py` (00-index generation), `scripts\replica_audit.ps1` (three-replica audit), `scripts\structure_audit.py` (AGENTS drift reconciliation) — all follow the **report/generate, never silently edit** rule; project differences go through config.

## 1. Research-doc writing rules (same mechanism for every work)

- **One directory per research part**: `研究文档\<topic-dir>\` is a tech-tree node; the topic narrative lives in that topic's documents, never in the index.
- **Head quote = upstream declaration**: every md file opens with a blockquote right after its H1, listing **only its dependencies** as relative links (never downstream — the generator infers those); `A-` (no upstream) and `O-` (others) are exempt; any other topic doc missing its upstream link (same-topic or cross-topic both count) → health-check error.
- **`00-索引.html` is the single, fully auto-generated index** (never hand-edit; rerun to regenerate).
- **Filename lifecycle markers**: `(过时)` (outdated), `(失败)` (failed) suffixes (marked ⚠ in the inventory, kept, not deleted); variants use suffixes (e.g. `_eps0075`).
- **Human/AI division of labor**: research-doc bodies stay concise and are written by humans (legacy docs exempt; new docs follow this); AI annotations, explanations and extensions go to `工作<n>\AI记录\` at the work root (current convention — outside the index scan domain `研究文档\`, naturally excluded from tech tree / inventory / sorting; legacy copies still under `研究文档\AI记录\` are recognized and equally ignored) — read, modified and maintained by AI only, exempt from every rule in this section (links still get dead-link checks); other documents (manuscripts included) must not reference it — a reference is a health-check error; when the body text has errors, AI lists suggested changes, and whether and how to change is the user's call.

## 2. Sorting canon (topic directory name prefixes)

- Topic directories carry a sort prefix `<letter>-` (e.g. `A-控制方程与问题描述`).
- **Three principles**: fewer dependencies sorts earlier; a dependent directory must sort after everything it depends on; with multiple dependencies, sort right after the nearest one.
- rank = 1 + max(dependency rank) (longest-path layering), letter = A + rank − 1, same rank same letter in parallel; `O-` does not participate and sorts last.
- Dependency = cross-topic relative links (head-quote and body links both count; outdated/failed docs excluded).
- `--apply-sort`: renames topic directories via `git mv` per the computed result + rewrites in-domain links + regenerates the index (cycles need a human ruling).

## 3. Health checks (index_generator scan detections; reports, never edits)

| Check | Criterion |
|---|---|
| Dead link | relative link target does not exist |
| References outdated | link points at an `(过时)/(失败)` doc (`AI记录` exempt — its annotation targets are often outdated/failed) |
| References AI记录 | a document outside links into `AI记录\` (forbidden — body dependencies stay human-loop; detected within the research-docs domain; the manuscript side relies on discipline) |
| Empty topic dir | directory with no md at all |
| Unsorted | topic directory name missing the `<letter>-` prefix |
| Missing upstream | non-A/O topic doc has no upstream link in its head quote (same-topic or cross-topic both count) |
| Sort mismatch | current letter ≠ computed letter (applied by --apply-sort) |
| Circular dependency | dependencies form a cycle (human/AI ruling) |

## 4. Three-replica audit philosophy (replica_audit)

- **The Win repo is the single canonical copy** (git-versioned); run sides (WSL/cluster) are running copies.
- **Downstream only from Win**: deployment scripts must come from the canonical copy, logged in the run ledger at deployment.
- **Upstream must come back**: code created or modified on the run side is copied back to the canonical copy and committed before closing the session — copy-back is a closing condition.
- Audit = basename/hash reconciliation: **same-name drift resolves in favor of Win** (downstream overwrite); files that exist only on the run side are pending back-copies; same content under a different name = renamed deployment (recognized, not a false alarm); ignore lists go in the config (case-level runtime clutter).

## 5. Engine invocation (call the engines directly; the project side keeps only configs)

**Config convention**: configs live in the layer-level `工具脚本\`, named after their engine (`索引生成器.config.json`, `副本巡检.config.json`); **generated automatically for new projects/users** — `python …\index_generator.py --init <layer-root>` (writes both into `<layer>\工具脚本\`; existing files are never overwritten; the index config works as-is, the audit config is a template — edit `wsl_distro`, both find commands, and the cluster settings to your machine).

```powershell
# Regenerate the 00-index (default scans all 工作*\; --apply-sort applies re-sorting)
python <repo>\.agents\skills\openfoam-research-init\scripts\index_generator.py --config <layer>\工具脚本\索引生成器.config.json [work] [--apply-sort]
# Three-replica audit (config carries WSL distro / both find commands / ignore list — machine paths never enter the skill)
pwsh -File <repo>\.agents\skills\openfoam-research-init\scripts\replica_audit.ps1 -Config <layer>\工具脚本\副本巡检.config.json
# Work-level AGENTS drift reconciliation (reuses the index config)
python <repo>\.agents\skills\openfoam-research-init\scripts\structure_audit.py --config <layer>\工具脚本\索引生成器.config.json
# Initialize both configs for a new project or user
python <repo>\.agents\skills\openfoam-research-init\scripts\index_generator.py --init <layer-root>
```

Config keys: `lang` (`zh` default / `en` — console output **and** the generated index page), `layer_root` (layer root, relative to the config), `works_prefix`, `docs_dir`, `ai_notes_dir` (AI-notes directory name, default `AI记录` — its canonical place at the work root is outside the index domain; legacy same-name dirs inside the domain are ignored; dead-link checks and the reference ban still apply), `code_dir`, `pub_dir`, `ext_dirs` (structure-audit external directories); the audit config additionally carries `wsl_distro`, `cluster_ssh` (cluster SSH alias, default `cluster`), `wsl_find`, `cluster_probe`, `cluster_find`, `ignore`. English filename markers `outdated`/`failed` are recognized alongside `过时`/`失败`.

## 6. New-project onboarding checklist

1. Build the work directory skeleton (four lines: `代码\ 数据\ 研究文档\ 算例集合\`; at the work root create `AI记录\` and **generate `AI纪律.md` together with it** (the AI free-maintenance zone, outside the index domain; template at the end of this section — doubles as the empty-dir placeholder that enters git) + top-level `手稿\ AI分析\ operations\` (inside `手稿\` also create `AGENTS.md` + `reference\` + `figures\`, with `.gitkeep` in empty dirs — see the academic-manuscript skill's manuscript-dir-agents for the template); two buckets `数据\原始\ 数据\衍生\`);
2. Generate the work-level `AGENTS.md` first version from [agents-template.md](agents-template.md) (humans write the instance afterwards; drift is reconciled by structure_audit);
3. `--init <layer-root>` generates both configs (index works as-is; the audit template needs your distro and both find commands);
4. Run all three engines to verify: index regenerates 00-索引.html, structure audit reports no drift, the audit reaches all sides consistently.

`AI记录\AI纪律.md` (work root) template (copy verbatim when scaffolding in step 1):

```markdown
# AI记录 · AI self-discipline

> This directory is read, modified and maintained by AI only (layer-level AGENTS research-docs rules): all research-doc writing discipline may be ignored here, free-form. Located at the work root (outside the index scan domain), it naturally stays out of `00-索引.html` and out of sorting; other documents and manuscripts must not reference it. Two AI-side self-discipline rules (not writing discipline):

- **Filenames contain the annotated target's name** (e.g. `形貌分析-AI注.md`) — this directory is searched by AI only; future grepping relies on the filename.
- **Periodically merge outdated records**: when the annotated document is `(过时)/(失败)` or a record has been absorbed into the body text, merge, compress or delete it — this directory must not grow without bound.
```

## 7. Division of labor with repo-wide md link checking (lychee pre-commit)

This engine group covers the research-docs domain (cross-topic links, upstream declarations, sorting) and code-copy consistency; link validity of all repo md **at commit time** is the job of the project repo's `.githooks\` pre-commit chain (`lychee.toml` exemption rules) — same names, different duties, not interchangeable.
