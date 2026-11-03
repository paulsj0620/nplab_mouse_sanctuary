#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python3 ]; then
  LAB_PYTHON=.venv/bin/python3
elif [ -x "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3" ]; then
  LAB_PYTHON="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
else
  LAB_PYTHON=python3
fi
if ! "$LAB_PYTHON" -c 'import openpyxl, numpy, scipy; assert tuple(map(int, scipy.__version__.split(".")[:2])) >= (1,16)' >/dev/null 2>&1; then
  echo '첫 실행: 통계 계산 패키지를 이 앱의 .venv 폴더에 설치합니다.'
  if [ ! -x .venv/bin/python3 ]; then
    "$LAB_PYTHON" -m venv .venv || exit 1
  fi
  LAB_PYTHON=.venv/bin/python3
  "$LAB_PYTHON" -m pip install -r requirements.txt || exit 1
fi
exec "$LAB_PYTHON" server.py
