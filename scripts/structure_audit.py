# -*- coding: utf-8 -*-
r"""结构审计（通用引擎，openfoam-research-init skill）：工作级 AGENTS.md 目录结构漂移对账。

对每个 工作*\（有 AGENTS.md 者）双向对账：
  [未提及] 顶层实际目录存在，但 AGENTS.md 全文未出现其名——新增/改名目录未登记；
  [已消失] AGENTS.md 中以**链接目标**（](<X/…) / ](X/…)）引用的顶层目录不存在
           （链接 = 目录实体引用；反引号提及太弱不报，防代码内子目录误伤）。
报告不代改：AGENTS 是人拍板的规则文档，修正由人工/AI 按报告执行。
退出码：0 = 无漂移；1 = 有漂移；2 = 输入错误。

用法：python structure_audit.py --config <project.json> [工作名...]
config 复用索引生成器的 project.json（layer_root / works_prefix / ext_dirs 可选）。
"""
import json
import re
import sys
from pathlib import Path

BACKTICK = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"\]\(<?([^)\s<>]+)")

LANG = "zh"          # config 键 lang：zh（缺省）/ en


def T(zh, en):
    return zh if LANG == "zh" else en


def main():
    argv = sys.argv[1:]
    cfg_path = None
    if "--config" in argv:
        i = argv.index("--config")
        cfg_path = argv[i + 1]
        del argv[i:i + 2]
    if not cfg_path:
        sys.exit(T("[结构审计] 必须给 --config <project.json>",
                   "[structure-audit] --config <project.json> is required"))
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8-sig"))  # sig：容忍编辑器加 BOM
    global LANG
    LANG = cfg.get("lang", "zh")
    layer = (Path(cfg_path).resolve().parent / cfg["layer_root"]).resolve()
    prefix = cfg.get("works_prefix", "工作")
    # 方向层公共目录与约定临时桶：工作 AGENTS 合法提及、但不属于本工作顶层
    ext = set(cfg.get("ext_dirs", ["公共库", "工具脚本", "reference_materials", "手稿规范"]))
    ext |= {"tmp", ".agents", ".git", "__pycache__"}

    names = [a for a in argv if not a.startswith("--")]
    works = [layer / n for n in names] if names else \
        sorted(p for p in layer.iterdir() if p.is_dir() and p.name.startswith(prefix))

    rc = 0
    print(T("=== 结构审计：AGENTS.md 目录结构漂移（报告不代改）",
            "=== Structure audit: AGENTS.md directory drift (reports, never edits)"))
    for work in works:
        agents = work / "AGENTS.md"
        if not agents.exists():
            continue
        text = agents.read_text(encoding="utf-8", errors="ignore")
        tops = sorted(d.name for d in work.iterdir() if d.is_dir())
        probs = []
        for d in tops:                                   # 主检：实际目录未提及
            if d not in text and d not in ext:
                probs.append(T("[未提及] 顶层目录 %s 存在，AGENTS.md 未登记",
                               "[unmentioned] top-level directory %s exists but AGENTS.md never registers it") % d)
        for tgt in LINK.findall(text):                   # 副检：链接引用的顶层目录已消失
            first = tgt.replace("\\", "/").split("/")[0].split("#")[0]
            if ("." in first or not first or first in ("..", ".")
                    or first in tops or first in ext):
                continue
            probs.append(T("[已消失] AGENTS.md 链接引用目录 %s，顶层不存在（改名/删除后未更新）",
                           "[vanished] AGENTS.md links to directory %s, absent at top level (renamed/deleted but never updated)") % first)
        if probs:
            rc = 1
            print("[%s]" % work.name)
            for p in probs:
                print("  " + p)
        else:
            print(T("[%s] 无漂移", "[%s] no drift") % work.name)
    sys.exit(rc)


if __name__ == "__main__":
    main()
