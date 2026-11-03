
## 2026-11-03 현재 운영: 내부망 전용

사용자가 외부 접속 대신 내부망 전용 운영을 선택했다. Tailscale/Cloudflare는 설치하거나 활성화하지 않았다.

- 접속 주소: http://10.92.73.22:8000/
- 유선 en0 주소에만 바인딩, 허용 클라이언트 대역 10.92.73.0/24. 다른 대역은 HTTP 403. X-Forwarded-For 등을 신뢰하지 않고 실제 소켓 발신 IP로 판단한다.
- Wi-Fi en1(192.168.83.99)은 허용하지 않는다. 다른 연구실 PC의 대역이 다르면 그 범위를 확인한 뒤 명시적으로 추가해야 한다. 모든 학교 네트워크를 자동 허용하지 않는다.
- 현재 HTTP 연결이며 전송 암호화는 없다. HTTPS가 필요하면 내부 인증서 배포를 별도 구성한다.
- 최종 폴더 .venv에 requirements/requirements.txt를 설치했다. com.mouselab.server/backup LaunchAgent를 등록했다. 서버는 caffeinate -is로 시스템 잠자기를 방지하며 로그인 후 자동 실행된다. 재부팅 후 macOS 사용자 로그인이 필요하고 로그아웃/종료 중에는 사용할 수 없다.
- 매일 03:00에 backups/로 SQLite 일관된 백업을 생성한다. SMB로의 복사는 아직 구성하지 않았다.
- 실행 DB는 이 폴더 data/lab.sqlite이며 이전 8766 작업 DB와 혼동하지 않는다. 사용자에게 위 내부망 주소를 안내한다.
- 배포 스크립트: -m scripts.deployment.setup_lan --host 10.92.73.22 --network 10.92.73.0/24 --install. 이미 등록된 서비스에는 실행을 거부한다. 중지 시 deploy/stop-services.command 사용. 기존 install-services.command는 이전 VPN용이므로 현재 LAN 운영에 사용하지 않는다.
- IP 주소가 바뀌면 서비스 바인딩과 접속 주소를 함께 갱신해야 한다. DHCP 예약 여부는 확인하지 않았다.
- 확인: 유선 소스 IP에서 /api/me 및 최신 Mouse Sanctuary 페이지 HTTP 200, Wi-Fi 소스 IP에서 403, 관리자 초기화 완료, 서버 running 및 백업 예약 등록 확인. 다른 물리 PC에서의 접속은 아직 확인하지 않았다.

---
# Mouse Sanctuary — 서버 저장 버전

데스크톱 중심의 흰색 연구실 앱입니다. 최초 183마리 명단은 포함되어 있지만 실제 측정값은 들어 있지 않습니다. 계정, 업로드 원본, 측정값, 정정 이력, 전역 제외 상태, 공유 그래프 서식은 서버 SQLite 데이터베이스에 저장합니다. 브라우저 localStorage를 사용하지 않습니다.

## 이 컴퓨터에서 실행

macOS에서는 `start.command`를 실행한 다음 브라우저에서 http://127.0.0.1:8000 을 엽니다. 이 컴퓨터의 Codex Python이 있으면 자동 사용합니다. 처음 표시되는 화면에서 관리자 계정을 직접 만드세요. 테스트 계정이나 테스트 측정값은 배포 패키지에 없습니다.

