# -*- coding: utf-8 -*-
r"""索引生成器（通用引擎，openfoam-research-init skill 随身分发）：自动生成各工作 研究文档\00-索引.html。

00-索引.html（唯一索引）：科技树 + 体检报告 + 流向图 + 借用图 + 文档清单，
全部 HTML+SVG 自排布（零依赖、零渲染引擎、浏览器直接打开）。

依赖与排序：
  * 依赖边 = 文档内全部跨课题相对链接（头部引用块 + 正文引用均算；过时/失败文档不参与）；
  * 排序自动计算：rank = 1 + max(依赖方 rank)（依赖越少越前；多依赖排最近依赖之后）；
    字母 = A + rank - 1；`O-` = others 不参与排序、与 A 同免上游声明要求；
  * 科技树箭头 = 上游 → 下游；
  * `--apply-sort`：按计算结果 git mv 改名课题目录 + 改写研究文档域内链接 + 再生索引。

AI记录（config 键 ai_notes_dir，缺省 "AI记录"）= 只由 AI 维护的自由区：
正位在工作根（<工作>\AI记录\，索引扫描域 研究文档\ 之外，天然不进科技树/文档清单/依赖图/排序与上游声明要求）；
研究文档内的存量同名目录同样识别并忽略。
链接卫生仍覆盖：AI记录 内文件参与死链检测；其它文档链接指向该目录 → 体检报错（正文依赖保持人工闭环）。

用法：python index_generator.py --config <project.json> [工作名] [--apply-sort]
       缺省 = 扫描配置根下全部 <工作前缀>*\（有 研究文档 者）。
项目差异全部走 config（json）：layer_root（方向层根，相对 config 位置）、works_prefix、
docs_dir、code_dir、pub_dir——引擎零机器路径、零项目硬编码。
规则正本：本 skill references/audit-and-tooling.md。
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

LAYER = None          # 由 config 装载（方向层根）
PUB = None            # LAYER / pub_dir
WORKS_PREFIX = "工作"
DOCS_DIR = "研究文档"
CODE_DIR = "代码"
AI_NOTES_DIR = "AI记录"
SKIP_DIRS = {"__pycache__", ".git"}
SCAN_EXT = {".py", ".sh", ".ps1", ".jsx"}
PREFIX_RE = re.compile(r"^([A-Z])-(.+)$")

LANG = "zh"          # config 键 lang：zh（缺省）/ en —— 引擎控制台输出与生成页文案语言


def T(zh, en):
    """输出文案双语化：缺省中文，config 设 lang=en 时英文。"""
    return zh if LANG == "zh" else en


def root_label():
    return T("（根）", "(root)")

FLOW_TARGET = [
    re.compile(r"数据[\\/]原始"),
    re.compile(r"数据[\\/]衍生[\\/]+([^\\/，。\s`）)、\"']+)"),
    re.compile(r"算例集合[\\/]+([^\\/，。\s`）)、\"']+)"),
    re.compile(r"(?:/home/[\w.-]+|~)[\\/]OpenFOAM"),
    re.compile(r"(?:~/[\w.-]*deploy|[\w.-]+@[\w.-]+:)"),
]
STD = set("""os sys json math re subprocess shutil pathlib csv argparse collections matplotlib scipy
numpy pandas glob time datetime copy itertools functools typing dataclasses enum warnings logging tempfile
hashlib unittest abc io struct xml ast importlib inspect traceback platform getpass uuid random statistics
operator heapq bisect array contextlib textwrap string fnmatch gzip zipfile tarfile configparser numbers
cmath fractions decimal errno signal socket threading multiprocessing queue select sqlite3 pickle base64
codecs locale gettext PIL cv2 sklearn torch openpyxl xlrd docx pptx fitz yaml toml chardet colorama tqdm
requests http urllib ftplib smtplib email paraview vtk __future__""".split())


def load_config(cfg_path):
    """装载项目配置：设置 LAYER / PUB / WORKS_PREFIX / 目录名 / LANG。返回 config dict。"""
    global LAYER, PUB, WORKS_PREFIX, DOCS_DIR, CODE_DIR, AI_NOTES_DIR, LANG
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8-sig"))  # sig：容忍编辑器加 BOM
    LANG = cfg.get("lang", "zh")
    LAYER = (Path(cfg_path).resolve().parent / cfg["layer_root"]).resolve()
    PUB = LAYER / cfg.get("pub_dir", "公共库")
    WORKS_PREFIX = cfg.get("works_prefix", "工作")
    DOCS_DIR = cfg.get("docs_dir", "研究文档")
    CODE_DIR = cfg.get("code_dir", "代码")
    AI_NOTES_DIR = cfg.get("ai_notes_dir", "AI记录")
    if not LAYER.is_dir():
        sys.exit(T("[索引生成器] config.layer_root 无效：%s",
                   "[index-generator] invalid config.layer_root: %s") % LAYER)
    return cfg


def git_root():
    """git 仓根（--apply-sort 的 git mv 工作目录），从 LAYER 向上探测。"""
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=LAYER,
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("[索引生成器] 不在 git 仓内：%s" % LAYER)
    return Path(r.stdout.strip())


def iter_files(base, exts):
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            yield p


def normalize_paths(text):
    text = re.sub(r"['\"]\s*,\s*['\"]", "\\\\", text)
    text = re.sub(r"['\"]\s*/\s*['\"]", "\\\\", text)
    return text.replace("/", "\\")


# ---------------- 文档网络：清单 + 头部引用块上游边 + 死链 ----------------
def head_quote(text):
    """文档头部引用块（H1 标题后、正文前，最多 10 行窗口内的连续 > 块）；无则返回 ''。"""
    lines = text.splitlines()
    i, seen_h1 = 0, False
    for i, ln in enumerate(lines):
        if ln.startswith("# ") and not seen_h1:
            seen_h1 = True
            break
    if not seen_h1:
        i = -1
    buf, in_q = [], False
    for ln in lines[i + 1:i + 12]:
        if ln.startswith(">"):
            in_q = True
            buf.append(ln[1:].strip())
        elif ln.strip() == "" and not in_q:
            continue                            # 标题后的空行
        elif in_q:
            break                               # 引用块结束
        else:
            break                               # 先遇正文 → 无头部引用块
    return "\n".join(buf)


def extract_links(text):
    ts = re.findall(r"\]\(<([^>]+)>\)", text)
    ts += re.findall(r"\]\((?!<)(?!https?:)([^)\s]+)\)", text)
    return [t.split("#")[0] for t in ts if t.split("#")[0]]


def scan_docs(docs_root, index_path):
    mds = sorted(p for p in iter_files(docs_root, {".md"}) if p.resolve() != index_path.resolve())
    # AI记录 正位在工作根（docs_root 之上、索引域外，天然不进索引）；研究文档内存量同名目录一并扫描识别。
    # 两处均仅参与链接检测与引用禁令，不进清单/依赖图/排序。
    notes_root = (docs_root.parent / AI_NOTES_DIR).resolve()
    ext_notes = sorted(iter_files(notes_root, {".md"})) if notes_root.is_dir() else []
    disp = {}                                   # p → 相对 docs_root 的显示路径（工作根 AI记录 虚拟挂接）
    for p in mds:
        disp[p] = p.relative_to(docs_root)
    for p in ext_notes:
        disp[p] = Path(AI_NOTES_DIR) / p.relative_to(notes_root)
    listing = {}
    for p in mds:
        topic = disp[p].parts[0] if len(disp[p].parts) > 1 else root_label()
        if topic == AI_NOTES_DIR:
            continue                            # AI记录：不进清单/依赖图/排序（链接仍检测）
        listing.setdefault(topic, []).append(p)
    edges, broken, stale_ref, nolink, ai_ref = set(), set(), set(), {}, set()
    for p in mds + ext_notes:
        try:
            text = p.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            continue
        rel = disp[p].parts
        src = rel[0] if len(rel) > 1 else root_label()
        in_notes = src == AI_NOTES_DIR
        doc_stale = bool(re.search(r"过时|失败|outdated|failed", str(disp[p])))  # 文档名或所在子目录名含标记
        q_links = extract_links(head_quote(text))
        all_links = extract_links(text)
        for raw in all_links:                   # 有效性检查：全文链接（含 AI记录 内文件）
            abs_t = (p.parent / raw).resolve()
            try:
                t_parts = abs_t.relative_to(docs_root).parts
            except ValueError:
                # 目标在研究文档域之外：指向工作根 AI记录 时仍执行引用禁令与死链检测
                if ext_notes and abs_t.is_relative_to(notes_root) and not in_notes:
                    ai_ref.add("%s → %s" % (disp[p], raw))          # 引用禁令
                    if not abs_t.exists():
                        broken.add("%s → %s" % (disp[p], raw))
                continue
            if t_parts and t_parts[0] == AI_NOTES_DIR and not in_notes:
                ai_ref.add("%s → %s" % (disp[p], raw))  # 引用禁令
            if not abs_t.exists():
                broken.add("%s → %s" % (disp[p], raw))
            elif in_notes:
                pass   # AI记录 内指向 (过时)/(失败) 文档属正常（注解对象常为过时/失败），豁免
            elif re.search(r"过时|失败|outdated|failed", abs_t.name):
                stale_ref.add("%s → %s（过时/失败）" % (disp[p], abs_t.name))
        # 依赖边：全文链接（头部引用块 + 正文引用均算依赖；过时/失败文档与 AI记录 不参与）。
        # 目标可为文档或课题目录（目录目标 parts 长 1，须是真实课题目录）。
        q_cross = 0
        q_up = 0
        if not doc_stale and not in_notes:
            for raw in all_links:
                abs_t = (p.parent / raw).resolve()
                try:
                    t_parts = abs_t.relative_to(docs_root).parts
                except ValueError:
                    continue
                if (abs_t.exists() and t_parts
                        and (docs_root / t_parts[0]).is_dir()):
                    if raw in q_links:
                        q_up += 1            # 引用块上游链接（同课题或跨课题均可）
                    if t_parts[0] != src:
                        edges.add((src, t_parts[0]))
                        if raw in q_links:
                            q_cross += 1
        # 上游声明要求：有前缀且非 A/O 的课题，非过时文档，引用块须有上游链接（同课题或跨课题均可）
        m = PREFIX_RE.match(src)
        if m and m.group(1) not in ("A", "O") and not doc_stale and not in_notes and q_up == 0:
            nolink.setdefault(src, []).append(str(disp[p]))
    return listing, edges, broken, stale_ref, nolink, ai_ref


# ---------------- 科技树：字母分组（总 TD 排行 / 行内均布） ----------------
def topic_rank(topic):
    """返回 (序值, 字母或None)。O 最后；无前缀在 O 之前；同字母按名排序。"""
    m = PREFIX_RE.match(topic)
    if not m:
        return (2, "")                          # 无前缀：O 之前
    letter = m.group(1)
    return (1, letter) if letter == "O" else (0, letter)


def render_tree(docs_root, listing, edges, ranks):
    """HTML+SVG 自排布科技树（00-索引.html）：行=rank（A→…→O 置底）、行内均布、
    依赖箭头坐标自算——不依赖任何渲染引擎，布局完全确定。"""
    topics = sorted(set(listing) | {a for a, _ in edges} | {b for _, b in edges})
    topics = [t for t in topics if t != root_label()]
    if not topics:                                              # 新建骨架：研究文档尚无课题目录
        return T("<p>（暂无课题目录——首个课题目录建立后重跑再生）</p>",
                 "<p>(no topic directories yet — rerun after the first topic directory is created)</p>")

    def t_letter(t):
        m = PREFIX_RE.match(t)
        return m.group(1) if m else "·"

    def bullets_of(t):
        out = []
        tdir = docs_root / t
        if tdir.is_dir():
            for ch in sorted(tdir.iterdir(), key=lambda x: x.name):
                if ch.name in SKIP_DIRS:
                    continue
                if ch.is_dir():
                    nm = ch.name + "/"
                elif ch.suffix.lower() == ".md":
                    nm = ch.name[:-3]
                else:
                    continue
                out.append((nm, bool(re.search(r"过时|失败|outdated|failed", nm))))
        return out

    def text_w(s):
        return sum(15 if ord(ch) > 0x2E7F else 8 for ch in s)

    LH, PAD_X, PAD_Y = 22, 14, 11
    GAP_H, GAP_V, MARGIN_L, MARGIN_R = 48, 78, 56, 24
    nodes = {}
    for t in topics:
        bs = bullets_of(t)
        w = min(max([text_w(t)] + [text_w("• " + b) for b, _ in bs]) + 2 * PAD_X, 560)
        h = (1 + len(bs)) * LH + 2 * PAD_Y
        nodes[t] = dict(name=t, bullets=bs, w=w, h=h)
    letters = []
    for t in topics:
        L = t_letter(t)
        if L not in letters:
            letters.append(L)
    letters.sort(key=lambda L: (L == "O", L == "·", L))          # A..Z, 无前缀·, O 最后
    rows = [(L, [t for t in topics if t_letter(t) == L]) for L in letters]

    y = 24
    for L, ts in rows:                                            # 逐行排布
        x = MARGIN_L
        for t in ts:
            nodes[t]["x"] = x
            nodes[t]["y"] = y
            x += nodes[t]["w"] + GAP_H
        y += max(nodes[t]["h"] for t in ts) + GAP_V
    canvas_w = max((nodes[t]["x"] + nodes[t]["w"]) for t in topics) + MARGIN_R
    canvas_h = y - GAP_V + 24

    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'font-family="system-ui,\'Microsoft YaHei\',sans-serif">' % (canvas_w, canvas_h),
           '<defs><marker id="arr" markerWidth="9" markerHeight="9" refX="7" refY="4.5" '
           'orient="auto"><path d="M0,0 L8,4.5 L0,9 z" fill="#555"/></marker></defs>']
    for L, ts in rows:                                            # 行标签
        yy = nodes[ts[0]]["y"] + nodes[ts[0]]["h"] / 2
        svg.append('<text x="18" y="%.0f" font-size="17" font-weight="600" fill="#888">%s</text>'
                   % (yy + 6, esc(L)))
    for a, b in sorted(edges):                                    # 箭头：依赖方 a(下行) → 被依赖方 b(上行)
        if a not in nodes or b not in nodes:
            continue
        na, nb = nodes[a], nodes[b]
        sx, sy = na["x"] + na["w"] / 2, na["y"]                   # a 顶边中点
        ex, ey = nb["x"] + nb["w"] / 2, nb["y"] + nb["h"]         # b 底边中点
        svg.append('<path d="M%.0f,%.0f C%.0f,%.0f %.0f,%.0f %.0f,%.0f" fill="none" '
                   'stroke="#555" stroke-width="1.3" marker-end="url(#arr)"/>'
                   % (sx, sy, sx, sy - 36, ex, ey + 36, ex, ey))
    for t in topics:                                              # 课题卡片
        n = nodes[t]
        svg.append('<g><title>%s</title>' % esc(t))
        svg.append('<rect x="%d" y="%d" width="%d" height="%d" rx="7" fill="#fff" '
                   'stroke="#222" stroke-width="1.4"/>' % (n["x"], n["y"], n["w"], n["h"]))
        ty = n["y"] + PAD_Y + 15
        svg.append('<text x="%d" y="%d" font-size="14.5" font-weight="700" fill="#111">%s</text>'
                   % (n["x"] + PAD_X, ty, esc(n["name"])))
        for i, (b, stale) in enumerate(n["bullets"]):
            ty += LH
            fill = "#999" if stale else "#333"
            svg.append('<text x="%d" y="%d" font-size="12.5" fill="%s">• %s</text>'
                       % (n["x"] + PAD_X, ty, fill, esc(b)))
        svg.append("</g>")
    svg.append("</svg>")
    return "\n".join(svg)


def render_bipartite(edges, edge_labels=None):
    """两列自排布 SVG：左 = 源（代码目录），右 = 目标；箭头左→右。
    edge_labels: {(src,tgt): 标签文本}（借用图的模块名）。返回 svg 字符串。"""
    if not edges:
        return T("<p>（无）</p>", "<p>(none)</p>")
    srcs = sorted({s for s, _ in edges})
    tgts = sorted({t for _, t in edges})

    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def tw(s):
        return sum(15 if ord(c) > 0x2E7F else 8 for c in s)

    NH, GAP_V, PAD_X, COL_GAP, MX = 30, 14, 12, 190, 24
    wl = max(tw(s) for s in srcs) + 2 * PAD_X
    wr = max(tw(t) for t in tgts) + 2 * PAD_X
    hl = len(srcs) * (NH + GAP_V) - GAP_V
    hr = len(tgts) * (NH + GAP_V) - GAP_V
    H = max(hl, hr) + 2 * MX
    x_l, x_r = MX, MX + wl + COL_GAP
    pos_l = {s: (x_l, MX + (H - 2 * MX - hl) / 2 + i * (NH + GAP_V)) for i, s in enumerate(srcs)}
    pos_r = {t: (x_r, MX + (H - 2 * MX - hr) / 2 + i * (NH + GAP_V)) for i, t in enumerate(tgts)}
    W = x_r + wr + MX
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'font-family="system-ui,\'Microsoft YaHei\',sans-serif">' % (W, H),
           '<defs><marker id="arr2" markerWidth="9" markerHeight="9" refX="7" refY="4.5" '
           'orient="auto"><path d="M0,0 L8,4.5 L0,9 z" fill="#777"/></marker></defs>']
    for s, t in sorted(edges):
        (x1, y1), (x2, y2) = pos_l[s], pos_r[t]
        sy, ty = y1 + NH / 2, y2 + NH / 2
        svg.append('<path d="M%.0f,%.0f C%.0f,%.0f %.0f,%.0f %.0f,%.0f" fill="none" '
                   'stroke="#777" stroke-width="1.2" marker-end="url(#arr2)"/>'
                   % (x1 + wl, sy, x1 + wl + 60, sy, x2 - 60, ty, x2, ty))
        if edge_labels and (s, t) in edge_labels:
            mx, my = (x1 + wl + x2) / 2, (sy + ty) / 2 - 4
            svg.append('<text x="%.0f" y="%.0f" font-size="10.5" fill="#999" text-anchor="middle">%s</text>'
                       % (mx, my, esc(edge_labels[(s, t)])))
    for s, (x, y) in pos_l.items():
        svg.append('<rect x="%d" y="%d" width="%d" height="%d" rx="5" fill="#fff" stroke="#333"/>'
                   % (x, y, wl, NH))
        svg.append('<text x="%d" y="%.0f" font-size="12" fill="#111">%s</text>'
                   % (x + PAD_X, y + NH / 2 + 4, esc(s)))
    for t, (x, y) in pos_r.items():
        svg.append('<rect x="%d" y="%d" width="%d" height="%d" rx="5" fill="#f2f6f2" stroke="#3a5a3a"/>'
                   % (x, y, wr, NH))
        svg.append('<text x="%d" y="%.0f" font-size="12" fill="#111">%s</text>'
                   % (x + PAD_X, y + NH / 2 + 4, esc(t)))
    svg.append("</svg>")
    return "\n".join(svg)


def render_flow(ins, outs):
    """三列流向图：左 = 数据\\原始（只读输入），中 = 代码，右 = 衍生/算例/运行区（输出）。
    箭头方向 = 数据流方向：原始 → 代码 → 目标；无输入边时退化为两列（代码 → 目标）。
    ins: {(原始, 代码目录)}；outs: {(代码目录, 目标)}。返回 svg 字符串。"""
    if not ins and not outs:
        return T("<p>（无）</p>", "<p>(none)</p>")
    srcs = sorted({s for _, s in ins} | {s for s, _ in outs})
    lefts = sorted({t for t, _ in ins})
    rights = sorted({t for _, t in outs})

    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def tw(s):
        return sum(15 if ord(c) > 0x2E7F else 8 for c in s)

    NH, GAP_V, PAD_X, COL_GAP, MX = 30, 14, 12, 190, 24
    wl = max([tw(t) for t in lefts] + [0]) + 2 * PAD_X
    wc = max(tw(s) for s in srcs) + 2 * PAD_X
    wr = max([tw(t) for t in rights] + [0]) + 2 * PAD_X
    ns = (len(lefts), len(srcs), len(rights))
    H = max(n * (NH + GAP_V) - GAP_V for n in ns if n) + 2 * MX
    x_l = MX
    x_m = MX + (wl + COL_GAP if lefts else 0)
    x_r = x_m + wc + COL_GAP
    pos_l = {t: (x_l, MX + (H - 2 * MX - (len(lefts) * (NH + GAP_V) - GAP_V)) / 2
             + i * (NH + GAP_V)) for i, t in enumerate(lefts)}
    pos_m = {s: (x_m, MX + (H - 2 * MX - (len(srcs) * (NH + GAP_V) - GAP_V)) / 2
             + i * (NH + GAP_V)) for i, s in enumerate(srcs)}
    pos_r = {t: (x_r, MX + (H - 2 * MX - (len(rights) * (NH + GAP_V) - GAP_V)) / 2
             + i * (NH + GAP_V)) for i, t in enumerate(rights)}
    W = (x_r + wr + MX) if rights else (x_m + wc + MX)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'font-family="system-ui,\'Microsoft YaHei\',sans-serif">' % (W, H),
           '<defs><marker id="arr2" markerWidth="9" markerHeight="9" refX="7" refY="4.5" '
           'orient="auto"><path d="M0,0 L8,4.5 L0,9 z" fill="#777"/></marker></defs>']
    for t, s in sorted(ins):                          # 原始 → 代码
        (x1, y1), (x2, y2) = pos_l[t], pos_m[s]
        sy, ty = y1 + NH / 2, y2 + NH / 2
        svg.append('<path d="M%.0f,%.0f C%.0f,%.0f %.0f,%.0f %.0f,%.0f" fill="none" '
                   'stroke="#777" stroke-width="1.2" marker-end="url(#arr2)"/>'
                   % (x1 + wl, sy, x1 + wl + 60, sy, x2 - 60, ty, x2, ty))
    for s, t in sorted(outs):                         # 代码 → 目标
        (x1, y1), (x2, y2) = pos_m[s], pos_r[t]
        sy, ty = y1 + NH / 2, y2 + NH / 2
        svg.append('<path d="M%.0f,%.0f C%.0f,%.0f %.0f,%.0f %.0f,%.0f" fill="none" '
                   'stroke="#777" stroke-width="1.2" marker-end="url(#arr2)"/>'
                   % (x1 + wc, sy, x1 + wc + 60, sy, x2 - 60, ty, x2, ty))
    for t, (x, y) in pos_l.items():
        svg.append('<rect x="%d" y="%d" width="%d" height="%d" rx="5" fill="#eef3fb" stroke="#2f4a7a"/>'
                   % (x, y, wl, NH))
        svg.append('<text x="%d" y="%.0f" font-size="12" fill="#111">%s</text>'
                   % (x + PAD_X, y + NH / 2 + 4, esc(t)))
    for s, (x, y) in pos_m.items():
        svg.append('<rect x="%d" y="%d" width="%d" height="%d" rx="5" fill="#fff" stroke="#333"/>'
                   % (x, y, wc, NH))
        svg.append('<text x="%d" y="%.0f" font-size="12" fill="#111">%s</text>'
                   % (x + PAD_X, y + NH / 2 + 4, esc(s)))
    for t, (x, y) in pos_r.items():
        svg.append('<rect x="%d" y="%d" width="%d" height="%d" rx="5" fill="#f2f6f2" stroke="#3a5a3a"/>'
                   % (x, y, wr, NH))
        svg.append('<text x="%d" y="%.0f" font-size="12" fill="#111">%s</text>'
                   % (x + PAD_X, y + NH / 2 + 4, esc(t)))
    svg.append("</svg>")
    return "\n".join(svg)


# ---------------- 依赖排序：rank = 1 + max(依赖方 rank)，字母 = A + rank-1 ----------------
def compute_ranks(edges, topics):
    """topics = 参与排序的课题（有前缀且非 O）。返回 (ranks, cycle)。
    依赖越少越前；依赖多目录时排在最近（最晚）依赖之后 ⇒ 最长路分层。
    O 参与的边不约束排序。"""
    deps = {t: set() for t in topics}
    for a, b in edges:
        if a in deps and b in deps:
            deps[a].add(b)                        # a 引用 b ⇒ a 依赖 b
    rank, state, cycle = {}, {}, []

    def visit(t, stack):
        if state.get(t) == 2:
            return rank[t]
        if state.get(t) == 1:
            cycle.extend(stack[stack.index(t):] + [t])
            return 0
        state[t] = 1
        r = 1 + max((visit(d, stack + [t]) for d in sorted(deps[t])), default=0)
        state[t] = 2
        rank[t] = r
        return r

    for t in sorted(topics):
        visit(t, [])
    return rank, sorted(set(cycle))


def sort_letter(rank_int):
    return chr(ord("A") + rank_int - 1)


# ---------------- 体检 ----------------
def audit_problems(broken, stale_ref, listing, edges, nolink, ranks, cycle, ai_ref):
    """返回问题列表（空 = 无问题）。报告不代改。"""
    probs = []
    for b in broken:
        probs.append(T("死链：%s", "Dead link: %s") % b)
    for s in stale_ref:
        probs.append(T("引用指向过时/失败文档：%s", "Reference points at an outdated/failed doc: %s") % s)
    for x in sorted(ai_ref):
        probs.append(T("引用 AI记录（其它文档不得引用——正文依赖保持人工闭环）：%s",
                       "References AI-notes (forbidden from other docs — body dependencies stay human-loop): %s") % x)
    for t, docs in sorted(listing.items()):
        if t != root_label() and not docs:
            probs.append(T("空课题目录：%s", "Empty topic directory: %s") % t)
    topics = [t for t in listing if t != root_label()]
    unprefixed = [t for t in sorted(topics) if not PREFIX_RE.match(t)]
    if unprefixed:
        probs.append(T("未安排排序（目录名缺 <字母>- 前缀）：%s",
                       "Unsorted (directory name missing the <letter>- prefix): %s") % "、".join(unprefixed))
    for t in sorted(nolink):
        probs.append(T("缺上游引用块（%s- 类文档头部引用块须列出上游链接）：%s（%d 篇）",
                       "Missing upstream head-quote (%s- class docs must list upstream links in the head quote): %s (%d docs)")
                     % (PREFIX_RE.match(t).group(1), t, len(nolink[t])))
    if cycle:
        probs.append(T("循环依赖（人工/AI 裁定后才能自动排序）：%s",
                       "Circular dependency (needs a human/AI ruling before auto-sorting): %s") % " → ".join(cycle))
    elif ranks:
        mism = []
        for t in sorted(ranks):
            want = sort_letter(ranks[t])
            cur = PREFIX_RE.match(t).group(1)
            if cur != want:
                mism.append("%s（%s- → %s-）" % (t, cur, want))
        if mism:
            probs.append(T("排序与依赖不符（按依赖自动计算应重排；--apply-sort 应用）：%s",
                           "Sort order disagrees with dependencies (computed from dependencies; apply with --apply-sort): %s")
                         % "、".join(mism))
    if not probs:
        return []
    return probs


# ---------------- 代码网络 ----------------
def code_node_fn(code_root):
    def fn(p):
        rel = p.relative_to(code_root).parts
        return "代码\\" + "\\".join(rel[:min(2, len(rel) - 1)])
    return fn


def scan_flow(code_root):
    """扫代码路径字面量 → 流向边。方向按两桶规则归类（类别自带方向，不解析读写调用）：
    ins  = 数据\\原始 → 代码（原始桶只读，代码对它只有读关系）；
    outs = 代码 → 目标（衍生/算例/运行区：代码产出或部署目标）。"""
    cn = code_node_fn(code_root)
    ins, outs = set(), set()
    for p in iter_files(code_root, SCAN_EXT):
        try:
            text = normalize_paths(p.read_text(encoding="utf-8-sig", errors="ignore"))
        except Exception:
            continue
        src = cn(p)
        for pat in FLOW_TARGET:
            for m in pat.finditer(text):
                tgt = m.group(0).rstrip("\\\"' ")
                if "OpenFOAM" in tgt:
                    tgt = "WSL 运行区 ~/OpenFOAM"
                elif "deploy" in tgt or "@" in tgt:
                    tgt = "集群运行区"
                if tgt == "数据\\原始":
                    ins.add((tgt, src))
                else:
                    outs.add((src, tgt))
    return ins, outs


def scan_borrow(code_root):
    cn = code_node_fn(code_root)
    mod_dir = {}
    for p in iter_files(code_root, {".py"}):
        mod_dir.setdefault(p.stem, cn(p))
    if PUB.is_dir():
        for p in iter_files(PUB, {".py"}):
            if p.parent == PUB:
                mod_dir.setdefault(p.stem, "公共库")
            else:
                mod_dir.setdefault(p.stem, "公共库\\" + "\\".join(p.relative_to(PUB).parts[:-1]))
    edges = set()
    for p in iter_files(code_root, {".py"}):
        try:
            text = p.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", text, re.M):
            mod = m.group(1).split(".")[0]
            if mod in STD or mod == p.stem:
                continue
            tgt = mod_dir.get(mod)
            if tgt and tgt != cn(p):
                edges.add((cn(p), tgt, mod))
    return edges


# ---------------- 00-索引.html 写出 ----------------
def sort_topics(edges, listing):
    """返回 (ranks, cycle)：参与排序 = 有前缀且非 O 的课题。"""
    topics = {t for t in listing if t != root_label()
              and PREFIX_RE.match(t) and PREFIX_RE.match(t).group(1) != "O"}
    return compute_ranks(edges, topics)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_content(work_name, docs_root):
    index_path = docs_root / "00-索引.html"
    listing, edges, broken, stale_ref, nolink, ai_ref = scan_docs(docs_root, index_path)
    ranks, cycle = sort_topics(edges, listing)
    tree_svg = render_tree(docs_root, listing, edges, ranks)
    audit = audit_problems(broken, stale_ref, listing, edges, nolink, ranks, cycle, ai_ref)

    code_root = LAYER / work_name
    flow = scan_flow(code_root / CODE_DIR) if (code_root / CODE_DIR).is_dir() else (set(), set())
    flow_svg = render_flow(*flow)

    borrow = scan_borrow(code_root / CODE_DIR) if (code_root / CODE_DIR).is_dir() else set()
    blabels = {}
    bedges = set()
    for s, t, m in borrow:
        bedges.add((s, t))
        blabels.setdefault((s, t), []).append(m)
    blabels = {k: "、".join(sorted(v)) for k, v in blabels.items()}
    borrow_svg = render_bipartite(bedges, blabels)

    rows = []
    for topic in sorted(listing):
        for p in sorted(listing[topic], key=str):
            rel = str(p.relative_to(docs_root)).replace("\\", "/")
            stale = bool(re.search(r"过时|失败|outdated|failed", rel))
            rows.append('<tr><td>%s</td><td>%s</td><td>%s</td></tr>'
                        % (esc(topic), esc(rel),
                           T("⚠ 过时/失败", "⚠ outdated/failed") if stale else ""))
    return tree_svg, audit, flow_svg, borrow_svg, rows


def update_index(work_name, docs):
    tree_svg, audit, flow_svg, borrow_svg, rows = build_content(work_name, docs)
    audit_html = (T("<p>✔ 无问题：无死链、无过时引用、无空目录，上游声明与目录排序合规。</p>",
                    "<p>✔ No problems: no dead links, no stale references, no empty directories; upstream declarations and directory sorting all compliant.</p>")
                  if not audit else
                  "<ul>\n" + "\n".join("<li>⚠ %s</li>" % esc(a) for a in audit) + "\n</ul>")
    doclist_html = ("<table>\n<tr><th>%s</th><th>%s</th><th>%s</th></tr>\n"
                    % (T("课题", "Topic"), T("文档", "Document"), T("标记", "Marker"))
                    + "\n".join(rows) + "\n</table>")
    html = r"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body{{margin:0;padding:24px 28px;background:#fafafa;font-family:system-ui,'Microsoft YaHei',sans-serif;color:#222}}
h1{{font-size:20px;margin:0 0 4px}}
h2{{font-size:16px;margin:28px 0 10px;padding-bottom:6px;border-bottom:1px solid #ddd}}
.note{{color:#888;font-size:12.5px;margin-bottom:6px}}
svg{{background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.12);max-width:100%}}
ul{{margin:6px 0;padding-left:22px;font-size:13.5px}} li{{margin:3px 0}}
p{{font-size:13.5px}}
table{{border-collapse:collapse;font-size:12.5px;background:#fff}}
th,td{{border:1px solid #ccc;padding:4px 10px;text-align:left}}
th{{background:#f0f0f0}}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="note">{gen_note}</div>

<h2>{h_tree}</h2>
<div class="note">{n_tree}</div>
{tree}
<h2>{h_audit}</h2>
{audit}
<h2>{h_flow}</h2>
<div class="note">{n_flow}</div>
{flow}
<h2>{h_borrow}</h2>
<div class="note">{n_borrow}</div>
{borrow}
<h2>{h_list}</h2>
{doclist}
</body>
</html>
""".format(lang=LANG,
           title=T("研究文档索引", "Research document index") + " · " + esc(work_name),
           gen_note=T("本文件由 <b>openfoam-research-init skill 的 index_generator.py</b> 完全自动生成，勿手改——重跑即再生；规则见 skill references/audit-and-tooling.md。",
                      "This file is fully auto-generated by <b>index_generator.py</b> of the openfoam-research-init skill — never hand-edit; rerun to regenerate. Rules: the skill's references/audit-and-tooling.md."),
           h_tree=T("科技树", "Tech tree"),
           n_tree=T("行 = 排序字母（A→…→O 置底，左侧行标），同行 = 同序列平行；箭头 = 上游 → 下游；灰字 = 过时/失败。",
                    "Row = sort letter (A→…→O at the bottom, row labels on the left); same row = parallel in the same series; arrows = upstream → downstream; grey text = outdated/failed."),
           h_audit=T("体检报告", "Health report"),
           h_flow=T("数据 ⇆ 代码 流向图", "Data ⇆ code flow"),
           n_flow=T("扫代码路径字面量，按两桶规则定方向：左「数据\\原始」= 只读输入（原始 → 代码）；右列衍生/算例/运行区 = 代码输出（代码 → 目标）；「WSL/集群运行区」= 脚本内写死的仓外运行路径。",
                    "Scans path literals in code, directions per the two-bucket rule: left column 数据\\原始 = read-only inputs (raw → code); right column derived/cases/run-areas = code outputs (code → target); the WSL/cluster run area = out-of-repo run paths hard-coded in scripts."),
           h_borrow=T("代码借用图（跨目录 import）", "Code borrowing (cross-directory imports)"),
           n_borrow=T("边标签 = 借用模块；公共库模块解析含方向层 公共库\\。",
                      "Edge labels = borrowed modules; shared-library module resolution includes the layer-level 公共库\\."),
           h_list=T("文档清单", "Document inventory"),
           tree=tree_svg, audit=audit_html,
           flow=flow_svg, borrow=borrow_svg, doclist=doclist_html)
    out = docs / "00-索引.html"
    out.write_text(html, encoding="utf-8", newline="\n")
    print(T("  [写出] 00-索引.html（%d 体检项）", "  [written] 00-索引.html (%d health items)") % len(audit))


