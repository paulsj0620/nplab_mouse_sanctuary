#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
LAB_APP_DIR="$(pwd)"
LAB_AGENT_DIR="$HOME/Library/LaunchAgents"
LAB_USER_ID="$(id -u)"
if launchctl print "gui/$LAB_USER_ID/com.mouselab.server" >/dev/null 2>&1; then
  echo '서버 서비스가 이미 설치되어 있습니다. 운영 가이드의 업데이트 절차를 확인하세요.'
  exit 1
fi
.venv/bin/python3 -m scripts.deployment.macmini prepare --require-setup
mkdir -p "$LAB_AGENT_DIR"
install -m 600 "$LAB_APP_DIR/deploy/generated/com.mouselab.server.plist" "$LAB_AGENT_DIR/com.mouselab.server.plist"
install -m 600 "$LAB_APP_DIR/deploy/generated/com.mouselab.backup.plist" "$LAB_AGENT_DIR/com.mouselab.backup.plist"
launchctl bootstrap "gui/$LAB_USER_ID" "$LAB_AGENT_DIR/com.mouselab.server.plist"
launchctl bootstrap "gui/$LAB_USER_ID" "$LAB_AGENT_DIR/com.mouselab.backup.plist"
install -m 600 "$LAB_APP_DIR/deploy/generated/com.mouselab.workday-awake.plist" "$LAB_AGENT_DIR/com.mouselab.workday-awake.plist"
launchctl bootstrap "gui/$LAB_USER_ID" "$LAB_AGENT_DIR/com.mouselab.workday-awake.plist"
echo '로그인 후 자동 실행과 매일 03:00 백업을 등록했습니다. 외부 접속은 아직 활성화하지 않았습니다.'
