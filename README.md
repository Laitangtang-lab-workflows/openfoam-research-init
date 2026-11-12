# openfoam-research-init

**Methodology + tooling for organizing simulation-based research projects (OpenFOAM/CFD in mind): code, data, documents and frozen case inputs live in separate trees, everything stays traceable and machine-independent.**

> [!NOTE]
> This repository is **written and maintained entirely by AI agents** under human direction — see [AI-maintained](#ai-maintained).
> Documentation is English-first; Chinese companions are available ([README.zh-CN.md](README.zh-CN.md), [SKILL.zh-CN.md](SKILL.zh-CN.md)).

## Why

Simulation research accumulates chaos: results nobody can reproduce, case setups that drift from what actually ran, data overwritten by accident, documents that reference nothing real. This project is a convention set (plus three engines that enforce it) distilled from real CFD research projects:

- **Four-line layering** — `code/`, `data/`, `research-docs/` and a frozen `case-archive/` are separate trees with one-way data flow: raw → (code) → derived → (written into) documents. Outputs never feed back into inputs.
- **Two-bucket data rule** — `raw/` (first-hand inputs, strictly read-only) vs `derived/` (anything a script can regenerate). If a script can produce it, it is derived. Whole derived buckets can be deleted and rebuilt at any time.
- **Case registry & freeze discipline** — a case must be frozen and registered in a ledger *before* it is sent to a compute environment. An unfrozen run proves nothing.
- **Explicit-parameter case generation** — cases come from shared generation libraries plus per-condition driver scripts with every parameter spelled out at the top of the file. One file describes one case; no chasing default-value chains.
- **Auto-generated index** — a zero-dependency HTML+SVG index (dependency tree, health report, data-flow and borrow graphs, document inventory) is produced by an engine and never hand-edited.
- **Three-replica audits** — hash-compare the canonical working copy (Windows) against WSL and cluster replicas: detect drift, renamed deployments, and remote-only files that still need copying back.
- **AGENTS.md drift audit** — reconcile what each project's `AGENTS.md` claims about its directory tree against what actually exists.

## The skill format

The core of this repository is a **`SKILL.md` agent skill** (the convention used by Claude Code, DeepSeek Harness and other agent harnesses). Drop the repo into your harness's skill directory and an AI session picks up the whole methodology with it:

```
git clone https://github.com/Laitangtang-lab-workflows/openfoam-research-init ~/.agents/skills/openfoam-research-init
# or per project:  <your-repo>/.agents/skills/openfoam-research-init
```

You can equally read `SKILL.md` and `references/` as plain documentation, or run the engines directly — no harness required.

## Engines

All engines are report/generate-only (they never edit your rules silently), take a JSON config, and contain zero machine-specific paths — every project difference lives in the config. Engine output (including the generated index page) is Chinese by default; set `"lang": "en"` in the config for English.

| Engine | What it does |
|---|---|
| `scripts/index_generator.py` | Regenerates the HTML index; `--apply-sort` re-sorts topic directories by computed dependency rank; `--init <root>` writes config templates for a new project. |
| `scripts/replica_audit.ps1` | Three-way hash audit: Windows canonical vs WSL vs cluster. Reports same-name drift (Windows wins), renamed deployments, and pending back-copy items. |
| `scripts/structure_audit.py` | Diffs each work-level `AGENTS.md` against the actual directory tree. |

Quick start for a new project:

```powershell
python scripts/index_generator.py --init <project-root>    # writes two config templates
python scripts/index_generator.py --config <cfg.json>      # regenerate the index
python scripts/structure_audit.py --config <cfg.json>      # AGENTS drift report
pwsh -File scripts/replica_audit.ps1 -Config <cfg.json>    # three-replica audit
```

## Repository layout

| Path | Content |
|---|---|
| `SKILL.md` | Skill entry point, methodology quick reference |
| `references/` | Full convention set: layout, data buckets, case generation, AGENTS template, engine rules |
| `scripts/` | The three engines |

## AI-maintained

Every file in this repository — code, documentation, this README — is written and updated by AI agents under human supervision. The conventions were distilled from real research projects in which AI sessions were the primary maintainers. Expect commits to be machine-authored; humans review direction and decisions, not lines.

## License

[CC0-1.0](LICENSE) — released to the public domain. Use, fork and vendor it into anything, no attribution required (a nod is always appreciated).

By submitting a pull request you agree that your contributions are dedicated under CC0 as well.
