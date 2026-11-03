#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python3 -m scripts.deployment.macmini check-initialized --port 8767
LAB_TAILSCALE="$(command -v tailscale || true)"
if [ -z "$LAB_TAILSCALE" ] && [ -x /Applications/Tailscale.app/Contents/MacOS/Tailscale ]; then
  LAB_TAILSCALE=/Applications/Tailscale.app/Contents/MacOS/Tailscale
fi
if [ -z "$LAB_TAILSCALE" ]; then
  echo '먼저 Tailscale 공식 앱을 설치하고 연구실 네트워크 계정으로 로그인하세요.'
  exit 1
fi
"$LAB_TAILSCALE" status
"$LAB_TAILSCALE" serve --bg --https=443 http://127.0.0.1:8767
"$LAB_TAILSCALE" serve status