def apply_sort(work_name, docs, index_path):
    """--apply-sort：按依赖计算字母 git mv 改名课题目录 + 改写研究文档域内链接 + 再生索引。
    仅当依赖图无循环时执行；循环/未安排排序的课题不动。"""
    listing, edges, _, _, _, _ = scan_docs(docs, index_path)
    ranks, cycle = sort_topics(edges, listing)
    if cycle:
        sys.exit(T("[apply-sort] %s 存在循环依赖，人工/AI 裁定后再排：%s",
                   "[apply-sort] %s has a circular dependency; resolve it manually before sorting: %s")
                 % (work_name, " → ".join(cycle)))
    renames = {}                                   # 旧课题名 → 新课题名
    for t in sorted(ranks):
        want = sort_letter(ranks[t])
        cur = PREFIX_RE.match(t).group(1)
        if cur != want:
            renames[t] = "%s-%s" % (want, PREFIX_RE.match(t).group(2))
    if not renames:
        print(T("[%s] 排序已合规，无需改名", "[%s] sorting already compliant, no renames") % work_name)
        return
    # 1) git mv 课题目录
    root = git_root()
    for old, new in sorted(renames.items()):
        r = subprocess.run(["git", "mv", str(docs / old), str(docs / new)], cwd=root,
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(T("[apply-sort] git mv 失败 %s → %s:\n%s",
                       "[apply-sort] git mv failed %s → %s:\n%s") % (old, new, r.stderr))
        print(T("  [改名] %s → %s", "  [renamed] %s → %s") % (old, new))
    # 2) 改写研究文档域内所有 md 中指向旧课题目录的链接（按解析后路径重求相对链接）
    for p in sorted(docs.rglob("*.md")):
        if p.name == "00-索引.md" or any(x in SKIP_DIRS for x in p.parts):
            continue
        text = p.read_text(encoding="utf-8-sig", errors="ignore")
        orig = text

        def fix(m):
            inner = m.group(1) or m.group(2)
            raw = inner.split("#")[0]
            if not raw:
                return m.group(0)
            try:
                abs_t = (p.parent / raw).resolve()
                parts = abs_t.relative_to(docs.resolve()).parts
            except Exception:
                return m.group(0)
            if not parts or parts[0] not in renames:
                return m.group(0)
            new_abs = docs / renames[parts[0]] / Path(*parts[1:])
            rel = os.path.relpath(new_abs, p.parent).replace("\\", "/")
            frag = ("#" + inner.split("#", 1)[1]) if "#" in inner else ""
            return "](%s%s)" % (rel, frag)

        text = re.sub(r"\]\(<([^>]+)>\)|\]\(([^)\s]+)\)", fix, text)
        if text != orig:
            p.write_text(text, encoding="utf-8", newline="\n")
            print(T("  [改链] %s", "  [relinked] %s") % p.relative_to(docs))


# ---------------- config 初始化（--init，供新项目/新用户） ----------------
IDX_CFG_DEFAULT = {
    "layer_root": "..",
    "lang": "zh",
    "works_prefix": "工作",
    "docs_dir": "研究文档",
    "ai_notes_dir": "AI记录",
    "code_dir": "代码",
    "pub_dir": "公共库",
    "ext_dirs": ["公共库", "工具脚本", "reference_materials", "手稿规范"],
}
REPL_CFG_TEMPLATE = {
    "layer_root": "..",
    "lang": "zh",
    "works_prefix": "工作",
    "code_dir": "代码",
    "pub_dir": "公共库",
    "wsl_distro": "Ubuntu-22.04",
    "cluster_ssh": "<集群SSH别名>",
    "wsl_find": "find /home/<用户>/OpenFOAM/<项目> \\( -name '*.py' -o -name '*.sh' \\) -not -path '*__pycache__*' -print0 | xargs -0 md5sum 2>/dev/null",
    "cluster_probe": "ssh -o ConnectTimeout=10 -o BatchMode=yes <集群SSH别名> 'echo __REACHABLE__'",
    "cluster_find": "find ~/<部署目录> -maxdepth 4 \\( -name '*.py' -o -name '*.sh' \\) -not -path '*__pycache__*' -print0 | xargs -0 md5sum 2>/dev/null",
    "ignore": ["initialRun.sh"],
}


def init_configs(layer):
    r"""--init <方向层根>：在其 工具脚本\ 下生成两份 config（已存在者不动，防覆盖）。"""
    tools = layer / "工具脚本"
    tools.mkdir(parents=True, exist_ok=True)
    for name, cfg in (("索引生成器.config.json", IDX_CFG_DEFAULT),
                      ("副本巡检.config.json", REPL_CFG_TEMPLATE)):
        p = tools / name
        if p.exists():
            print(T("  [跳过] %s 已存在（防覆盖）", "  [skip] %s already exists (never overwritten)") % p)
            continue
        p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8", newline="\n")
        print(T("  [生成] %s", "  [generated] %s") % p)
    print(T("提示：索引 config 即开即用；巡检 config 为模板——改 wsl_distro、wsl_find、cluster_* 为本机实际后使用；lang=en 可切英文输出。",
             "Tip: the index config works as-is; the audit config is a template — set wsl_distro, wsl_find and cluster_* to your machine; lang=en switches engine output to English."))


def main():
    argv = sys.argv[1:]
    if "--init" in argv:                             # 新项目/新用户：生成 config 后退出
        i = argv.index("--init")
        root = Path(argv[i + 1]) if i + 1 < len(argv) else Path(".")
        init_configs(root.resolve())
        sys.exit(0)
    cfg_path = None
    if "--config" in argv:
        i = argv.index("--config")
        cfg_path = argv[i + 1]
        del argv[i:i + 2]
    if not cfg_path:
        sys.exit(T("[索引生成器] 必须给 --config <project.json>（项目差异全在 config）",
                   "[index-generator] --config <project.json> is required (all project differences live in the config)"))
    load_config(cfg_path)
    do_sort = "--apply-sort" in argv
    names = [a for a in argv if not a.startswith("--")]
    works = [LAYER / name for name in names] if names else \
        sorted(p for p in LAYER.iterdir() if p.is_dir() and p.name.startswith(WORKS_PREFIX))
    for work in works:
        if not work.is_dir():
            sys.exit(T("[索引生成器] 工作不存在: %s", "[index-generator] work not found: %s") % work.name)
        docs = work / DOCS_DIR
        if not docs.is_dir():
            print(T("[%s] 无 %s，跳过（建立后自动纳入）", "[%s] no %s, skipped (included once created)")
                  % (work.name, DOCS_DIR))
            continue
        print("[%s]" % work.name)
        if do_sort:
            apply_sort(work.name, docs, docs / "00-索引.html")
        update_index(work.name, docs)


if __name__ == "__main__":
    main()
