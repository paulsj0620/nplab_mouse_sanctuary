# Mouse Sanctuary

연구실의 마우스 실험 자료를 여러 사용자가 업로드·수정하고, 개체별 값과 그룹 비교 그래프를 만드는 데스크톱 중심 웹앱입니다. 계정, 측정값, 원본 업로드, 수정·제외 이력과 공유 그래프 서식은 SQLite에 저장합니다.

## 현재 운영과 작업 흐름

연구팀 운영 사이트는 [Mouse Sanctuary](https://nplab.alwaysdata.net/)입니다. 맥미니에서는 개발·검증을 진행하며, 내부망 주소 또는 localhost로 접속하면 사이트 이름과 브라우저 제목에 **Dev.**가 표시됩니다. 운영 DB와 개발 DB는 별도로 관리합니다.

### 게스트 체험

로그인 화면의 **Try Graph as a guest** 버튼으로 가상 마우스 48마리의 FACS·주차별 체중·Liver HE·PSR 예시 그래프를 볼 수 있습니다. 비교 샘플 선택, 그래프 서식 변경, PNG·SVG·CSV 내보내기를 지원합니다. 예시 데이터 표시가 화면과 그림에 포함됩니다. 데이터 업로드와 저장에는 로그인이 필요하며, 게스트 체험에서는 p-value를 계산하지 않습니다.

### 로그인 후 사용 흐름

1. **Home**에서 실험과 자료를 찾습니다.
2. **Import**에서 META Data 또는 FACS 요약 자료를 선택하고, ID·항목·단위·중복 검토를 거쳐 저장합니다.
3. **Data**에서 측정값과 결측 사유를 확인하고 수정합니다.
4. **Graph**에서 비교 표본과 항목을 골라 1–8개 그래프를 구성하고 그림·데이터·통계를 내보냅니다.
5. **Edit History**에서 변경 이력을 확인합니다. 사용자 관리는 관리자 권한을 따릅니다.

FlowJo 요약 XLS의 Count·Frequency·MFI는 서로 다른 측정 정의로 보존합니다. 원시 FCS/WSP를 다루는 실험적 FACS 기능은 기존 QA 계정으로 제한하며, 일반 사용자의 Graph 기능과 구분합니다.

## Graph 사용

- **Number of graphs**에서 1–8개를 선택합니다. 오른쪽 **Graph 1–8** 탭으로 각 그래프의 설정을 바꿀 수 있습니다. Graph 화면에 들어가면 선택한 그래프의 설정이 펼쳐집니다.
- **Metric** 팝업은 대분류를 세로로 보여주며, 선택한 항목 오른쪽에 다음 단계가 나타납니다. 실제 측정값이 있는 항목을 표시합니다.
- **Comparison samples**는 이번 보드의 비교 대상을 고릅니다. **Global exclusions**는 마우스 제외·복원을 미리 보여주고, 사유와 함께 저장하면 모든 지표와 다른 사용자에게 적용되며 변경 이력에 기록됩니다.
- **Graph formatting**에서 그래프 종류, 축, 제목, 오차 막대 등을 조정합니다. 주차별 체중은 **Weekly weight trend**에서 Off·Mean·Median을 선택합니다. 기본값은 Off이며 Mean·Median은 각 그룹의 주차별 평균·중앙값을 연결합니다. SD·SEM 오차 막대는 평균 기준입니다.
- 오차 막대 기본값은 **SEM**, p-value 표시는 **0.05 미만**, Y축 하한은 **0**입니다. 단일 시점의 독립 그룹 비교에는 one-way ANOVA와 Tukey 다중비교를 사용합니다. 시계열 분석에는 이 검정을 적용하지 않습니다.
- **Shared presets**로 그래프 구성을 저장합니다. 오른쪽 메뉴 제목은 고정되고, 펼친 내용만 스크롤됩니다.
- PNG·SVG 내보내기는 비어 있는 그래프를 건너뛰며, 데이터와 통계는 CSV로 내보낼 수 있습니다.

| 분류 | 선택 경로 |
| --- | --- |
| Metabolic outcome | Weight-timeline / Weight-endpoint / ITT / OGTT → 측정 항목 |
| Histology | 장기 → HE (%) / PSR (%) |
| Flow cytometry | 장기 → 패널 → 마지막 gate 이름 → 측정 지표 |
| qPCR | 장기 → pathway → 유전자 |

FACS의 전체 gate 경로는 저장하며 화면에는 마지막 이름을 표시합니다. 같은 장기·패널에서 이름이 중복되면 상위 경로를 함께 표시합니다. qPCR pathway와 FACS panel은 Import에서 지정할 수 있습니다.

## 이 폴더의 역할

| 위치 | 내용 |
| --- | --- |
| `data/` | 로컬 DB·업로드·FCS 자산. 초기 빈 예제 폴더로 간주하지 않음 |
| `scripts/` | 서버·입력·통계·FCS·유지보수·배포·테스트 코드 |
| `static/` | 브라우저 HTML·CSS·JavaScript·이미지 |
| `config/` | 로컬 설정·접근 제한·실험 분류·입력 프로필 |
| `requirements/`, `vendor/` | 의존성 목록과 포함된 라이브러리 |
| `docs/` | 기능·데이터 구조·운영·이전 문서 |
| `archives/` | 초기 명단·스프레드시트·이전 앱 사본 |
| `backups/`, `logs/` | 기존 백업과 실행 기록 |
| `deploy/`, `start.command`, `start-windows.cmd` | 로컬 설치·시작 도구 |

이 웹앱은 위 프로젝트 구조를 기준으로 실행합니다.

## 로컬 실행과 검증

macOS는 `start.command`, Windows는 `start-windows.cmd`를 사용합니다. 이미 실행 중인 로컬 서비스가 있다면 같은 포트로 중복 실행하지 않습니다. 현재 DB와 계정을 유지하며 초기화하지 않습니다. Windows 이전본은 독립 복사본이며 자동 동기화되지 않습니다.

프로젝트 루트에서 테스트를 실행할 수 있습니다.

```sh
.venv/bin/python -B -m unittest scripts.tests.test_accounts scripts.tests.test_import_review scripts.tests.test_login_history scripts.tests.test_statistical
node --test scripts/tests/js/test_chart.cjs scripts/tests/js/test_i18n.cjs
```

FCS 엔진 테스트는 별도 의존성이 필요하며 `scripts/tests/run.py`가 기본/FCS 환경을 나누어 실행합니다. main 푸시는 아래 자동 배포를 실행하므로 배포할 변경을 검토한 후 푸시합니다.

## GitHub에서 운영 배포

`main`에 push하면 GitHub Actions의 **Test and deploy Mouse Sanctuary**가 테스트 후 코드 전용 배포와 사이트 재시작을 수행합니다. 배포 작업은 저장소 변수 `DEPLOY_ALWAYSDATA=true`와 production 환경의 SSH·API 설정을 사용합니다. [Actions 실행 기록](https://github.com/paulsj0620/nplab_mouse_sanctuary/actions)에서 test와 deploy 결과를 확인할 수 있습니다.

배포 스크립트는 허용 목록의 코드·화면 파일을 전송합니다. 운영 DB, 계정, 업로드 원본, archives는 서버에 보존합니다. 배포 후 공개 JavaScript와 로그인 상태 조회 응답을 검증합니다. 상세 설정과 수동 실행 방법은 [GitHub 운영 배포 문서](docs/github-deployment.md)에 있습니다.

두 개발 기기에서는 작업 시작 전 `git pull --ff-only origin main`으로 최신 코드를 받습니다. 개발 DB는 기기별로 관리합니다.

화면이 이전 모습으로 보이면 강력 새로고침으로 최신 화면 파일을 다시 받습니다. Chrome·Edge 기준 macOS는 **⌘⇧R**, Windows는 **Ctrl⇧R**입니다.

## 상세 안내

- [데이터 구조와 Graph 분류](docs/database-erd.md)
- [FCS 기능과 한계](docs/fcs-explorer.md)
- [백업·복원](docs/backup-and-restore.md)
- [Windows 이전](docs/windows-transfer.md)
- [GitHub 운영 배포](docs/github-deployment.md)
- [코드 구조](scripts/README.md)
- [AI 작업 지침과 상세 이력](AGENTS.md)

자동 백업은 사용자 요청으로 중지된 상태를 유지합니다. 기존 백업은 보존합니다. 이전 `archives/MouseSanctuary/`의 일부 FCS 파일은 현재 보존본에 대한 상대 링크이므로, 해당 폴더만 독립적인 백업·이동용 복사본으로 취급하지 않습니다.

## 문서 관리

이 프로젝트의 전체 안내는 이 README, AI 작업 지침은 [AGENTS.md](AGENTS.md)에 둡니다. 공통 최상위 안내 파일 없이 각 프로젝트 안에서 맥락을 확인할 수 있도록 관리합니다. 추가 설명·작업 기록은 이 프로젝트의 기존 문서 위치를 사용합니다.
