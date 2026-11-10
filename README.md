# Mouse Sanctuary

연구실의 마우스 실험 자료를 여러 사용자가 업로드·수정하고, 개체별 값과 그룹 비교 그래프를 만드는 데스크톱 중심 웹앱입니다. 계정, 측정값, 원본 업로드, 수정·제외 이력과 공유 그래프 서식은 SQLite에 저장합니다.

## 현재 운영과 작업 흐름

연구팀 운영 사이트는 [Mouse Sanctuary](https://nplab.alwaysdata.net/)이며, 이 Mac의 폴더는 개발·검증과 로컬 데이터 보관에 사용합니다. 운영 서버와 로컬 DB는 별개입니다. 이 설명은 2026-11-06 운영 기록을 기준으로 하며 이번 폴더 정리에서 원격 상태를 다시 확인하거나 배포하지 않았습니다.

1. **Home**에서 실험과 자료를 찾습니다.
2. **Import**에서 META Data 또는 FACS 요약 자료를 선택하고, ID·항목·단위·중복 검토를 거쳐 저장합니다.
3. **Data**에서 측정값과 결측 사유를 확인하고 수정합니다.
4. **Graph**에서 비교 표본과 항목을 골라 1–8개 그래프를 구성하고 그림·데이터·통계를 내보냅니다.
5. **Edit History**에서 변경 이력을 확인합니다. 사용자 관리는 관리자 권한을 따릅니다.

FlowJo 요약 XLS의 Count·Frequency·MFI는 서로 다른 측정 정의로 보존합니다. 원시 FCS/WSP를 다루는 실험적 FACS 기능은 기존 QA 계정으로 제한하며, 일반 사용자의 Graph 기능과 구분합니다.

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

**사용자 요청에 따라 이 웹앱의 실행 구조는 공통 연구 폴더 체계의 예외로 유지했습니다.** 이번 정리에서는 README와 AGENTS만 수정했습니다.

## 로컬 실행과 검증

macOS는 `start.command`, Windows는 `start-windows.cmd`를 사용합니다. 이미 실행 중인 로컬 서비스가 있다면 같은 포트로 중복 실행하지 않습니다. 현재 DB와 계정을 유지하며 초기화하지 않습니다. Windows 이전본은 독립 복사본이며 자동 동기화되지 않습니다.

프로젝트 루트에서 테스트를 실행할 수 있습니다.

```sh
.venv/bin/python -B -m unittest scripts.tests.test_accounts scripts.tests.test_import_review scripts.tests.test_login_history scripts.tests.test_statistical
node --test scripts/tests/js/test_chart.cjs scripts/tests/js/test_i18n.cjs
```

FCS 엔진 테스트는 별도 의존성이 필요하며 `scripts/tests/run.py`가 기본/FCS 환경을 나누어 실행합니다. 테스트·개발·운영 배포는 별개입니다. main 푸시는 배포를 유발할 수 있으므로 프로젝트 AGENTS의 배포 지침을 따릅니다.

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
