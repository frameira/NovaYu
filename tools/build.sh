#!/usr/bin/env bash
# 改完 Markdown 之后跑这个：重建网页版和 PDF，然后自检。
# 用法： bash tools/build.sh
set -euo pipefail
cd "$(dirname "$0")/.."

python3 tools/build.py

# 找 Chrome，找不到就跳过 PDF（网页版已经生成）
CHROME=""
for c in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "$(command -v google-chrome || true)" \
  "$(command -v google-chrome-stable || true)" \
  "$(command -v chromium || true)" \
  "$(command -v chromium-browser || true)"; do
  [ -n "$c" ] && [ -x "$c" ] && CHROME="$c" && break
done

if [ -n "$CHROME" ]; then
  "$CHROME" --headless=new --disable-gpu --no-sandbox --no-pdf-header-footer \
    --virtual-time-budget=8000 \
    --print-to-pdf="$PWD/防开盒指南.pdf" "file://$PWD/index.html" 2>/dev/null || true
  if [ -f "防开盒指南.pdf" ]; then
    echo "已生成 防开盒指南.pdf（$(du -h 防开盒指南.pdf | cut -f1)）"
  fi
else
  echo "没找到 Chrome，跳过 PDF 生成（网页版已更新）"
fi

python3 tools/check.py
