#!/usr/bin/env python3
# 把仓库里的 Markdown 合成一个单页 HTML，方便手机上看、也方便打印成 PDF。
# 用法： python3 tools/build.py
import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 顺序就是网页里的顺序
DOCS = [
    "README.md",
    "docs/00-10分钟版.md",
    "应急卡.md",
    "docs/01-认识开盒.md",
    "docs/02-你暴露了什么.md",
    "docs/03-自查.md",
    "docs/04-加固.md",
    "docs/05-应急.md",
    "docs/06-附录.md",
    "docs/07-未成年人和家长.md",
    "DISCLAIMER.md",
]

REPO_BLOB = "https://github.com/frameira/NovaYu/blob/main/"


def anchor(text):
    """跟 GitHub 一样的锚点算法。"""
    s = text.strip().lower()
    s = "".join(c for c in s if c.isalnum() or c in " -_")
    return s.replace(" ", "-")


def stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def rewrite_link(url, stem_map):
    if url.startswith(("http://", "https://", "mailto:")):
        return url, True
    if url.startswith("#"):
        return url, False
    if url.endswith("LICENSE"):
        return REPO_BLOB + "LICENSE", True
    if url.endswith(".md") or ".md#" in url:
        if ".md#" in url:
            path, frag = url.split(".md#", 1)
            target = path + ".md"
            key = stem_map.get(os.path.normpath(os.path.join("ROOT", target)))
            return "#%s--%s" % (key or stem(target), frag), False
        key = stem_map.get(os.path.normpath(os.path.join("ROOT", url)))
        return "#doc-%s" % (key or stem(url)), False
    return url, False


def inline(text, stem_map):
    out = html.escape(text, quote=False)
    out = out.replace("\\*", "\x00")  # 保留被转义的星号

    def link(m):
        label, url = m.group(1), m.group(2)
        href, external = rewrite_link(url, stem_map)
        attrs = ' target="_blank" rel="noopener"' if external else ""
        return '<a href="%s"%s>%s</a>' % (href, attrs, label)

    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out.replace("\x00", "*")


def convert(md, stem_map):
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if re.match(r"^---+$", stripped):
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            hid = "doc-%s" % stem_map["__current__"] if level == 1 else "%s--%s" % (
                stem_map["__current__"], anchor(text))
            out.append("<h%d id=\"%s\">%s</h%d>" % (level, hid, inline(text, stem_map), level))
            i += 1
            continue

        # 表格
        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = ["<table><thead><tr>"]
            t += ["<th>%s</th>" % inline(c, stem_map) for c in header]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join("<td>%s</td>" % inline(c, stem_map) for c in r) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue

        # 引用
        if stripped.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(buf), stem_map))
            continue

        # 列表（有序 / 无序 / 复选框）
        m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m or stripped.startswith("- "):
            ordered = bool(m)
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                mo = re.match(r"^(\d+)\.\s+(.*)$", cur)
                if ordered and mo:
                    items.append(("num", mo.group(2)))
                elif not ordered and cur.startswith("- "):
                    items.append(("dot", cur[2:]))
                elif ordered and not mo:
                    break
                elif not ordered and not cur.startswith("- "):
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            cls = ' class="check"' if any(t == "dot" and b.startswith("[ ]") for t, b in items) else ""
            out.append("<%s%s>" % (tag, cls))
            for _, body in items:
                checkbox = ""
                if body.startswith("[ ]"):
                    checkbox, body = '<span class="box"></span>', body[3:].strip()
                elif body.startswith("[x]"):
                    checkbox, body = '<span class="box on"></span>', body[3:].strip()
                out.append("<li>%s%s</li>" % (checkbox, inline(body, stem_map)))
            out.append("</%s>" % tag)
            continue

        # 段落
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#{1,4}\s|[-*]\s|\d+\.\s|>|\|)", lines[i].strip()
        ) and not re.match(r"^---+$", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf), stem_map))

    return "\n".join(out)


CSS = """
:root{--fg:#1a1a1a;--muted:#6b6b6b;--line:#e3e3e3;--accent:#b4232a;--bg:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-size:17px;line-height:1.8;
 font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
 -webkit-text-size-adjust:100%}
.wrap{max-width:44rem;margin:0 auto;padding:24px 18px 80px}
nav{position:sticky;top:0;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);
 padding:10px 18px;font-size:14px;backdrop-filter:blur(6px);z-index:9}
nav a{color:var(--muted);text-decoration:none;margin-right:14px;white-space:nowrap}
nav a:hover{color:var(--accent)}
nav .inner{max-width:44rem;margin:0 auto;overflow-x:auto}
section{padding-top:8px}
h1{font-size:26px;line-height:1.4;margin:40px 0 18px;padding-bottom:10px;border-bottom:2px solid var(--fg)}
h2{font-size:21px;margin:34px 0 12px}
h3{font-size:18px;margin:26px 0 10px}
h4{font-size:17px;margin:22px 0 8px}
p{margin:12px 0}
ul,ol{margin:12px 0;padding-left:22px}
li{margin:7px 0}
ul.check{list-style:none;padding-left:2px}
ul.check li{position:relative;padding-left:26px}
.box{position:absolute;left:0;top:.55em;width:14px;height:14px;border:1.5px solid #999;border-radius:3px}
.box.on{background:var(--accent);border-color:var(--accent)}
strong{font-weight:600}
a{color:var(--accent)}
hr{border:0;border-top:1px solid var(--line);margin:34px 0}
blockquote{margin:16px 0;padding:10px 16px;border-left:3px solid var(--line);color:var(--muted)}
code{background:#f4f4f4;padding:1px 5px;border-radius:4px;font-size:.92em}
table{border-collapse:collapse;width:100%;margin:16px 0;font-size:15px}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left}
th{background:#fafafa;font-weight:600}
.top{font-size:13px;color:var(--muted);margin:0 0 4px}
@media print{
 nav{display:none}
 .wrap{max-width:none;padding:0}
 body{font-size:11.5pt;line-height:1.7}
 section{page-break-before:always}
 section:first-of-type{page-break-before:avoid}
 h1{page-break-after:avoid}
 table,blockquote{page-break-inside:avoid}
 a{color:inherit;text-decoration:none}
}
"""


def render():
    stem_map = {}
    for p in DOCS:
        stem_map[os.path.normpath(os.path.join(ROOT, p))] = stem(p)

    nav, body = [], []
    for p in DOCS:
        full = os.path.join(ROOT, p)
        with open(full, encoding="utf-8") as f:
            md = f.read()
        key = stem(p)
        title = next((l.lstrip("# ").strip() for l in md.split("\n") if l.startswith("# ")), key)
        nav.append('<a href="#doc-%s">%s</a>' % (key, html.escape(title)))
        stem_map["__current__"] = key
        body.append('<section>\n%s\n</section>' % convert(md, stem_map))

    out = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>中国公民防开户（开盒）指南</title>
<meta name="description" content="写给普通人看的隐私防护手册：认识开盒、查自己漏在哪、把口子堵上、被开盒之后怎么办。">
<style>%s</style>
</head>
<body>
<nav><div class="inner">%s</div></nav>
<div class="wrap">
<p class="top">中国公民防开户（开盒）指南 · 只针对中国大陆居民 · CC BY-NC-SA 4.0</p>
%s
</div>
</body>
</html>
""" % (CSS, "".join(nav), "\n".join(body))

    return out


def main():
    out = render()
    dst = os.path.join(ROOT, "index.html")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(out)
    print("已生成 %s（%.1f KB）" % (dst, os.path.getsize(dst) / 1024))


if __name__ == "__main__":
    main()