일반적인 Python 3.11 이상 환경에서는 다음과 같이 실행합니다.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/requirements.txt
.venv/bin/python -m scripts.app.server
```

Windows는 `.venv\Scripts\python.exe`를 사용합니다. Excel 입력에 openpyxl이 필요합니다. CSV는 Python 표준 라이브러리로 처리합니다.

## 연구실에서 여러 사용자와 사용

연구실 서버 한 대에서 앱을 실행하고 모든 사용자가 그 서버 주소로 접속합니다. 각자 자신의 컴퓨터에서 별도 서버를 실행하면 DB도 서로 달라집니다.

1. 먼저 서버 컴퓨터의 localhost에서 관리자 계정을 생성합니다.
2. 관리자 화면에서 연구자 계정을 추가합니다. 사용자별 로그인으로 수정 작성자를 식별합니다.
3. 내부 네트워크용 테스트는 `python -m scripts.app.server --host 0.0.0.0 --port 8000`으로 실행한 뒤 연구실의 승인된 네트워크 범위에서 접속합니다. 이 명령은 모든 인터페이스에 열리므로 네트워크 노출 범위는 서버 담당자가 정합니다.
4. 실제 공동 운영에서는 HTTPS reverse proxy 뒤에 두고 `--secure-cookie`를 사용하세요. 기본 서버는 내부 파일럿을 위한 표준 라이브러리 HTTP 서버이며 인터넷 공개 운영용 서버가 아닙니다. SSO, 비밀번호 재설정/사용자 비활성화, 연구별 권한 분리는 아직 없습니다.
5. DB 파일은 서버의 로컬 디스크에 둡니다. 네트워크 공유 폴더에 DB 파일을 두고 각 PC가 직접 여는 방식은 사용하지 않습니다.

서버는 요청을 여러 스레드로 받고 쓰기 트랜잭션은 SQLite가 순서대로 처리합니다. 다른 ID의 업로드는 모두 저장됩니다. 같은 값의 동시 수정은 버전을 비교하여 뒤늦은 요청을 409 충돌로 거부합니다. 화면은 15초마다 최신 변경을 확인하며, 수정 창이나 Import 작업 중에는 입력을 보존합니다. 이 기간에 다른 사용자가 변경했더라도 저장 시 버전 검사가 최종적으로 충돌을 막습니다.

## Import

- FACS XLS, XLSX 또는 UTF-8 CSV, 최대 10MB. 한 번에 최대 10,000행·200열·100,000개 관측.
- 첫 행은 중복 없는 컬럼명. 병합 헤더 및 Excel 수식은 값 기반 표로 정리한 사본을 입력합니다.
- 업로드 → 시트 선택 → Mouse ID/그룹/실험/주차/식이/반복 컬럼 연결 → 가져올 측정 컬럼 체크 → 이름·단위·시점·organ/gate 확인 → 사유 입력 → 저장.
- 신규 mouse ID는 그룹이 있으면 명단에 추가됩니다. 총 개체 수를 183으로 제한하지 않습니다. 이 앱은 단일 연구실 연구를 위한 공간이므로 ID는 전체 명단에서 유일해야 합니다.
- 이미 있는 ID는 기존 mouse에 연결합니다. 기존 그룹과 다르면 가져오기를 막고 명단 수정에서 정정하도록 합니다.
- 측정 이름은 자유 입력입니다. Body weight, OGTT, ITT, Weight of tissues, Total Cholesterol, LDL-C, HDL-C, Triglycerides, Fasting Glucose, H&E, PSR, FACS 외의 항목도 가능합니다.
- 단위 자동 제안은 편의 기능입니다. 실제 측정 단위를 반드시 확인하세요. mmol/L와 mg/dL을 자동 변환하지 않습니다.
- `OGTT_0`, `OGTT_15`, `OGTT_30`은 같은 이름 OGTT와 각 숫자 시점으로 자동 제안합니다. long-format의 시간 컬럼을 직접 지정할 수도 있습니다. 기본 시간축 제목은 Time (min)이며 다른 기준이면 바꿉니다.
- FACS는 gate가 있으면 organ, 상위 gate, 분모를 함께 지정합니다. `%`, `events`, `cells/organ`, `cells/mL` 등은 서로 다른 측정 정의로 저장합니다. Absolute Count를 퍼센트만으로 자동 계산하지 않습니다.
- 빈 칸은 값 NULL + 결측 사유로 저장합니다. 0은 실제 값입니다. `NA`, `ND` 같은 문자열은 숫자로 해석하지 않고 가져오기를 막습니다.
- 동일 mouse + 측정 정의 + 시점 + 반복의 중복이 있으면 전체 Import를 취소합니다. 일부 행만 저장되는 일은 없습니다. 기존 값은 데이터 화면에서 수정합니다.
- 원본 파일 바이트, SHA-256, 매핑, 원본 행 번호와 작성자를 보존합니다. 단순 헤더 기반 단위 변경이나 organ 이름 통일을 자동으로 추측하지 않습니다.

## 그래프와 공유 서식

측정 컬럼을 선택하면 막대+개체별 점, 점+평균, 시간별 곡선 중에서 선택할 수 있습니다. 평균 ± SD / 평균 ± SEM / 평균만을 전환할 수 있습니다. SD는 표본 SD(n−1), SEM은 SD/√n입니다. n=1이면 오차 막대가 없고, n=0이면 평균도 없습니다.

그룹 색·기호·순서·채움/윤곽, 축 제목·범위, 글자 크기, 그룹명 각도를 조절할 수 있습니다. 서식을 이름으로 서버에 저장하면 다른 사용자도 선택할 수 있습니다. 현재 서식은 데이터 선택 조건도 함께 저장합니다.

첨부 GraphPad 이미지의 검정/분홍/청록/하늘/보라 색상, 서로 다른 기호, 막대와 개체 점, 검정 축을 재현한 템플릿입니다. Prism 파일(.pzfx/.prism) 호환이나 원본 템플릿과 픽셀 단위 동일성을 보장하는 기능은 아닙니다. SVG는 벡터로, PNG는 2배 해상도로 내보냅니다. PNG에 특정 인쇄 DPI 메타데이터를 설정하지는 않습니다.

p-value는 아래 ANOVA/Tukey 기능으로 자동 계산합니다. 수동 입력과 기준 그룹 선택은 제공하지 않습니다. AUC, baseline 정규화, 반복측정 통계도 아직 없습니다. 서로 다른 기술 반복은 합치지 않고 반복 선택으로 구분합니다.

`예시로 서식 보기`의 수치는 합성값이며 DB에 저장되지 않습니다. 원본 그림의 p-value를 예시에 복사하지 않았습니다.

## 수정과 제외

- 데이터 화면에서 측정값·결측 사유, mouse의 그룹·실험·주차·식이·메모·제외 상태를 수정할 수 있습니다.
- mouse ID, 관측의 측정 정의·시점·반복은 생성 후 고정입니다. 잘못 연결된 정의를 재매핑하는 관리 기능은 다음 단계입니다.
- 변경 사유가 필수이며 서버가 인증된 작성자·시간·변경 전후 값을 기록합니다. 입력 원본 파일은 바뀌지 않습니다.
- 차트 점을 클릭하면 해당 mouse의 전역 제외/복원 상태를 수정할 수 있습니다. 모든 지표·organ·gate와 시점에 같은 제외 상태를 적용합니다.
- 현재는 한 연구 공간의 공통 제외 상태입니다. 개인별 분석 세트는 아직 없습니다.
- 이력은 DB 트리거로 UPDATE/DELETE를 막습니다. DB 관리자까지 막는 암호학적 위변조 방지 저장소는 아닙니다.

## 백업과 내보내기

데이터 화면에서 전체 JSON(같은 DB 스냅샷의 데이터+이력), 측정값 CSV, 업로드 원본을 내려받습니다. 그래프의 데이터 CSV는 현재 필터·제외를 적용합니다. JSON은 검토용으로, 계정과 원본 파일까지 복구하려면 DB 백업을 사용하세요.

```sh
python -m scripts.maintenance.backup backups/lab-2026-11-02.sqlite
```

백업은 SQLite backup API로 실행하며 기존 파일은 덮어쓰지 않습니다. 복원은 서버를 종료한 뒤 백업 DB를 별도 경로로 복사하고 `python -m scripts.app.server --db 복사한파일.sqlite`로 실행합니다. 계정·세션도 포함되므로 백업 접근권한을 제한합니다. 앱 소스와 `archives/seed/` 폴더도 함께 보관합니다.

## 검증

```sh
python -m unittest -v scripts.tests.test_service
node --test scripts/tests/js/test_chart.cjs
```

기본 서버 테스트 8개: 신규 개체/동적 항목/0·결측/재시작 후 유지, 원자적 롤백, 동시 수정 충돌, 두 사용자 동시 업로드·소유권, 전역 제외/복원·원본/이력 불변, 인증/역할/공유 서식 충돌, XLSX 행 추적, 유효하지 않은 숫자 차단.

차트 테스트 6개: SD/SEM, 전역 제외, 반복 혼합 거부, SVG 구조, 잘못된 축 범위·비교선 차단, OGTT 시점과 결측. 별도 로컬 HTTP 검증에서 로그인, CSRF, 권한, 사용자 간 공유, stale-write 409, 일관된 JSON 내보내기를 확인했습니다. 브라우저에서는 CSV 선택/매핑/저장, 수정 버전 증가, OGTT SEM 표시를 확인했습니다.

공식 서식 참고: https://www.graphpad.com/guides/prism/latest/user-guide/using_format_graph_one_way.htm

## FACS XLS Import 업데이트

구형 Excel `.xls`의 `gate 경로 | 통계량` 형식을 직접 읽습니다. xlrd 2.0.2와 라이선스를 vendor/에 포함했습니다. 일반적인 XLS 표는 XLSX/CSV로 변환하세요.

- 빈 첫 헤더를 Sample로 읽고, 염색 대조군/미분류 파일명과 Mean/SD 행을 분리합니다. 인식되지 않은 샘플은 자동 포함하지 않으므로 제외 목록도 확인하세요.
- 샘플명에서 organ 및 mouse ID 후보를 제시합니다. `Liver_102_001.fcs`의 001은 acquisition 접미사로 보존하며 ID 후보는 102입니다. 사용자가 행별 ID를 수정하고 확인해야 저장됩니다.
- 한 시트의 반복 헤더를 별도 표로 분리합니다. 계산 표에는 통계량 이름과 단위가 필요합니다. 선택한 표의 원래 시트/행 번호, 파일명, 변환 정보 및 매핑을 이력에 보존합니다.
- 사용자가 지정한 제공 Count 파일은 SHA-256이 일치할 때만 아래 표(헤더 93행, 데이터 94–179행)를 기본 선택합니다. Absolute Count, cells/µL를 제안하고 비어 있는 bead 열은 체크하지 않습니다. 86마리 × 26열 = 2,236개 값입니다. 이 프로필은 다른 파일에 임의 적용하지 않습니다.
- Freq는 실제 Excel 백분율 서식의 숫자만 ×100해 %로 읽습니다. `n/a`는 원본 결측 사유와 함께 NULL로 저장합니다. MFI라는 파일명만 보고 통계량을 추정하지 않고 Geometric Mean 헤더와 채널을 보존합니다.
- 다른 prefix를 가진 gate 경로는 자동 병합하지 않습니다. 한 번에 하나의 organ을 선택해 가져옵니다. 원본 XLS 수식의 재계산은 하지 않고 저장된 셀 값을 읽습니다.
- FACS 추가 테스트 5개와 제공 파일을 이용한 폐기용 DB 검증을 완료했습니다. 실제 사용자 DB에는 FACS 측정값을 미리 넣지 않았습니다. 브라우저 미리보기에서 대상 표·ID를 확인하고 사유를 입력해 저장하세요.

Gate 이름은 선택 목록, 데이터 화면, 그래프 제목/설명에서 `/`로 구분된 마지막 이름만 표시합니다. 전체 경로는 원본 정의·JSON/데이터 CSV에 보존하며 선택 목록과 데이터 항목에 마우스를 올리면 확인할 수 있습니다. 같은 말단 이름이라도 측정 ID와 전체 경로를 기준으로 구분합니다.

## 오른쪽 데이터·샘플 선택 패널

그래프 오른쪽에서 측정 항목과 샘플을 선택합니다. 실험·주차·시점 필터는 펼쳐서 사용합니다. 현재 항목의 샘플을 ID/그룹으로 검색하고, 개별 체크 또는 표시된 샘플의 일괄 포함·제외를 지정한 뒤 사유와 함께 선택 저장을 누릅니다. 저장 전 변경 취소가 가능합니다.

저장된 포함·제외는 연구 공간의 모든 측정 항목·gate·시점에 공통 적용됩니다. 미측정 mouse 표시를 켜도 측정값이 새로 생기지는 않습니다. 여러 샘플의 변경은 한 트랜잭션으로 저장하며, 어느 하나라도 버전 충돌이 나면 전체 변경을 취소하고 최신 상태를 불러옵니다. 사용자·시각·사유·전후 상태가 mouse별로 기록됩니다.

검증: 서버 15개·차트/샘플 목록 7개 테스트 통과. 실제 브라우저에서 QA 샘플의 검색, 제외 저장, 그래프 점 제거, 포함 복원 및 오른쪽 배치를 확인했습니다.

## 다중 그래프와 Exp → Diet → Mouse 선택

- 기본 4개, 개수 선택에서 4–8개 그래프를 2열로 표시합니다. 각 카드에서 측정 항목을 바꾸거나 설정 버튼을 눌러 오른쪽에서 해당 그래프의 SD/SEM·축·시점·반복·그래프 서식을 조절합니다. 그룹 순서·색상·기호·채움은 공통 패널에서 함께 조절합니다. 그래프 수를 줄였다가 늘려도 숨겨진 카드의 설정을 유지합니다.
- 오른쪽 샘플은 원본 명단의 experiment → diet → mouse_id로 묶습니다. Diet가 비어 있으면 기존 그룹명을 사용하며, Exp가 다르면 같은 Diet도 별개로 표시합니다. Exp/Diet 체크는 현재 표시된 하위 mouse를 선택합니다. 일부만 포함된 계층은 부분 선택 상태입니다.
- 샘플 목록은 열린 그래프의 관측을 합집합으로 표시합니다. 특정 그래프에서 미측정인 mouse도 다른 그래프에 값이 있으면 목록에 포함됩니다. 각 그래프는 자기 항목에서 측정된 값만 사용하며, 결측을 0으로 채우지 않습니다.
- 체크 변경은 모든 그래프에 즉시 미리보기로 반영됩니다. 선택 저장을 누르면 변경 사유·사용자·시각·전후 상태와 함께 전역 제외를 확정합니다. 변경 취소는 저장된 상태로 되돌립니다.
- 전체 SVG/PNG는 A–H 패널을 한 장에 내보냅니다. PNG는 합성 SVG의 2배 해상도입니다. 전체 그래프 CSV에는 패널 번호와 원본 gate 경로가 들어갑니다. 미저장 샘플 선택이 있으면 SVG 메타데이터에 변경 목록, CSV에 selection_preview 여부를 기록합니다.
- 공유 서식에는 그래프 개수·개별 항목·서식·선택한 설정 카드가 저장됩니다. 샘플의 전역 포함·제외는 그래프 서식과 별도로 서버에서 관리됩니다. 이전 단일 그래프 서식도 선택한 카드에 불러올 수 있습니다.
- 검증: 서버 16개·차트/계층/다중 그래프 9개 테스트 통과. 브라우저에서 4/8개 렌더링, 8개 동시 제외 미리보기와 취소, Exp/Diet 일괄 선택·부분 선택, 개별 SD/SEM 유지, 공유 서식 복원, OGTT 혼합, SVG 8개 패널 및 PNG 내보내기를 확인했습니다.

## 숫자 p-value와 공통 그룹 색상

기본 모드는 one-way ANOVA(등분산 가정) + Tukey 다중비교입니다. 표본 수가 같으면 Tukey HSD, 다르면 Tukey–Kramer로 계산합니다. 각 그래프의 표시 그룹 전체를 하나의 비교 집합으로 보정하며, 여러 그래프/gate 사이에 추가 다중검정 보정은 하지 않습니다. 독립성·정규성·등분산 가정을 사용합니다. 시간 곡선의 반복측정 분석은 지원하지 않아 단일 시점의 막대/점 그래프에서 사용합니다.

- 서버에 저장된 측정값과 현재 선택·그룹·시점·반복을 기준으로 계산합니다. 제외된 mouse와 결측은 빼며, 0은 실제 값으로 유지합니다. 한 mouse의 반복/시점 혼합, 비교 그룹 2개 미만, 그룹별 n<2, 그룹 내 분산이 모두 0이면 유효한 p-value를 표시하지 않습니다.
- 그래프의 p-value 버튼에서 모든 쌍 / 0.1 미만 / 0.05 미만 중 선택합니다. 새 그래프의 기본 보기는 0.05 미만입니다. 반올림 전 Tukey 보정 p-value에 엄격한 미만(<) 기준을 적용하며 비교선과 표를 함께 필터링합니다. Tukey의 전체 쌍 보정 범위는 유지하고 통계 CSV에는 전체 결과를 포함합니다.
- 별표 대신 숫자를 표시합니다. 작은 수는 지수 표기를 쓰고, 계산값이 수치 정밀도 한계로 0이 되면 p ≈ 0으로 표시합니다. 수동 p-value 입력은 제거했습니다. 이전 서식의 수동 비교선도 표시하지 않습니다.
- 샘플 선택 변경 시 이전 p-value를 지우고 새 선택으로 계산합니다. 데이터 revision이 맞지 않으면 결과를 거부합니다. SVG 메타데이터에 분석 방법·라이브러리 버전·전체 그룹별 mouse ID·보정 p·원본 데이터 해시·revision·미저장 선택을 포함합니다. 통계 결과 CSV는 반올림 전 p-value를 내보냅니다.
- 그래프 상단의 공통 그룹 설정에서 색상을 바꾸면 같은 Diet의 모든 그래프(숨겨진 카드 포함)에 함께 적용됩니다. 초기 색상은 Chow 검정, Western 분홍, TRF 6:18 청록, TRF 10:14 하늘, ADF 진보라, Reverse 밝은 보라입니다. 그룹의 표시 순서/주차가 달라도 같은 Diet 색상을 사용합니다. 공통 팔레트도 공유 서식에 저장합니다. 공통 설정이 없는 이전 서식은 저장된 색상·기호를 바탕으로 공통 설정으로 변환하며 '그림의 초기 색상'으로 전체 복원할 수 있습니다.
- 첫 실행에 과학 계산 패키지가 없으면 start.command가 앱 폴더의 .venv에 requirements/requirements.txt를 설치합니다(인터넷 필요). 기존 Python 환경을 수정하지 않습니다. 수동 설치는 위 가상환경 설치 절차를 사용합니다.

통계 엔진은 SciPy 1.16.3입니다. 구현 기준: [one-way ANOVA](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.f_oneway.html), [Tukey HSD/Kramer](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.tukey_hsd.html). 해석 가능한 분석을 위해 실험 설계에 맞는 그룹과 시점으로 선택하세요.

검증: Python 테스트 22개, 차트 테스트 16개 통과. 알려진 ANOVA F=27, p=.001 및 공식 SciPy Tukey 예제의 수치와 일치했습니다. 브라우저에서 8개 그래프의 숫자 p 표시, 전체 색상 동시 변경, 샘플 제외·취소 후 재계산, 전체 15개 쌍 표시를 검증했습니다. 추가로 보정 p=0.05 및 0.1의 경계값 제외와 필터 변경 시 원본 통계 결과 유지를 확인했습니다.

## 공통 그룹 설정, 접힌 트리, N 상세, 맥미니 운영

- 그룹 순서·표시·색상·점 기호·막대 채움은 하나의 공통 패널로 관리합니다. 같은 Diet의 모든 그래프와 숨겨진 카드에 적용됩니다. 숫자 순서 입력은 제거했고, ≡ 핸들을 끌어 원하는 위치로 이동합니다. 방향키로도 이동할 수 있습니다. 화면에는 1, 2, 3… 순서만 표시합니다.
- Exp/Diet 트리는 초기에는 접혀 있습니다. 검색하면 해당 경로를 펼쳐 찾을 수 있고 검색을 지우면 기존 펼침 상태로 돌아갑니다.
- 그래프의 N 상세에서 측정값 있음, 결측(NULL), 미측정(해당 관측 행 없음), 전역 제외를 서로 겹치지 않게 구분하고 mouse ID를 표시합니다. 표시 그룹/필터 기준 대상 수는 이 네 범주의 합입니다. 곡선의 개체 수는 같은 mouse를 여러 시점에 중복 계산하지 않습니다.
- 제공된 Absolute Count는 86마리, Frequency는 88마리(44·45 추가)입니다. MFI 전체에는 n/a 6개가 있으며 해당 gate의 N에만 영향을 줍니다. 그래프 N을 억지로 맞추거나 결측을 0으로 채우지 않습니다.
- 맥미니 운영 안내는 deploy/맥미니-운영가이드.html입니다. -m scripts.deployment.macmini는 자동 실행/일일 백업의 launchd 설정을 생성하며, 생성 자체는 서비스를 등록하거나 외부 접속을 열지 않습니다. install-services.command와 enable-private-access.command는 운영자가 준비한 맥미니에서 실행합니다. 비공개 VPN 연결에는 Tailscale 설치·로그인과 연구자 접속 권한 설정이 필요합니다.

## 윤곽 기본값, 음수 축과 단위

- 새 그래프의 모든 그룹은 윤곽 막대로 시작합니다. 채움으로 바꾸면 막대 면의 불투명도는 35%(투명도 65%)이며 윤곽선·개체 점·오차 막대는 선명하게 유지합니다. 명시적으로 저장한 이전 서식의 채움 선택은 복원됩니다.
- 이번 제공 파일에서 가져온 Absolute Count 2,236개와 Frequency 2,288개 관측값에는 음수가 없습니다. Y축은 기본 0부터 표시합니다. 평균−SD/SEM이 하한보다 작으면 아래쪽 오차 막대만 그래프 영역에서 잘라 표시하고 화면과 SVG에 이를 명시합니다. 계산된 SD/SEM·평균·원본 측정값과 통계에는 변화가 없습니다. 실제 음수 관측값은 조용히 숨기지 않고 축 범위를 조절하도록 안내합니다. SVG 메타데이터에 축 범위·생략된 하단 오차 막대 개수·실제 음수 개수·음수 오차범위 여부를 포함합니다.
- a.u.는 arbitrary units(임의 단위)이며 MFI의 상대 형광강도 표기입니다. cells/µL 또는 %가 아닙니다. 제공 MFI 파일의 통계량은 Geometric Mean이며 원본 통계량 이름을 유지합니다. [FlowJo 통계 설명](https://docs.flowjo.com/flowjo/workspaces-and-samples/ws-statistics/ws-statdefinitions/).

- MFI 그래프의 기본 제목은 업로드 시 보존한 원본 열 제목(`gate 경로 | Geometric Mean (…)`)을 그대로 사용합니다. 긴 제목은 줄바꿈하며 원본 문자열을 SVG 제목과 메타데이터에 유지합니다. 기존 원본 바이트·측정 정의·metric ID는 수정하지 않습니다.

- 새 그래프의 오차 막대 기본값은 평균 ± SEM입니다. SD/SEM 선택은 그래프별로 변경하고 공유 서식에 저장할 수 있습니다.

## Git checkout and local configuration

This repository contains application code, tests and documentation. Research originals, SQLite databases, the real `archives/seed/` roster, backups, logs, virtual environments and machine-specific FCS configuration are intentionally excluded. A Git commit is not a research-data backup.

For an existing installation, retain its local `data/`, `archives/seed/`, `config/fcs_access.json` and `config/fcs_paths.json`. For a new installation, provision an authorized `archives/seed/roster.json` separately before starting the server; this repository does not ship the research roster. Copy `config/fcs_access.example.json` to `config/fcs_access.json` and explicitly configure approved QA user IDs. Copy `config/fcs_paths.example.json` to `config/fcs_paths.json` and configure approved shared-folder mappings for that machine. Never commit actual account databases or research files.
