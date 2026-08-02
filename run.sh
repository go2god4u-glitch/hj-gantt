#!/usr/bin/env bash
# hj_gantt 실행 — 처음이면 가상환경까지 알아서 만든다.
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "가상환경을 만듭니다..."
  python3 -m venv venv
  ./venv/bin/pip install --quiet --upgrade pip
  ./venv/bin/pip install --quiet -r requirements.txt
fi

if ! ./venv/bin/python -c "import flask, openpyxl" 2>/dev/null; then
  ./venv/bin/pip install --quiet -r requirements.txt
fi

echo ""
echo "  hj_gantt  →  http://127.0.0.1:5001"
echo "  (종료: Ctrl+C)"
echo ""
exec ./venv/bin/python app.py
