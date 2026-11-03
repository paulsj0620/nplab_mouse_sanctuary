#!/bin/sh
set -eu
LAB_USER_ID="$(id -u)"
launchctl bootout "gui/$LAB_USER_ID/com.mouselab.server" || true
launchctl bootout "gui/$LAB_USER_ID/com.mouselab.backup" || true
echo '앱과 백업 예약을 중지했습니다. Tailscale Serve도 종료하려면 운영 가이드의 명령을 사용하세요.'
