#!/usr/bin/env python3
# 三件事：
#   1. 查所有 Markdown 里的相对链接和锚点，有没有指向不存在的文件或标题
#   2. 重新渲染一遍网页版，跟仓库里已提交的 index.html 对比，看有没有忘记重建
#   3. 查网页版内部的锚点有没有坏链
# 任何一项不过，退出码为 1。用法： python3 tools/check.py
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402

ROOT = build.ROOT
problems = []


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def headings(md):
    return [build.anchor(l.lstrip("# ").strip()) for l in md.split("\n") if l.startswith("#")]


def all_markdown():
    out = ["README.md", "DISCLAIMER.md", "应急卡.md"]
    docs = os.path.join(ROOT, "docs")
    out += ["docs/" + n for n in sorted(os.listdir(docs)) if n.endswith(".md")]
    return [p for p in out if os.path.exists(os.path.join(ROOT, p))]


# 1. Markdown 内的链接
LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
for rel in all_markdown():
    src = os.path.join(ROOT, rel)
    md = read(src)
    for m in LINK.finditer(md):
        url = m.group(2)
        if url.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target, _, frag = url.partition("#")
        if not target:
            continue
        dst = os.path.normpath(os.path.join(os.path.dirname(src), target))
        if not os.path.exists(dst):
            problems.append("%s：链接指向不存在的文件 -> %s" % (rel, url))
            continue
        if frag and dst.endswith(".md"):
            if frag not in headings(read(dst)):
                problems.append("%s：锚点不存在 -> %s" % (rel, url))

# 2. index.html 是不是最新的
out = build.render()
dst = os.path.join(ROOT, "index.html")
if not os.path.exists(dst):
    problems.append("index.html 不存在，请先跑 python3 tools/build.py")
else:
    old = read(dst)
    if old != out:
        problems.append("index.html 跟 Markdown 对不上，请重新跑 python3 tools/build.py")

# 3. 网页版内部锚点
if os.path.exists(dst):
    page = read(dst)
    ids = set(re.findall(r'id="([^"]+)"', page))
    for href in set(re.findall(r'href="#([^"]+)"', page)):
        if href not in ids:
            problems.append("index.html：锚点不存在 -> #%s" % href)

if problems:
    print("检查不通过，共 %d 处：" % len(problems))
    for p in problems:
        print("  - " + p)
    sys.exit(1)

print("检查通过")
print("  Markdown 文件 %d 个，链接和锚点全部有效" % len(all_markdown()))
print("  index.html 是最新的")
print("  网页版内部锚点全部有效")
