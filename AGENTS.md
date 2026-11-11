# 재사용 디자인 규약 — 2026-11-11 확정

이 절은 다른 페이지를 만들거나 기존 UI를 수정할 때 따르는 **현재 디자인 기준**이다. 아래의 날짜별 기록은 변경 이력이다. 과거의 8px/14px 카드, 강한 Help blur, 페이지별 Help 배치 등은 최종 기준이 아니다. 뒤에 있는 「2026-11-09 폴더 정리」 제한은 당시 폴더 정리 작업에 한정되며, 사용자가 요청한 UI 개발을 금지하는 전역 규칙이 아니다.

## 1. 디자인 목적과 범위

- 흰색·중성 회색의 Liquid Glass에서 영감을 받은 인터페이스. Apple의 실제 수치/광학 효과를 복제했다는 의미는 아니다. 과장된 색·장식보다 데이터와 조작의 가독성을 우선한다.
- 유리 효과는 내비게이션, 도구 묶음, 설정 패널에 적용한다. 과학 그래프와 내보내는 그림은 불투명한 흰 배경을 유지한다. 축·점·오차막대·p-value에 블러를 적용하지 않는다.
- 기본 대상은 1920×1080 데스크톱. 브라우저 도구 모음 때문에 실제 viewport는 더 작을 수 있으므로 높이를 1080px로 고정하지 않는다. 1280px·1100px 폭에서도 확인한다. 현재 body min-width는 1100px이며 모바일 UI는 별도 범위다.
- 각 탭은 바로 작업 메뉴/카드부터 시작한다. 중복 페이지 제목, 소개 문장 때문에 작업 영역을 아래로 밀지 않는다. 접근성용 제목은 `sr-only`로 유지 가능하다. 필드 설명·오류·단위·출처 정보는 삭제하지 않는다.
- 현재 구현 위치: `static/style.css`(공통 외형), `static/index.html`(구조/스크립트), `static/app.js`(페이지/Graph/탭 전환), `static/tutorial.js`(Help), `static/strategies.js`(Gating).

## 2. 공통 수치와 색

| 요소 | 확정 기준 |
|---|---|
| 큰 카드·Data 표 외곽·Edit History 이벤트·Graph 카드 | `--radius-panel:24px` |
| 카드 내부 설정 블록·그룹별 색상 카드 | `--radius-inset:16px` |
| 일반 입력 필드·textarea | `--radius-field:14px` |
| 버튼·상단 단일행 입력/선택창·내비게이션 | `--radius-pill:999px` |
| 메뉴 묶음·일반 dialog | radius 28px |
| 메뉴 묶음 | padding 8px, gap 8px, min-height 58px, border 1px |
| Graph/Import 작업 버튼 | height 40px; Graph padding `0 13px`, font-size 12px, weight 700 |
| 내비게이션 | padding 4px, gap 4px; 버튼 height 36px, padding `0 12px`, weight 700 |
| 기본 글꼴 | Arial, `Apple SD Gothic Neo`, sans-serif; body 14px / 1.55 |
| 기본 버튼 / 주요 작업 버튼 | weight 600 / 700; 선택 전후 weight를 바꾸지 않는다 |
| 입력창·Graph 미선택 비교 버튼 | border `#bac2ca`, inset shadow `inset 0 1px 2px #28344105` |
| 상단 내비게이션·공통 메뉴 묶음 외곽 | border `#8997a5` 1px |
| 일반 카드/표/dialog 경계 | `#c0c7ce` 또는 공통 `--glass-line`, 해당 기존 컴포넌트를 따름 |
| 공통 glass line | `rgba(100,110,120,.20)` |
| 기본 선택/주요 버튼 | `#292b2e`, 흰 글자; Graph 비교 버튼은 기존 선택 스타일 유지 |

정확한 glass 표면 값:

```css
/* 공통 패널 */
--glass: rgba(255,255,255,.56);
--glass-shadow: inset 0 1px 0 #fff, inset 0 -1px 0 #ffffff70,
                0 8px 24px #28344112, 0 1px 3px #2834410a;
/* 메뉴 묶음 배경 / blur */
background: linear-gradient(135deg,#fffffff0,#ffffff65 55%,#ffffffb8);
backdrop-filter: blur(22px) saturate(125%);
/* 메뉴 묶음 + 상단 nav의 최종 그림자: 기본 패널 그림자보다 명확함 */
box-shadow: inset 0 1px 0 #fff, inset 0 -1px 0 #ffffffa6,
            0 2px 4px #28344130, 0 8px 18px #28344120;
/* 큰 glass 패널 */
background: linear-gradient(135deg,#ffffffdd,#ffffff75 60%,#ffffffbc);
backdrop-filter: blur(24px) saturate(125%);
```

- header 배경 `linear-gradient(110deg,#ffffffc9,#ffffff70)`, blur 28px / saturate 130%. 일반 패널과 header에 `-webkit-backdrop-filter`도 함께 사용한다.
- body는 흰 radial 두 개와 `linear-gradient(130deg,#f8f9fa,#e9ecef 55%,#f7f8f9)`를 합친 fixed 배경이다. 새 페이지가 독자적으로 유색 배경을 추가하지 않는다.
- Graph 미선택 비교 버튼은 흰 배경·입력창과 같은 경계/안쪽 음영이다. 바깥 메뉴 묶음의 경계와 안쪽 버튼 경계를 혼동하지 않는다.

## 3. 레이아웃과 스크롤

- `.page > .page-toolbar`, `#graphs > .graph-toolbar`: padding `0 5px 8px`, margin `0 -5px 12px`, min-height 0, align-items flex-start. 첫 메뉴의 위쪽 padding을 페이지마다 임의로 추가하지 않는다.
- Graph 좌측 비교 버튼, 우측 개수/내보내기, Import META/FACS, Data 필터/내보내기 묶음은 공통 스타일을 공유한다. Graph 내부 `.import-tabs`에는 border/padding 0, gap 8px를 적용하여 외곽선 중복을 방지한다.
- Graph toolbar는 `overflow:visible; flex-wrap:wrap`. **`overflow-x:auto`를 되살리지 말 것:** 다른 축의 visible도 auto로 계산되어 아래 그림자가 사각형으로 잘렸다. `overflow-y:visible`만 추가해도 해결되지 않는다. 폭이 부족하면 묶음을 다음 줄로 보낸다.
- 스크롤은 표 본문·이미지 뷰포트·설정 본문처럼 필요한 내부에만 둔다. 외곽 그림자를 가진 부모에 무조건 overflow hidden을 주지 않는다. 내부 내용을 둥근 카드에 잘라야 한다면 외곽 그림자와 내부 clipping의 책임을 나눈다.
- `html{scrollbar-gutter:stable}` 유지. 페이지 높이 변화로 상단 메뉴가 좌우로 움직이지 않아야 한다.
- 긴 metric 버튼: `min-width:0; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap`. flex/grid 자식에도 min-width 0이 필요하다.
- Graph는 한 화면에 두 그래프를 보여주고 행 단위 snap을 사용한다. 높이는 `max(300, floor(innerHeight - figureTop - 18))`로 산출해 `--graph-view-height`에 전달한다(기본값 600px). toolbar 높이가 변하면 다시 계산해야 한다.
- Graph figure: overflow-y auto / x hidden, scroll-snap-type y mandatory, overscroll-behavior-y contain, scrollbar-gutter stable. 카드 height 100%, min-height 0, snap-align start / stop always. SVG는 width/height 100%로 비율 유지. 좌우 카드의 시작·끝과 sidebar 시작 높이를 함께 확인한다.
- 하단 Group colors/Summary: radius 24px, border `#b8c0c8`, 배경 `#f7f8fa`, shadow `0 2px 6px #2834410c`, backdrop blur 없음. summary radius는 23px, 펼쳤을 때 하단 모서리는 0. 부모의 불필요한 세로 padding으로 흰 띠가 생기지 않게 한다.
- Gating: 좌측 목록 190px / 중앙 `minmax(0,1fr)` / 우측 설정 310px, gap 14px. 목록·설정은 독립 스크롤, 중앙 Fit/zoom/pan. 선택 후 목록 scrollTop을 보존한다. zoom 버튼은 이미지 우측 상단의 작은 도구로 둔다.

## 4. 클릭·드래그 탭 전환

- DOM의 기존 `button[data-page]`와 권한 검사/페이지 전환 handler를 재사용한다. 새로운 드래그 코드에서 직접 페이지 hidden 상태를 임의로 바꾸지 않는다.
- 클릭/키보드 선택: 하나의 `.nav-selection-indicator`가 이동한다. 색 `#292b2e`, radius 999px, shadow `0 2px 5px #0001`; left/top/width/height를 **260ms `cubic-bezier(.22,1,.36,1)`**로 변경한다. 콘텐츠 자체를 좌우로 미는 기능은 아니다.
- nav는 relative/isolation isolate, 표시 막은 z-index 0·pointer-events none·aria-hidden, 버튼은 relative/z-index 1. 실제 active 버튼은 투명 배경으로 하고 글자 색은 유지한다.
- 버튼 선택 여부로 padding/font-weight/테두리 두께가 바뀌면 인접 탭이 밀린다. 선택/비선택 모두 weight 700, 1px 투명 border 공간을 유지한다.
- 드래그 임계 거리 6px. primary pointer/왼쪽 버튼에서 시작하고 임계 이동 후에만 pointer capture를 건다. pointerdown 즉시 capture하면 일반 클릭 대상이 nav로 바뀔 수 있다.
- 드래그 중에는 미리보기만, 놓았을 때 기존 `.click()` 경로로 최종 이동한다. nav 좌우 범위 밖 또는 상하 16px 여유 밖에서 놓으면 취소. Esc, pointercancel/lost capture, 창 blur/resize도 취소한다.
- 드래그 표시: radius 999px, border `#8b99a8`, 배경 `linear-gradient(145deg,#ffffffed,#dce5eccc)`, blur 12px, shadow `inset 0 1px 0 white,0 3px 10px #28344130`. 포인터에 즉시 따라가며 기존 선택 막은 잠시 숨긴다.
- 드래그 직후 브라우저가 생성하는 trusted pointer click만 억제한다(`detail>0`). 프로그램 click/Enter 등 keyboard activation을 막지 않는다.
- hidden/disabled 탭 제외. 언어·권한·크기 변화 후 실제 rect로 위치 재계산. 최초 배치는 애니메이션 없이 수행한다.
- MutationObserver는 자신이 수정하는 indicator의 속성 변화를 무시해야 한다. hidden/style 변경을 다시 관찰해 무한 loop를 만들지 않는다. 기존 구현은 ResizeObserver 및 languagechange도 사용한다.
- `prefers-reduced-motion:reduce`에서는 선택 막 transition을 끈다.

## 5. Help 튜토리얼

- Help 진입점은 header 계정 영역의 공통 버튼이다. 페이지별 도움말은 현재 숨기되 기존 동적 설명 ID를 함부로 삭제하지 않는다.
- native modal dialog로 배경 조작/포커스를 제한한다. EN/KO, 이전·다음·완료·닫기, Esc, 종료 후 원래 포커스/스크롤 복원을 유지한다. 도움말은 데이터 쓰기·업로드·삭제를 실행하지 않는다.
- 네 개의 `.tour-glass` 영역이 강조 대상 바깥만 덮는다. **dialog와 `::backdrop`은 모두 background transparent / backdrop-filter none**. 전역 dialog blur가 남으면 강조 메뉴도 흐려진다.
- 주변 blur는 **2px**, saturate 105%, 배경 `linear-gradient(125deg,#e8edf326,#f7faff38)`. 기존 10px는 너무 강하다는 피드백으로 폐기했다.
- 강조 영역은 대상 rect 바깥 6px. 모서리는 대상 computed corner radius를 읽고 실제 크기에 맞춰 percent/pill 값을 환산한 뒤 6px를 더한다. 고정 20px를 모든 요소에 쓰지 않는다(CSS fallback만 20px).
- 강조선 2px `#768da3`, shadow `0 0 0 4px #ffffffb0,0 8px 32px #23364b22`. 위치/크기에 transition all을 걸지 않는다. 이전 단계 잔상이 생긴다.
- 안내 카드 width 360px, max-width viewport−32px, padding 22px, radius 24px, max-height viewport−32px. 대상과 18px 간격으로 배치하고 안 맞으면 위/옆으로 이동한다. 제목 20px, 본문 14px/1.65, 진행 표시 12px/700.
- 카드 자체 blur 24px는 유지 가능하지만 메뉴를 덮지 않아야 한다. 단계 대상이 숨김/없음이면 건너뛴다. resize/scroll 후 위치를 갱신한다.
- reduced transparency에서는 불투명 배경+blur none으로 대체한다. 모션 감소 설정도 존중한다. focus-visible을 제거하지 않는다.

## 6. 새 페이지에 적용하는 작업 순서

1. 기존 컴포넌트와 최종 computed style을 먼저 확인한다. style.css에는 역사적인 중복 선언이 있으므로 첫 번째 일치만 보고 판단하지 않는다.
2. 구조를 `작업 toolbar → 짧은 상태 정보 → 작업 본문`으로 만들고 공통 radius/toolbar 그룹을 재사용한다. 새 selector가 공통 규칙에서 빠지지 않게 한다.
3. 기능용 ID, data 속성, 번역, 권한, 저장 상태는 보존한다. UI 정리만으로 DB/계정/원본/그래프 통계를 수정하지 않는다.
4. blur·그림자는 바깥 셸, 콘텐츠 clipping은 내부로 구분한다. 양 축 overflow의 **계산된 값**을 확인한다. 사각형 그림자 단절은 border 색 변경으로 해결되지 않는다.
5. 브라우저에서 기본/선택/hover/focus/펼침/접힘, 긴 영어·한국어, 빈 데이터·실제 데이터 상태를 확인한다. 사용자 사진이 모호하면 외곽선/내부선/그림자 clipping 중 무엇인지 확인한 뒤 수정한다.
6. 변경된 CSS/JS의 index.html asset query version을 갱신한다. 실행 서버가 실제 파일을 제공하는지 확인하고, 캐시 때문이라고 근거 없이 단정하지 않는다.
7. 새 JS 파일을 추가하면 server.py 정적 파일 매핑과 scripts/deployment/alwaysdata.py 코드 배포 allowlist도 확인한다. 개발 확인과 운영 배포를 구분하고, 요청 없이 commit/push/배포하지 않는다.
8. AGENTS에는 새로운 확정 기준과 검증 결과를 반영한다. 단순히 예전 수치를 뒤에 누적해 상충하는 규칙으로 남기지 않는다.

## 7. 완료 전 검증 기준

- 1920×1080 및 실제 더 낮은 viewport, 폭 1280/1100에서 작업 버튼·그림자·focus ring이 잘리지 않는지 확인. 최상위 문서의 불필요한 가로 overflow가 없어야 한다.
- Graph/Data/Import toolbar 시작선·둥근 외곽 높이 비교. 그래프 좌우 카드 높이/하단 N 라벨/범례와 sidebar 내부 접근성 확인.
- 탭 클릭 시 실제 CSS transition 존재와 종료 rect가 버튼 rect에 1px 이내로 맞는지 확인. 클릭·드래그·드래그 취소·Enter·권한별 숨김·언어 전환을 점검한다.
- Help는 강조 대상 선명도와 카드 viewport 내 배치, Esc/포커스 복귀, 언어 전환 확인. 읽기 전용 조작 중 API 쓰기 요청이 없어야 한다.
- 자동 검사는 계산된 색/overflow/geometry와 동작을 확인하고 **스크린샷도 직접 확인**한다. 수치만 같아도 실제 그림자는 부모 clipping 때문에 다르게 보일 수 있다.
- 테스트는 mock 또는 개발 데이터에서 수행한다. 운영 DB·계정·비밀번호·원본·QA 접근 제한은 유지한다. 디자인 규약 변경 자체는 운영 배포를 의미하지 않는다.

---

# 현재 우선 지침 — 2026-11-09 폴더 정리

## 문서 위치와 정리 기준

- `README.md`와 `AGENTS.md`는 이 프로젝트 루트에 둔다. `WorkInProgress` 최상단에는 공통 README·AGENTS 등 Markdown 안내 파일을 다시 만들지 않는다.
- README는 사람이 읽는 목적·흐름·현재 결과·실행 위치 안내이고, AGENTS는 AI 작업 지침이다. 날짜별 과거 기록과 현재 지침을 구분한다.
- 별도 `_maintenance` 폴더를 만들지 않는다. 핵심 정리 내역은 기존 README나 작업 기록에 남긴다.
- 이 웹앱은 사용자 지정 예외다. 전체 폴더 정리에서는 README·AGENTS만 정비하며 실행 구조, 코드, 설정, DB, 원본, 백업, 자동 실행 구성과 파일 위치를 유지한다.

- 사용자는 **웹앱은 README·AGENTS만 정리하고 실행 구조를 유지**하도록 명시했다. 이번 전체 작업 공간 정리에서 이 프로젝트의 코드·설정·DB·원본·폴더·시작 파일·자동 실행·백업·배포는 변경하지 않는다.
- [README.md](README.md)를 사람용 시작점으로 사용한다. 상세 기능·통계·보존·검증 원칙과 날짜별 이력은 아래에 유지한다. 과거 기록의 최초 설치 상태를 현재 상태로 혼동하지 않는다.
- 운영은 `https://nplab.alwaysdata.net/`, Mac은 개발·검증용이라는 2026-11-06 기록이 최신 운영 설명이다. 이 문서 정비에서 원격 상태 확인이나 배포를 수행하지 않았다.
- 실제 로컬 DB·업로드 자료가 존재한다. 초기 빈 데모로 가정하거나 기존 계정·연구 데이터를 초기화하지 않는다.
- 자동 백업 중지 요청과 QA 전용 FACS 제한을 유지한다. 일반 Graph·FACS 요약 Import와 원시 FCS 분석 기능을 구분한다.
- 커밋·푸시·배포와 서비스 재설정은 폴더 안내 문서 정비에 포함되지 않는다.

---

# Mouse Sanctuary — 작업 인계 및 유지보수 지침

작성일: 2026-11-02 (Europe/Berlin)
최종 저장 위치: /Users/paul/WorkInProgress/nplab_mouse_web

## 프로젝트 목적과 사용자 요구

약 183마리 mouse의 실험값을 여러 연구자가 업로드·수정하고, GraphPad 형태의 그룹 비교 그림을 만드는 연구실 내부 웹앱이다. 모바일 대응은 필요 없다. 흰색 배경과 간결한 데스크톱 UI를 유지한다. 향후 mouse 및 새로운 측정 컬럼을 추가할 수 있어야 한다.

지원 대상에는 Body weight, OGTT, ITT, tissue weight, Total Cholesterol, LDL-C, HDL-C, Triglycerides, Fasting Glucose, H&E lipid droplet, PSR, organ별 여러 FACS gate가 포함된다. 실제 업로드된 데이터와 예시/미측정 항목을 구분한다.

## 오늘 구현·수정한 기능

- Python HTTP 서버 + SQLite 기반 계정 로그인, 관리자/편집 권한, 다중 사용자 업로드 및 수정. 버전 충돌은 409로 처리하여 다른 사용자의 변경을 덮어쓰지 않는다.
- 고유 mouse ID, metric, timepoint, replicate로 관측값을 구분한다. 원본 업로드 바이트·해시를 보존하고 수정·제외·복원 이력을 남긴다.
- XLS/XLSX/CSV Import, FlowJo XLS 다중 표 인식, 샘플명과 mouse ID 매핑 검토, 결측값과 실제 0 구분.
- 그래프는 1–8개까지 선택한다. 기본은 4개이며 여러 그래프는 2열로 표시한다. 각 그래프의 측정 항목/gate, 시점, 반복, 축 등을 선택한다.
- 하나의 공통 패널에서 그룹 순서·표시·색상·점 기호·채움을 모든 그래프에 적용한다. ≡ 드래그 핸들과 방향키로 순서를 변경한다.
- 오른쪽 샘플 창은 Exp → Diet → Mouse 계층이며 초기에는 접혀 있다. 검색 시 해당 경로를 펼친다.
- 샘플 선택 변경을 모든 그래프에 즉시 미리보기로 반영한다. 사유를 입력하고 저장하면 mouse 전체에 전역 제외/복원이 적용된다. 취소하면 저장 전 상태로 돌아간다.
- N 상세에서 측정값 있음, NULL 결측, 미측정, 전역 제외를 ID별로 구분한다.
- One-way ANOVA + Tukey 다중비교를 서버에서 계산한다. 표본 수가 다르면 Tukey–Kramer. 수동 p-value 입력과 기준 그룹 선택은 제거했다.
- p-value 보기는 모든 쌍 / 0.1 미만 / 0.05 미만. 반올림 전 Tukey 보정 p에 엄격한 < 조건을 적용한다. 보기 변경은 전체 비교 집합의 보정이나 통계 계산을 바꾸지 않는다.
- SVG/PNG 그림, 데이터 CSV, 전체 통계 CSV, 공유 그래프 서식 저장을 지원한다.

## 최종 기본값 — 반드시 유지

- 오차 막대: 평균 ± SEM. 사용자가 SD로 바꿀 수 있다.
- p-value 보기: 0.05 미만.
- Y축 하한: 0.
- 모든 그룹의 막대: 윤곽. 채움 모드의 불투명도는 35%(투명도 65%).
- 색상: Chow #000000, Western #fc225c, TRF 6:18 #197274, TRF 10:14 #64c3fa, ADF #3b0070, Reverse #a55af8.
- 기본 기호: Chow 사각형, Western 삼각형, TRF 6:18 역삼각형, TRF 10:14 마름모, ADF 원, Reverse 사각형.
- 저장된 서식에서 사용자가 명시적으로 선택한 SD/SEM, p-value 보기 등은 복원한다. 새 그래프 기본값 변경을 이유로 기존 서식을 일괄 덮어쓰지 않는다.

## FACS 데이터 해석

원래 파일은 research 드라이브의 다음 폴더에서 받았다:
`/Volumes/research/mk3-L15/AG Perakakis/Sol/Data/FACS/2026-06-25_T cell Panel mouse/Results_combine/`

- `T cell 36w DI combine_Count.xls`: 사용자가 Sheet0 (2)의 아래 계산 표(헤더 93행, 데이터 94–179행)만 사용하도록 확정했다. 이름 Absolute Count, 단위 cells/µL. 위쪽 원시 Count를 대신 사용하면 안 된다. 86마리 × 26 gate = 2,236개 관측값.
- `T cell 36w DI combine_Freq.xls`: 88마리 × 26 gate = 2,288개. Excel % 서식의 소수 저장값은 ×100하여 %로 가져온다. Freq. of Parent의 분모/상위 gate를 유지한다.
- `T cell 36w DI combine_MFI.xls`: 86마리 × 24 항목 = 2,064개(결측 6개 포함). 원본 통계량은 Geometric Mean이다. 산술평균이나 median으로 바꾸지 않는다.
- MFI 그래프 제목은 원본 열 제목 `gate 경로 | Geometric Mean (…)` 그대로 사용한다. 업로드 mapping의 column에서 source_header를 읽어 표시하며, 긴 제목은 줄바꿈한다. 원본 metric ID/정의는 그대로 유지한다.
- 일반 gate 선택 표시는 /로 구분된 마지막 이름을 사용한다. 전체 경로는 원본·메타데이터·툴팁에 보존한다. MFI 그래프 제목은 사용자의 최신 요청에 따라 원본 전체 열 제목을 사용한다.
- a.u.는 arbitrary units(임의 단위), 여기서는 상대 형광강도 표기이다. 실제 농도 단위로 해석하지 않는다.
- Frequency에는 mouse 44·45가 추가로 있어 Count/MFI와 N이 다를 수 있다. 임의로 N을 맞추거나 결측을 0으로 채우지 않는다.
- 확인 당시 Absolute Count와 Frequency의 실제 음수 관측값은 0개였다. 음수 축은 평균−SD가 0 미만이어서 발생했다. 최종 UI는 Y축 0 미만의 오차 막대 부분만 화면에서 잘라내고, 화면과 SVG에 이를 명시한다. 평균·SD·SEM·통계 및 원본 값은 변경하지 않는다. 실제 음수 관측값을 조용히 숨기지 않는다.

## 통계의 범위

독립 표본, 정규성, 등분산 가정의 one-way ANOVA/Tukey이다. 각 그래프 내부의 전체 그룹 쌍을 한 비교 집합으로 보정한다. 그래프/gate 사이 추가 보정은 없다. 그룹당 n<2, 비교 그룹 부족, 그룹 내 분산 모두 0, 중복된 mouse 반복 혼합 등은 계산 불가를 표시한다. 시간 곡선의 반복측정 통계와 AUC는 아직 구현하지 않았다.

샘플 선택 변경 시 이전 p-value를 제거하고 새 결과를 계산한다. revision을 검증하고, CSV에는 보기 필터와 관계없이 전체 비교 결과를 내보낸다. SVG 메타데이터에는 분석 방법, 원본 데이터 해시, 그룹별 mouse ID, 보정 p, revision, 미저장 선택, 축 범위와 오차 막대 생략 여부가 포함된다.

## 저장된 데이터와 계정

`data/lab.sqlite`는 작업 중 사용하던 `work/qa-v2.sqlite`의 SQLite backup API로 만든 일관된 복사본이다. 연구 데이터, 업로드 원본, 계정, 공유 서식, 이력을 포함한다. 일반 ZIP 배포본에는 DB가 없지만 이 프로젝트 폴더에는 현재 상태를 보존하기 위해 DB를 함께 저장했다.

원본 roster는 183마리이며 현재 작업 DB에는 QA용 mouse 6마리가 추가되어 총 189마리가 보인다. QA 자료를 연구 데이터로 혼동하지 말고, 임의 삭제하지 않는다. 확인 당시 전역 제외 ID는 156, 157, 158, 159였다. 이 사용자의 선택을 초기화하지 않는다.

기존 계정으로 로그인한다. 계정 비밀번호나 세션 토큰을 이 문서 또는 저장소에 기록하지 않는다. data/ 및 백업은 공개 저장소·외부 서비스에 업로드하지 않는다.

## 실행 방법

1. 이 폴더의 `start.command`를 실행한다.
2. 로컬 주소는 기본 `http://127.0.0.1:8000/`이다.
3. 첫 실행에 필요한 패키지가 없으면 로컬 `.venv`를 만들고 requirements.txt를 설치한다. 이 과정은 인터넷이 필요할 수 있다.
4. 이 복사본의 기본 DB는 `data/lab.sqlite`이다.

저장 시점에 기존 작업 서버는 `http://127.0.0.1:8766/`에서 이전 작업 폴더와 이전 DB로 실행 중이었다. 이번 요청은 최종 폴더 저장이므로 기존 서버의 실행 경로를 자동 전환하지 않았다. 복사본을 실행한 뒤에는 해당 폴더의 DB가 독립적으로 갱신되므로, 실제로 사용할 서버/주소를 하나로 정해서 작업한다.

의존성: openpyxl 3.1.5, numpy 2.2.6, scipy 1.16.3. XLS reader xlrd와 라이선스는 vendor/에 포함한다. 기존 가상환경은 경로에 종속되므로 복사하지 않았다.

백업: `python backup.py backups/lab-YYYYMMDD.sqlite` (기존 파일은 덮어쓰지 않는다). 실행 중인 DB를 일반 파일 복사로 백업하지 않는다.

## 파일 구성과 검증

- server.py: 로그인/CSRF/API/정적 파일 제공
- service.py: SQLite, Import, 수정, audit, 공유 서식, MFI 원본 제목 메타데이터
- facs.py 및 import_profiles.json: XLS 해석과 확인된 Count 표 선택
- statistical.py: ANOVA/Tukey 계산
- static/app.js: 화면 상태·공통 그룹 설정·샘플 선택·통계 요청
- static/chart.js: SVG 차트·SD/SEM·비교선·원본 제목·0 하한 표시
- seed/: 원본 mouse roster
- deploy/: 향후 맥미니 운영용 준비 자료
- README.md: 상세 설명

확인 완료: Python 테스트 22개, 차트 테스트 16개. 브라우저에서 8개 그래프, 전역 제외 미리보기/취소, p-value 재계산, 세 가지 보기, 0 하한, 윤곽/채움 및 SVG 내보내기를 확인했다. 저장된 MFI 원본 XLS 24개 열 제목과 그래프 제목이 모두 일치한다. 가장 마지막 SEM 변경은 기본값/UI 선택을 수정하고 JavaScript 구문 검사를 통과했다.

검증 명령(의존성 설치 후):
`python -m unittest test_service test_facs test_statistical`
`node --test test_chart.cjs`

## 다음 작업 시 주의

- 사용자는 맥미니를 이용한 외부 접속을 원하지만 연결 작업은 나중에 하기로 명시했다. 외부 접속, Tailscale, 자동 실행 서비스 설치를 임의로 진행하지 않는다.
- 대상 폴더에 원래 있던 `Treg 36w DI combine_for Prism.xlsx`는 그대로 보존했다. 이번 저장 요청만으로 이 파일을 분석하거나 Import하지 않았다.
- 오늘 사용자는 “충격적인 소식을 들었다”고 말했으나 그 내용은 아직 제공하지 않았다. 추측해서 데이터 정의나 분석 방법을 바꾸지 않는다.
- 수정 시 원본 불변성, 고유 mouse ID 연결, 결측/0 구분, 여러 gate/반복 구분, audit 및 사용자 설정 보존을 우선한다.

## 추가 Import: mouse info with histo mean.xlsx

사용자 확인에 따라 Sheet1만 사용하여 Liver PSR/HE, 단위 %로 Import했다. 183개 기존 ID, 366개 관측 행(각 항목 182개 실측과 1개 NULL), 신규 mouse 0. Sheet1_t120은 사용하지 않았다. histology.py가 좌우 표를 정규화하며 source_row와 mapping.source_cells로 원본 셀을 추적한다. 원본 숫자 배율 변환 없음. 원본 XLSX 바이트 보존, 기존 데이터/그룹/제외 상태 보존, import 및 관측 생성 audit 기록, 작업 전 backups/에 일관된 DB 백업을 생성했다. 최종 폴더 data/lab.sqlite에만 추가했으며 이전 작업 폴더의 8766 서버 DB는 별도이다.

## 추가 UI 피드백

p-value 보기에 표시 안 함(none)을 추가했다. 선택 시 그래프의 ANOVA·Tukey 숫자·비교선과 카드의 통계 문구를 숨기며 통계 CSV 계산 결과는 유지한다. 기본값은 p<0.05이다. 그래프에 유효한 개체가 없는 그룹을 제거하며 N 상세의 결측·제외 정보와 복원용 샘플 트리는 보존한다. 사용자가 제외 개체도 표시를 명시하면 해당 빈 점은 보인다. Exp 옆에 roster의 weeks를 작은 회색 bold로 표시하며 여러 주차가 있으면 함께 표시한다. 차트 테스트 18개 통과.

- Exp 주차 라벨: 해당 Exp의 원래 roster에 ADF, RC/Reverse, TRF 그룹이 하나라도 있으면 `36 Weeks / Dietary Intervention` 형식으로 표시한다. Chow/Western만 있으면 주차만 표시한다. 검색·샘플 제외에 따라 실험 라벨이 바뀌지 않도록 전체 roster를 기준으로 판정한다.

## 최종 브랜드: Mouse Sanctuary

사용자가 Mouse Sanctuary 이름과 생성된 통통한 마우스 아이콘을 승인했다. 로그인·상단 로고·페이지 제목·favicon에 적용. static/mouse-cemetery.png는 첨부 사진의 서 있는 마우스만 참고하여 내장 image_gen으로 생성한 투명 PNG이다. 생성 지시: 오른쪽 위를 보는 둥근 귀의 검정 마우스, 왼쪽으로 휘는 꼬리, 더 통통한 배와 엉덩이, 간결한 실루엣, 배경·표지판·문자 제거. 원본 생성 이미지를 수정 없이 프로젝트에 복사했다.

- 최종 이름은 사용자 요청으로 Mouse Sanctuary로 변경했다. 로그인·상단 로고·브라우저 제목·실행 메시지에 반영. 승인된 마우스 이미지는 그대로 사용하며 기존 이미지 파일명/URL mouse-cemetery.png는 호환성을 위해 유지한다.

## 2026-11-03 현재 운영: 내부망 전용

사용자가 외부 접속 대신 내부망 전용 운영을 선택했다. Tailscale/Cloudflare는 설치하거나 활성화하지 않았다.

- 접속 주소: http://10.92.73.22:8000/
- 유선 en0 주소에만 바인딩, 허용 클라이언트 대역 10.92.73.0/24. 다른 대역은 HTTP 403. X-Forwarded-For 등을 신뢰하지 않고 실제 소켓 발신 IP로 판단한다.
- Wi-Fi en1(192.168.83.99)은 허용하지 않는다. 다른 연구실 PC의 대역이 다르면 그 범위를 확인한 뒤 명시적으로 추가해야 한다. 모든 학교 네트워크를 자동 허용하지 않는다.
- 현재 HTTP 연결이며 전송 암호화는 없다. HTTPS가 필요하면 내부 인증서 배포를 별도 구성한다.
- 최종 폴더 .venv에 requirements.txt를 설치했다. com.mouselab.server/backup LaunchAgent를 등록했다. 서버는 caffeinate -is로 시스템 잠자기를 방지하며 로그인 후 자동 실행된다. 재부팅 후 macOS 사용자 로그인이 필요하고 로그아웃/종료 중에는 사용할 수 없다.
- 매일 03:00에 backups/로 SQLite 일관된 백업을 생성한다. SMB로의 복사는 아직 구성하지 않았다.
- 실행 DB는 이 폴더 data/lab.sqlite이며 이전 8766 작업 DB와 혼동하지 않는다. 사용자에게 위 내부망 주소를 안내한다.
- 배포 스크립트: deploy/setup-lan.py --host 10.92.73.22 --network 10.92.73.0/24 --install. 이미 등록된 서비스에는 실행을 거부한다. 중지 시 deploy/stop-services.command 사용. 기존 install-services.command는 이전 VPN용이므로 현재 LAN 운영에 사용하지 않는다.
- IP 주소가 바뀌면 서비스 바인딩과 접속 주소를 함께 갱신해야 한다. DHCP 예약 여부는 확인하지 않았다.
- 확인: 유선 소스 IP에서 /api/me 및 최신 Mouse Sanctuary 페이지 HTTP 200, Wi-Fi 소스 IP에서 403, 관리자 초기화 완료, 서버 running 및 백업 예약 등록 확인. 다른 물리 PC에서의 접속은 아직 확인하지 않았다.

## 2026-11-03 English interface

User requested English UI. Menus, graph settings, sample selection, import/edit/account screens, chart validation, server errors and statistical notices now use English; HTML lang=en and dates use en-GB. Original imported names, notes, audit history, missing reasons and metric identity metadata are preserved. Korean import-header aliases and internal fallback/group keys remain compatible with existing data and presets. No DB migration or network permission changes. Existing chart tests now expect English errors. Validation: 22 Python tests and 18 chart tests passed.

User reports wired LAN access works, but eduroam does not. The current 10.92.73.0/24 allowlist remains unchanged. A different eduroam subnet is denied by the app; school routing restrictions are also possible and have not been verified.

## 2026-11-03 Account settings and ERD

Added My account: self-service username rename and password change with current-password verification. Admins can rename accounts in User management. Username is the login name (no separate display-name field). Rename preserves user ID, role, uploads and audit links; duplicate names and stale expected usernames are rejected. Existing history lists the current joined username; rename events preserve old/new names. Password updates use a new salt and PBKDF2 hash, revoke all owner sessions, and record a secret-free audit event. Password attempts are limited to five per account per five minutes. Routes require existing session and CSRF. No real account credentials changed during QA; tests use disposable databases. Schema unchanged. New test_accounts.py (4 tests) and test_account_http.py (2 HTTP tests) cover rename authorization/conflicts, CSRF, self-only password updates, revocation, rate limits and secret-free audit. Existing 22 Python tests also passed. Full schema ERD: docs/database-erd.md, verified directly from the live SQLite schema.

## 2026-11-03 FCS Explorer v1

Implemented shared original FCS/WSP library, 2 MB resumable binary upload (FCS 2 GB/WSP 100 MB), owner/timestamp/hash tracking, authenticated original download, immutable catalogue and completed analyses. Originals are SHA-256-addressed files in data/fcs/objects plus a verified same-disk mirror; staging is retained. No delete/overwrite UI. Off-device/SMB backup is NOT configured. Existing daily backup now includes original/derived assets and a manifest via fcs_backup.py; a full restore of the actual 3 files + 2 analyses was verified in a separate temp directory (11 assets). Do not back up SQLite alone now.

Supplied Liver_146.fcs (249802 events) and Liver_147.fcs (443017), 20 channels each, and EXP9_T cell combine.wsp (FlowJo 10.10.0) were ingested under qa_admin by the assistant; source hashes verified against original Downloads files and mirror. WSP IDs 153/154 must not be treated as mouse IDs 146/147. Each sample imports 43 gates. WSP /→_ aliases are normalized in memory only with collision checks. FlowKit 1.2.3 runs in isolated .fcs-venv (requirements-fcs.txt), keeping existing main dependencies unchanged. Browser scatter/density/histogram, parent-population gate overlays, 20k deterministic plot sampling, full-event counts, FlowJo-reference comparison, PNG and gate CSV are available.

IMPORTANT: 32/43 counts differ for 146 and 28/43 for 147 versus saved WSP reference counts. These are unresolved differences; do not call results FlowJo-equivalent. UI and CSV explicitly show differences. Existing measurements were checked unchanged. No automatic export to existing measurements; event counts are not cells/µL. Imported gates are read-only; editing/UMAP/t-SNE/private sharing are not implemented. See docs/fcs-explorer.md for support/analysis-memory limits and restore procedure.

Tests: 31 service/unit tests + 3 HTTP + 18 chart tests passed, including large/resumable upload, ownership, CSRF, original immutability, backup/restore. Actual gate counts/ancestry and rectangle overlay coordinates checked. Full DB export now includes FCS manifests/runs (not original bytes); download originals separately or use complete backup bundles.

## 2026-11-03 FCS count discrepancy audit

Read-only audit of Liver_146/147: FCS identity matches WSP metadata; direct DATA float parsing matches first 19 raw channels exactly. WSP 13x13 Comp Tcell 36w matrix/order and independent compensation calculation match exactly. FCS embedded matrix differs from WSP (max coefficient delta 0.3499995287559233); WSP matrix is correctly used. All 33 transform settings per sample and all polygon vertex conversions checked. Comp-/unprefixed transform pairs are identical in this workspace. First mismatch is uncompensated FSC-A/SSC-A Cells (+15/+62), then parent membership differences propagate. FlowJo binning/polygon-edge compatibility is the leading hypothesis, NOT a fully established explanation: global 256-bin rounding reduces some differences but fails to reproduce all counts. Do NOT introduce guessed rounding or force counts to WSP references. Fresh FlowJo recomputed counts and gated-event exports are needed for event-level confirmation. No production algorithm, DB, original file, or completed run was modified. Audit report, 86-gate CSV, JSON details and reproducible diagnostic script: docs/fcs-audit-20261103/.

## 2026-11-03 QA gate editor

FCS Explorer is now restricted to stable user IDs [1, 2, 3] (qa_admin, qa_editor, qa_viewer) in fcs_access.json. Missing/invalid config denies access. Other administrators do not bypass this restriction; renaming an account cannot grant access. All /api/fcs/* endpoints enforce it before body processing, including chunks/download/plot/edit. Login/me expose fcs_access; UI hides the tab. General export/audit omit FCS catalogue, runs and FCS events for non-QA users. Existing graph/data/import functionality remains available. Do not enable general release without the user's request.

Added 2D finite rectangle and polygon drawing and handle dragging. Select a population then New rectangle/New polygon to create a child; select an existing 2D gate then Edit selected gate to modify it. Axes are frozen during editing; Cancel discards only the draft. Enter a gate name and mandatory reason, then Save as new analysis. Each save queues a new immutable run with actor/time/reason/base_run and cumulative geometry changes in fcs_runs.edit_spec. Migration adds this nullable column plus an immutable update trigger. Finished runs and original FCS/WSP bytes remain unchanged. Full-event membership is recalculated for edited gates and descendants using the exact stored coordinate axes and FlowUtils polygon / FlowKit-style rectangle bounds (min inclusive, max exclusive). Child names/paths update after parent rename. Affected FlowJo reference comparisons are cleared; unchanged gates retain theirs. No attempt to fix unresolved FlowJo binning differences. New gates support all available axes; changing compensation/transforms, 1D/open-ended gate editing, deletion, WSP export and batch propagation are not implemented. Self-intersecting polygons and invalid geometry are rejected. Max 100 edits/lineage and existing memory limits remain.

Validation: 14 access/library/account HTTP+unit tests, 22 existing service/FACS/statistics tests, 2 isolated gate geometry tests; JS syntax checks. Actual 146/147 unchanged Cells geometry edits reproduced all 43 prior app counts each. Production browser saved an unchanged Cells analysis and a new QA rectangle check under Cells (156946 events); both are clearly recorded as QA verification versions, not biological results. Original four-file catalogue and 6978 measurements unchanged; completed prior analyses preserved. A pre-existing running user analysis completed normally during rollout. Before deployment backup: backups/pre-gate-editor-20261103T111250.sqlite plus asset manifest/bundle; prior source in backups/gate-editor-code-20261103T111250.

## 2026-11-03 FlowJo-style FCS workspace

Reworked static/index.html, static/fcs.js and static/style.css into a desktop white/gray workspace inspired by FlowJo v10: ribbon tools; searchable samples; collapsible population hierarchy with counts/% parent; analysis versions; breadcrumb/parent navigation; central plot with axis/display selectors; right population inspector and gate editor; collapsed statistics; original-file/upload and new-analysis dialogs. Sample click opens its latest completed WSP analysis, falling back to latest completed/raw or pending run. Existing gate drawing/version-save APIs, original preservation and QA-only ID allowlist remain. No new FlowJo algorithm parity or unsupported tools claimed. Existing count discrepancies remain prominently visible.

During browser verification the existing server exhausted file descriptors: Store.db context managers committed/rolled back but never closed SQLite connections, including background queue polling. Added ClosingConnection that closes after context exit while retaining transaction behavior. No schema/data changes. Restarted existing LAN service. test_connection_lifecycle.py retains 1100 connection references to ensure closure, and checks commit/rollback. 36 existing service/FACS/statistics/account/FCS tests and 2 new lifecycle tests passed. Browser QA: Liver_147 43-gate tree, collapse/expand, parent navigation, edit/cancel, pseudocolor, files and analysis dialogs; no console errors. No new production analysis or data modification during this UI verification. Backup prior static files and service.py: backups/workspace-ui-20261103T113147.

## 2026-11-03 Compact FCS plot

Reduced the central FCS canvas display to 85% of its panel width, capped at 650px. Canvas resolution and coordinate mapping remain unchanged. Other charts are unaffected.

## 2026-11-03 FlowJo WSP export and SMB references

User requested bidirectional FlowJo file compatibility, then requested WSP-linked FCS path import and explicitly confirmed S:/MK3/research/ maps to /Volumes/research/. Added fcs_paths.json (server-managed allowlist), fcs_references.py, fcs_export.py; new QA-only, CSRF-protected POST /api/fcs/export and /api/fcs/import-reference, QA-only GET /api/fcs/workspace-files/{wsp_id}. Existing original download provides generated WSP files. No access scope/network change.

FlowJo WSP ribbon button exports a completed WSP-backed analysis to a NEW immutable library file, with mirror, normal asset backup inclusion and export provenance audit. The original full WSP is copied: only selected sample edits are applied, other sample/group/template XML retained. Edited rectangle/polygon geometry is inverse-transformed back to WSP coordinates; edited gates become sample-specific, stale counts/statistics are cleared for affected populations. Selected FCS URI is relative to the WSP; download original FCS alongside it or reconnect in FlowJo. Other referenced FCS files are not bundled. Round-trip gate hierarchy, shape, axes and bounds are checked before publishing. No WSP-free export, .flowjo v11 native export, or multi-run merge yet. FlowJo desktop application verification is PENDING; do not equate successful FlowKit round-trip with identical FlowJo counts.

Files & upload now lists WSP references with original Windows URI, mapped Mac path, availability, filename matches and searchable sample names. Import from SMB copies only configured-root regular .fcs files through the existing chunk/hash/mirror pipeline; no client-supplied server path and no writes to SMB. Paths escaping root or through out-of-root symlinks are rejected. SMB source size/mtime changes abort publication. Identical SHA-256 already in the catalogue reuses that file ID (retained staging copy, provenance audit); name match alone does not establish identity. Shares must remain mounted on the server to import new data. Already imported copies remain usable if disconnected. Original sample paths are evidence, not trusted instructions. All 101 references in supplied WSP were available.

Validation: 41 main Python tests + 5 isolated gate/export tests passed. Test suites cover root escape/symlinks, missing paths, source preservation/hash deduplication/audit, edited parent rename/new child/coordinate inversion, no-edit geometry preservation and QA access denial to new endpoints. Four actual 146/147 analyses (including existing edit/new-gate runs) exported/reimported with identical full-event membership masks and counts; all other samples, selected compensation/transform XML and original hashes preserved. Additional isolated Liver_147 compensated biexponential rectangle change + parent rename + new polygon also matched all event memberships across 44 gates. Reports in docs/flowjo-interop-validation. Source backup: backups/flowjo-interop-code-20261103T115654. Browser verified 44-gate WSP export saved under qa_admin and 101 SMB references; original lab measurements unchanged.

SMB production QA initially waited in macOS NetworkVolumes authorization (TCC log confirmed prompt at 11:58 and permission event at 12:18). Source then copied successfully and SHA-256 deduplication reused Liver_146's original catalogue ID. No grant was automated. Added fcs_copy.py: approved source copy now runs in a bounded subprocess (120 seconds), reports permission/mount guidance on timeout, and publishes nothing on copy failure. Source copy/deduplication/timeout tests passed; 6978 lab measurements unchanged. Re-tested 11 reference/library/access/HTTP tests after this change.

## 2026-11-03 SMB originals linked without local FCS copies
User changed requirement to save Mac disk space. Files dialog now uses Link SMB original / Link all available with sequential progress, stop after current file, per-file errors and retry. Keep tab open; this is a browser-managed queue, not a persistent background batch. All includes whole workspace regardless of search. POST /api/fcs/link-reference is QA-only, uses approved WSP sample path, read-only bounded SHA-256 probe, immutable fcs_external mapping and provenance audit. No objects/mirror/staging bytes written for linked originals. Existing local uploads/copies retained. Source is revalidated on use and after analysis; changed source requires a new linked version. SMB must remain mounted; no app backup of external original bytes. Backup manifest records external paths/hashes separately and continues backing up local files/results. Analysis caches still consume local space. Existing copy endpoint retained for compatibility, but no longer used by reference UI.

## 2026-11-03 Four horizontal FCS plots
FCS Explorer defaults to four compact plots (1–4 selectable). Each slot retains its own gate, axes, display and preview for the current analysis. Select a card to use common controls and live gate editor; inactive cards show retained canvases. Sample/version changes reset slots; unsaved gate edits block slot/layout changes. PNG exports active plot only. Narrow desktops scroll horizontally. Inspector moved below plots to provide width. No source/DB/statistics change.

## Gate editor feedback fix
User reported spinning cursor after rectangle/polygon. Browser reproduced ready editor but disabled tool had cursor:wait and instructions below plots. Added prominent editor-ready banner/cancel, crosshair on active editor canvas, default disabled-button cursor. Plot preview has 30s timeout/error feedback and stale response readiness guard; duplicate editor starts guarded. Three request tests cover timeout, stale and success. No commit/push: user requires prior confirmation for commits.

## 2026-11-03 Eight FCS plots and multi-sample comparison
Supersedes four-plot behavior above: layout supports 1–8 plots, up to four columns (eight uses two rows). Each card selects a completed analysis, retaining its own run, gate, axes, display and preview; selecting a different sample replaces only the active slot. Header selects a slot for common controls; plot body enlarges it, Back to all plots/Escape closes enlargement. Unsaved gate edits block sample/slot/layout changes. Placeholder selection does nothing. Original files, DB and QA access unchanged. This is side-by-side comparison, not event overlay; layout is session-only. Browser verified Liver_146 and Liver_147 together, eight cards, zoom/back, and retention after 8→1→8. JS syntax and three plot request regression tests passed. Commit/push still requires user's prior confirmation.

## 2026-11-03 Gate deletion/editing and Home
Added Delete gate confirmation with descendant count and mandatory reason. POST /fcs/edit validates delete operations, removes the subtree in a NEW immutable analysis, remaps indices/masks, and supports later edits. Older runs and original FCS/WSP remain untouched. WSP exporter replays deletion lineage and removes matching sample populations from a copied XML; round-trip tests cover delete-all and delete-then-add. Existing rectangle/polygon Edit gate supports handle movement and renaming; added clear editing banner and unsupported-kind guard. QA access unchanged. UI verified edit readiness and deletion confirmation/cancel without changing production analyses.
Home is the default signed-in page: mouse/experiment/metric/non-null measurement counts, graph/import shortcuts, QA-only FCS summary and recent library files. Analysis total explicitly limited to recent history returned by library endpoint. White desktop layout. Eight gate/export tests and two access/HTTP tests passed; JS syntax and diff whitespace checked. Server restarted to load validation changes. No commit/push performed; prior confirmation still required.

## 2026-11-03 Combined FCS analysis and restricted Home list
Added QA-only POST /api/fcs/combine and Combine FCS dialog. Select 2–8 distinct original FCS completed analyses and an explicit common-gate template. Duplicate originals (by hash), nested combines, different organs and incompatible channel/compensation/fluorescence-transform layouts are rejected. Version-pinned transformed coordinate caches concatenate in source order; all common gates are evaluated against all events. Time transform differences are inverse-transformed and mapped to the template's Time scale; originals are unchanged. Caps: 2M events, 60M coordinates, 100M memberships, free disk reserve 1 GiB. Derived caches consume local disk; no new original FCS copies. Immutable edit_spec stores combine source run IDs/name; edit/delete operations retain combine lineage. Source ranges preserve file/hash/local event identity, hover shows original event and file, CSV exports pooled and per-source gate counts. Combined WSP export blocked explicitly; not represented as a single original sample. Existing single-sample export unaffected. Library lists recent 100 runs.
Verified actual Liver_146 (11:14:01 local analysis) + Liver_147 (10:41:00) yields 692819 events, 43 common gates, completed through UI. One older incompatible analysis attempt correctly failed and is retained as immutable history. Synthetic combine test covers pooled/source counts, deletion and channel incompatibility; 8 gate/export and 2 QA/HTTP tests passed. Original sources were read only.
Home Recent FCS files section is hidden by default and rendered only for username qa_admin, per user request; other QA accounts retain FCS Explorer access but no recent-file DOM content on Home. Mocked renderer validated qa_admin, other QA and regular account behavior. No commit/push.

## 2026-11-03 Combined WSP export
Combined FlowJo WSP export now supported for WSP-backed combines. Isolated fcs_combined_export creates a multi-sample WSP containing selected original FCS references and the final common gate tree on each sample. No concatenated FCS is created. Template compensation/transforms (including normalized Time) retained; source Keywords/event counts and unique sample/gate IDs assigned, unrelated sample/group definitions removed from the new copy. Original files/workspaces unchanged. Duplicate source filenames rejected to avoid ambiguous FlowJo relinking. Export independently reanalyzes every original FCS with generated WSP and compares every gate membership bit against the combined masks; failures prevent publication. Export timeout up to 15 minutes, derived validation files temporary. Existing immutable file library/mirror/audit publish path reused; UI offers WSP and each original FCS download. Combined export tested with Liver_146+147: 692819 events, 43 gates, all per-source membership masks exactly equal. Nine unit regression tests passed; actual FlowJo desktop verification still pending. Previous combined-export restriction superseded. No commit/push.

## 2026-11-03 Python scripts organized by function
All 32 application/deployment/test Python files moved into scripts packages: app (server/service), imports (facs/histology), statistics, fcs (analysis/storage/SMB/gates/combine/export), maintenance (backup), deployment (Mac mini/LAN), tests. Vendor xlrd remains vendor/ and is not application source. Shared scripts.paths.ROOT resolves the project root independently of cwd. Configuration, seed, data, uploads, caches, static assets and original research files retain their locations. Python commands now use package mode: `.venv/bin/python -m scripts.app.server`; test runner `.venv/bin/python -m scripts.tests.run` invokes both appropriate environments. FCS subprocesses use -m with project-root cwd. Root start.command and deploy shell launchers remain and call updated modules. Installed/generated server and backup launchd entries updated in place, keeping IP, network allowlist, port, schedule and data paths unchanged. Original code/plists backed up under backups/python-layout-* before migration. 48 main + 9 FCS tests passed after removing old source locations; server /api/me returned 200 with existing setup. Real combined worker re-execution validated package entrypoint. No original FCS/WSP/Excel modification and no git commit/push.

## 2026-11-03 JSON / CJS / TXT organization
Root JSON configuration and examples moved to config/: fcs_access.json, fcs_paths.json, import_profiles.json and *.example.json. Server QA allowlist, SMB mappings and spreadsheet profile readers updated. Machine-specific JSON stays gitignored at new paths. Root CJS tests moved to scripts/tests/js/ with relative static imports fixed. TXT dependency lists moved to requirements/requirements.txt and requirements/requirements-fcs.txt; start.command and installation docs updated. Original JSON/TXT hashes verified unchanged. Generated data/seed/results/backup manifests and third-party assets remain colocated with their data. 57 Python + 25 CJS tests passed, server restarted with unchanged network settings and returned 200, production QA IDs and SMB rules loaded from config. Source backup in backups/config-layout-*. No git commit/push.

## 2026-11-03 Archive initial roster and root spreadsheets
Moved seed/ intact to archives/seed/ and root XLSX files to archives/spreadsheets/ (Treg 36w DI combine_for Prism.xlsx, mouse info with histo mean.xlsx). All moved file hashes verified unchanged; no source overwrite. Existing DB drives normal site operation; archived roster JSON is still used only to seed an empty DB, and archived Mouse-info.xlsx still serves authenticated Original roster download. Server references and README updated, entire archives/ gitignored. No DB/analysis data move. Relevant 14 tests passed and restarted server returned HTTP 200. No commit/push.

## 2026-11-03 Automatic SMB backup
User explicitly chose smb://med.tu-dresden.de/ste/MK3/research/mk3-L15/AG Perakakis/Sungjoon/00. Backup. Added machine-local config/backup.json (gitignored), targeting its Mouse Sanctuary subfolder under mounted /Volumes/research. scripts.maintenance.smb_backup creates consistent SQLite + existing FCS asset bundle and adds content-addressed archives/config snapshots. Versioned complete manifests publish last after SHA-256 verification; no retention deletion, unchanged objects reused. External linked SMB FCS bytes remain excluded; provenance paths/hashes are retained and school-side backup remains necessary. Each transfer worker requires an actual smbfs mount, refuses out-of-mount destinations and is bounded to 30 minutes. Local snapshots retained on failure; unsent complete manifests retry hourly. Single-process lock prevents overlapping jobs. Status logs/backup-status.json, existing backup stdout/error logs. Existing backup launchd service now runs daily 03:00 local time, hourly retries/catchup and at login; deploy generator preserves this when config exists. No network exposure or credentials changes. First SMB snapshot completed 2026-11-03 15:38:58 Europe/Berlin. Restore command verifies hashes and SQLite integrity into a new destination only. Tests cover roundtrip, idempotent retry, corruption refusal, traversal rejection; FCS backup regression tests passed. See docs/backup-and-restore.md. No commit/push.
First production SMB bundle was restored into an isolated temporary directory: all 96 manifest entries verified, SQLite integrity_check=ok, 189 mice and 6978 measurements recovered, 217 external-source references retained. Restore test copy removed automatically; live data and SMB backup untouched. Unique backup payload ~2.68 GiB.

## 2026-11-03 Backups paused by user request
User wants to reorganize current data before any further backups. Unloaded and persistently disabled com.mouselab.backup via launchctl; verified no running backup process. Set config/backup.json enabled=false and added fail-closed guards to scheduled run (including --force) and SMB sender. Functionality retained, existing local/SMB backups retained without deletion. Do not create further backups or re-enable schedule without explicit user instruction. Application server remains running.

## 2026-11-03 Explorer display name
Renamed navigation, Home card/shortcut and UI guidance from FCS Explorer to FACS Explorer. File extension .fcs, internal API/module names and data unchanged. Backup remains disabled; no backup or commit performed.

## 2026-11-03 FACS label and navigation order
Display name shortened to FACS. Top navigation: Home, Import, Data, Graph, FACS, Audit History, User management. Existing role visibility and internal IDs unchanged. No backup or commit.

## 2026-11-03 Import preview and validation
Added scripts/imports/validation.py and authenticated editor POST /api/import/review. Full selected rows are checked read-only: exact mouse ID roster match, group/experiment/diet/week mismatches, new IDs with suggestions (never auto-correct), explicit allow-new registration + required group, duplicate full measurement keys inside file and DB, metric definitions, invalid values, blanks and timepoints. Review returns first 100 normalized observations and first 300 issues; total counts cover entire file. No preview-created mice/metrics/measurements. Successful review HMAC binds actor/upload/mapping and audit revision; /api/import revalidates inside BEGIN IMMEDIATE and rejects missing/stale review tokens. Other concurrent changes require re-review. Existing direct Store import remains usable for internal fixtures/migrations; HTTP always requires review. UI invalidates review after mapping changes, disables saving until successful validation. Existing FACS sheet/sample mapping supported. Upload itself still stores immutable pending original bytes before review; this is distinct from saving measurements. Four new tests + full suite (63 Python tests) passed. Isolated browser test verified duplicate-file/database/unknown-ID display, blocked save, and successful explicit new-ID registration. No production test data imported, originals unchanged, backup remains disabled. No commit/push.

## 2026-11-03 META Data / FACS Data import tabs
Import now has accessible META Data and FACS Data tabs with contextual guidance and separate CSV templates. META covers mouse metadata plus general measurements (still requires at least one measurement); FACS covers FlowJo summary XLS/XLSX or custom gate-result CSV. Raw .fcs/.wsp remain in FACS workspace. Tabs retain independent in-memory upload/mapping drafts, including values/checkboxes/reasons, and invalidate review tokens on switch; refresh does not restore unsaved drafts. Shared validation and atomic save unchanged. Upload/sheet operations block tab switches to avoid mixing asynchronous results. Browser isolated test confirmed FACS guidance, META draft preservation across round-trip, and validation still reports file/database duplicates and unknown IDs. No production data or backup changes, no commit.

## 2026-11-03 Metadata-only registration and experiment workspaces
META Data supports explicit metadata_only import with no measurement columns. Review requires mapped ID and Exp for new mice, explicit allow-new, and group (falls back to Diet when no Group supplied). Existing IDs are checked for metadata conflicts and never overwritten. Duplicate IDs in a metadata-only file are blocked. Creates mice and audited committed upload linkage, zero metrics/measurements. Later measurement/FACS-summary imports join the same exact Mouse ID. Added upload_mice association for future imports; experiment workspace also discovers historical upload provenance and measurement links.
Home Browse experiments opens Exp workspace (top menu order preserved). Lists mouse roster, committed source spreadsheets, QA-only associated FCS/WSP and analyses. FCS file links can target an experiment and optionally one of its mice; explicit link/unlink requires editor/admin, QA access and reason, with fcs_experiment_link audit. Unlink does not delete source files. Filename guessing is not used. WSP-only links do not pull every sample's analyses into an experiment. Combined analysis membership is discovered from linked source runs and may span experiments, noted in UI. Older analyses outside recent catalog page can still open.
New association tables only; original files untouched. Three experiment/metadata tests plus QA endpoint coverage added; all 66 Python tests passed. Isolated browser verified metadata-only save (one mouse, zero measurements), then Exp listing its mouse and source CSV. Production data not used for test imports. Backup remains disabled; no commit/push.

## 2026-11-04 Graph development priority
User feedback: FlowJo remains the team's FACS analysis tool. Keep the experimental FACS workspace limited to the existing QA accounts (stable IDs 1/2/3: qa_admin, qa_editor, qa_viewer); do not release it to other accounts. Prioritize Graph improvements for subsequent development. Existing FlowJo summary Count/Frequency/MFI import and graphing remain available to ordinary authorized users. Original FCS/WSP files and implemented analysis features are retained. Verified current allowlist against account IDs and passed scripts.tests.test_fcs_access (non-QA admins denied FACS endpoints, exports filtered, QA allowed). No application code change needed; no backup, commit or push.

## 2026-11-04 Windows transfer
User requested running the application on a Windows laptop with current data. Added start-windows.cmd (Python 3.12 launcher, Windows-local venv, localhost-only server, explicit existing-DB check) and docs/windows-transfer.md. Prepared a private transfer ZIP in the conversation outputs, using a read-only SQLite backup API snapshot and retaining local FCS assets/archives; this is a user-requested migration copy, not re-enabling backups. SMB external originals remain references; only the packaged path configuration uses the Windows UNC share. Mac data/config/server unchanged. Windows copy is independent, without synchronization. QA FACS analysis runtime is not installed by this launcher and remains unvalidated on Windows; Graph/Data/Import are the intended use. Do not claim native Windows execution was tested. No commit/push, no scheduled backup.

## 2026-11-04 Graph study tabs
Graph now opens By Week (basic-diet studies) or Dietary Intervention. Explicit experiment classification in config/experiment_types.json: Exp1/2/3/4/6/7/8/10 basic, Exp5/9 DI, including their Chow/Western controls. Unknown/QA experiments are omitted with a visible notice; classify future experiments in this config rather than guessing from each mouse's diet. Original mouse metadata remains unchanged (including blank DI weeks). Tab-specific panels retained in memory; saved presets include study tab. Available metrics, Exp/week filters, sample trees, figures, CSV and ANOVA use the tab scope; shared global mouse exclusion behavior unchanged. Statistical scope supports an explicit empty set and validates input. Browser isolated fixture verified Exp1 vs Exp9 and retention of DI Chow controls. Existing 66 Python tests passed, additional scope regression passed, and 18 chart tests passed. Original data untouched, backup disabled, no commit/push. Previously delivered Windows transfer ZIP predates these tabs.

## 2026-11-04 Add basic-diet controls to DI graphs
DI tab now offers explicit Exp/age/diet checkbox groups for basic-study Chow/Western controls; none added by default. static/study.js computes exact selected mouse IDs (deduplicated); basic tab ignores DI additions. DI experiments retain all their own controls. UI shows Added control on source Exp branches and summarizes chosen origins. Existing per-panel Exp/week filters remain applicable and are explained beside selection. Scope IDs flow to frontend plots/sample trees and validated backend ANOVA; empty scope remains empty. Graph data CSV includes experiment, weeks, study_tab and added_control. Shared presets save diControls; original classification/data untouched. No automatic compatibility matching or gate-definition merging. Synthetic UI verified selective Chow addition (DI 2 -> 3 mice), no unintended Western, basic tab stays 2, selection survives round trip. New regression coverage tests exact mouse scopes and exclusion effects. Full Python suite and 19 chart tests passed. No backup, commit or push; earlier Windows ZIP unchanged.

## 2026-11-04 Flexible Graph comparison replaces study tabs
Removed mutually exclusive study tabs and DI-only control picker. Graph defaults to all mice, including unclassified experiments. All experiments / Basic diet / Dietary Intervention are quick starting selections; the right-hand Comparison samples tree always lists all Exp -> Diet -> Mouse with active-metric data availability. Selecting branches or mice defines a shared exact mouse scope without altering global exclusions; scope changes clear per-panel Exp/week filters to avoid invisible restrictions (UI explains). Existing Global exclusions controls retain audited save behavior. Metrics remain available even outside scope. Custom selection persists in shared presets; older study/DI-control presets migrate in memory. Graph CSV now reports selection_mode and experiment_type plus Exp/weeks. Synthetic browser test verified DI selection -> add basic Exp and unclassified Exp, missing-data notices, and preset roundtrip; no console errors. Translated missing-label fallbacks to Not specified / Exp not specified / Diet not specified in graphs and statistics; legacy shared style alias retained. 19 chart tests and 7 statistical tests passed. Originals unchanged, no backup/commit/push; Windows ZIP remains older.

## 2026-11-04 Graph selection visibility
Added explicit Graph aria-pressed selected styling (dark neutral background/white text) plus Current selection status including Custom selection. Distinct hover and keyboard focus styles. Static changes only; no data modifications or backup.

## 2026-11-04 UI language and Edit History
Renamed Audit History navigation/page to Edit History (Korean: 변경 이력); internal audit API and immutable records unchanged. Added persistent per-browser English/Korean selector on login and workspace, dictionary-based translation for primary static UI, selected dynamic UI slots, fixed headers/buttons, placeholders and account edit labels. Scientific SVG labels, user input/data cells and raw history JSON remain original. QA FACS-specific text and some detailed dynamic messages are still English; do not claim exhaustive localization. Known legacy Korean system/import reason strings have exact display translations; original note remains expandable. Unrecognized Korean free-text notes remain unchanged with an original-note label. New account/preset automatic reasons are English. Language switch rerenders history; searches include localized reasons/actions. Test covers language persistence and preservation of arbitrary text. Isolated browser verified ko/en toggle, reload persistence, localized history and original notes; no errors. Full Python suite passed; no production data rewrite, backup or commit.

## 2026-11-04 Weekday idle-sleep prevention
User requested automatic sleep prevention only Monday–Friday 09:00–17:00. Removed the always-on caffeinate -is wrapper from installed/generated server LaunchAgents and deployment generator. Added scripts/deployment/workday_awake.py and com.mouselab.workday-awake LaunchAgent: runs at login, weekday 09:00 and every 60 seconds (no concurrent launchd instances), holds caffeinate -i with timeout to 17:00 and parent-PID lifetime guard only during that window. Uses Mac local timezone, presently Europe/Berlin CET. Display sleep allowed; does not schedule wake or force sleep at 17:00. Manual sleep unaffected. Outside hours follows macOS settings/other apps' assertions. Installer/stop scripts include scheduler for future deployments. Weekday/weekend/09:00/17:00 boundary checks passed. Verified live timed assertion expires at 17:00, server runs directly without caffeinate and HTTP responds after launchd replacement. Automatic backup still disabled. No research data changes or backup.

## 2026-11-05 Sleep prevention correction
User observed sleep during scheduled hours. pmset logs confirm 09:00 job began during DarkWake, followed by Maintenance Sleep at 09:03:31 and Sleep Service Back to Sleep at 09:20:10; full wake at 09:31:50 via HID. Idle-only -i did not cover these system sleep transitions. Changed scheduled caffeinate to -is (AC system sleep plus idle sleep), retaining 17:00 timeout and parent lifetime guard. Verified both assertions active with timeout to 17:00. Does not schedule a full wake at 09:00; no overnight/live sleep-cycle validation performed. No server/data/backup changes.

## 2026-11-05 Admin Login History
Added append-only login_history table (id, stable user_id if known, attempted username snapshot, outcome, UTC timestamp). Records successful/failed credential checks transactionally; failures commit before raising 401. HTTP rate-limited attempts record blocked. No password, token, IP or request body recorded. GET /api/login-history requires admin, returns newest 100 with cursor for older records. User management now contains bilingual Login History showing Europe/Berlin time; ordinary accounts denied server-side. Prior sessions are not backfilled and history is separate from data-edit revision. Three new unit/HTTP tests cover success/failure, unknown username, secrets absent, append-only, pagination, rename preservation, auth and rate limits. All 71 Python tests and i18n test passed; synthetic UI shows failed/successful attempts in both languages. Production records begin at deployment; research originals unchanged, no backup/commit/push.

## 2026-11-06 Graph 화면과 운영 배포

**개발과 운영.** 맥미니는 개발·검증용이며, 연구팀이 사용하는 운영 사이트는 [Mouse Sanctuary](https://nplab.alwaysdata.net/)다. 이전의 내부망 전용 기록은 11월 3일 당시 구성이다.

### Graph 선택 및 표시

- 그래프 수는 1–8개다. PNG와 SVG 내보내기는 빈 칸과 현재 조건에서 측정값이 없는 그래프를 건너뛰고 실제 그림만 배치한다. A–H 패널 문자는 원래 보드 위치를 따른다. 모두 비어 있거나 축 설정이 잘못되면 이유를 표시한다.
- Metric 팝업은 현재 비교 대상에 실제 수치가 있는 항목만 제공한다. 0도 측정값이다. 대분류를 세로로 나열하고 선택한 행 오른쪽에 다음 단계를 표시한다. 열 너비는 고정한다.
- Metabolic outcome은 Weight-timeline, Weight-endpoint, ITT, OGTT를 구분한다. Weight-timeline에서는 그룹별·주차별 체중의 평균선 또는 중앙값선을 선택할 수 있다. 초기값은 Off다. 전역 제외와 결측을 반영하며, 중앙값선을 선택해도 SD·SEM 오차 막대는 평균 기준이다.
- Histology는 장기 다음에 측정 항목이 바로 나온다. 예를 들어 Liver에서 HE (%) 또는 PSR (%)를 누르면 그래프에 적용한다.
- Flow cytometry는 장기 → 패널 → 마지막 gate 이름 → 측정 지표 순서다. 전체 gate 경로를 보존하며, 같은 장기·패널에 끝 이름이 중복될 때만 상위 경로를 덧붙인다. qPCR은 장기 → pathway → 유전자 순서다. Import에서 지정한 패널·pathway는 측정 항목 식별에 포함한다. 선택 경로와 저장 구조는 [Graph 분류 ERD](docs/database-erd.md#graph-metric-erd)를 참고한다.

### 오른쪽 설정 패널

- Comparison samples는 이번 그래프 보드의 비교 대상을 고른다. Global exclusions는 모든 지표에 적용할 마우스 제외·복원을 미리 보여주고, 사유와 함께 저장하면 다른 사용자에게도 적용되며 Edit History에 기록된다.
- Comparison samples, Graph settings, Global exclusions, Graph formatting, Shared presets는 기본으로 접혀 있다. 한 번에 하나만 열고, 오른쪽 메뉴 제목은 고정한 채 내용만 스크롤한다. 메뉴 전환 시 입력 중인 제외 사유를 유지한다. 제목은 16px 볼드이며 열린 메뉴는 더 진한 회색으로 표시한다.

### 배포 및 검증

- 운영 배포 커밋은 `9059926`이다. 배포 전 Python 테스트 36개와 JavaScript 테스트 32개가 통과했다. 운영에서 HTML·JavaScript·CSS 5개 파일이 배포본과 일치하고 로그인 상태 조회가 정상 응답하는 것을 확인했다.
- 두 개발 기기에서는 작업 시작 전 최신 main을 받는다. main에 푸시하면 GitHub Actions가 테스트 후 코드 전용 배포를 실행한다. 커밋 전 사용자에게 알리고, 운영 배포 요청 여부를 확인한다.
- 배포에는 `scripts/deployment/alwaysdata.py`의 허용 목록을 사용한다. 운영 DB, 계정, 업로드 원본, archives는 배포 대상에서 제외한다. 배포 설정과 검증 절차는 [GitHub 배포 문서](docs/github-deployment.md)를 참고한다.

## 2026-11-09 로컬 중복 사본 정리

사용자 요청으로 `archives/MouseSanctuary/data/fcs/`의 동일 파일 103개(3,520,922,266 bytes)를 현재 `data/fcs/`의 보존본을 가리키는 상대 심볼릭 링크로 교체했습니다. 전체 SHA-256을 전후 확인했습니다. 완료된 staging 13개는 변경 가능한 staging 경로 대신 해시 이름의 immutable objects를 참조합니다. 현재 원본·DB·독립 백업·앱 코드는 변경하지 않았으며 배포하지 않았습니다.

이전 `archives/MouseSanctuary/` 사본은 이제 독립 실행/이동용 완전 복사본이 아닙니다. 폴더만 따로 옮길 때는 링크 대상도 포함하거나 링크 대상의 내용을 실제 파일로 복사해야 합니다. 정리 기록과 자동 복원 스크립트가 있던 작업 공간의 `_maintenance/`는 같은 날 사용자 요청으로 삭제했습니다. 보존본과 상대 심볼릭 링크는 그대로 유지되며 삭제 후 모든 기존 링크의 대상이 존재하는지 확인했습니다.

## 2026-11-10 Guest Graph preview

로그인 화면의 Try Graph as a guest 버튼으로 브라우저 내 가상 데이터를 사용해 Graph를 체험한다. 예시는 48개 마우스의 FACS, 주차별 체중, Liver HE·PSR이다. 그래프 선택·서식·비교 샘플 필터·PNG/SVG/CSV 내보내기를 지원하며, 게스트 표시와 합성 데이터 표기를 유지한다. 게스트는 Graph 화면만 제공하며 서버 API 호출을 클라이언트에서 차단한다. 서버 인증 규칙은 기존 로직을 따른다. 로그인 화면으로 돌아가면 체험 상태를 초기화한다. 기존 예시 모드와 같이 p-value는 계산하지 않는다.

브라우저에서 입장, 4개 그림, 샘플 제외·복원 필터, PNG, 서식, 종료를 검증했다. 첫 로그인 상태 확인인 /api/me 외에 API 요청이 발생하지 않았고 JavaScript 테스트 32개가 통과했다. 개발본에 반영했으며 이번 작업의 커밋·운영 배포는 보류했다. 작업 시작 시 저장소 전체에 기존 파일 모드 변경이 있었으므로 후속 커밋에서 이를 함께 포함하지 않도록 검토한다.

## Graph browser drafts

Graph 설정은 localStorage의 버전 있는 키에 사용자 ID(없으면 username), 게스트, 실제/예시 모드를 구분해 자동 저장한다. 그래프 개수, 활성 탭, 패널 설정, 그룹 서식, 비교 대상, 저장 전 제외 변경과 사유를 복원한다. 서버 측 샘플 버전이 바뀌었거나 삭제된 대상의 제외 초안은 복원에서 제외하고 안내한다. 저장은 브라우저에 한정하며 Shared presets는 연구실 공유 용도로 유지한다. 저장소 사용이 차단되면 안내한다. 페이지 위치는 기존 sessionStorage로 복원한다. 브라우저에서 새로고침 후 개수·활성 탭·제목·오차 막대·추세선 복원을 검증했다. 이번 변경은 개발본이며 아직 배포하지 않았다.


## 2026-11-10 Security hardening and Graph follow-ups

- Existing accounts, password hashes, research data and immutable source files must remain intact. This change does not reset credentials, disable any real account, migrate the production schema, start backups, commit/push or deploy.
- Login throttling now reserves in-flight attempts and retains failed attempts only: per account 15 and per IP 30 within 5 minutes, bounded to 4096 keys. Successful attempts release their reservation. Blocked events are recorded once per account/window, not on every retry. Counters are process-local and reset on restart. Only `--alwaysdata` trusts the provider-replaced `X-Real-IP`; LAN deployments ignore forwarded headers. Do not expose that hosted backend directly to untrusted clients.
- Hosted responses include HSTS for one year (no includeSubDomains/preload). The user separately enabled Force HTTPS in alwaysdata. Server handles at most 8 concurrent requests; excess gets a retryable 503. Login/setup JSON limit 16 KiB, normal JSON 2 MiB, summary-upload JSON 15 MiB. One authenticated import operation at a time, including body decoding and workbook parsing; another request gets a retryable 503.
- Summary upload defaults: 10 MiB/file, 200 MiB total stored original blobs, 100 MiB/user, 20 MiB and 20 files pending/user, minimum 64 MiB free disk plus upload transaction headroom. These caps cover summary-upload blobs, not FCS assets or the full hosting account quota. Checks and insertion run in one transaction. Exact same-owner, same-name, same-hash pending reuploads reuse the original. No cleanup/deletion of existing originals, including pending or archived files. Over-limit existing installations retain access to data but cannot add files beyond quota. CSV row/column limits checked while parsing.
- User management has Disable/Enable access with mandatory reason, admin authorization, CSRF, stale-status protection and a self-disable guard. Disabled users cannot log in; sessions are revoked on disable. Status is derived from immutable `access_change` user events, so no schema migration is required. No existing user/event is changed on startup. Previously queued/in-flight work may finish; this is not cancellation of FCS jobs. Re-enable keeps the same password and requires a fresh login.
- My account offers explicit clearing of this account's browser graph drafts and signing out; other accounts' drafts, server data and Shared presets are retained. Ordinary sign-out retains drafts as previously requested.
- Summary Median now includes Mouse IDs. Odd N shows median-value mice; even N with distinct central values shows both central value populations marked midpoint. Equal central values show all tied mice rather than arbitrarily selecting one; missing/excluded mice follow existing filters.
- Graph header has one row of 3 selection + 5 export/example buttons, all 40px high. The redundant Graph heading is removed; current selection and counts form a compact status row. Number of graphs sits immediately after the three selection buttons. The first graph card and sidebar now start at the same height; long guidance lives in a collapsed Help panel. Confirmed alignment at desktop widths 1280 and 1778.
- Validation uses disposable DBs and synthetic browser data only. Full final Python suite: 73 main + 9 FCS tests passed, including request bounds, overload responses and account authorization. JS: 33 tests including median source edge cases. Browser checked account disable/restore, required reason, Korean labels, draft clearing, Median IDs and header layout. Follow-up production deployment still needs the existing code-only release workflow; include new scripts/app/security.py (already in allowlist). No production credentials/data were changed. The Mac development service was restarted and /api/me confirmed normal startup with existing accounts.


### White Liquid Glass UI follow-up

- User requested a subtle Liquid Glass treatment and compact layouts on other tabs. White/neutral translucent surfaces, restrained blur, rounded borders and shadows now apply to navigation, control panels, Home cards, upload/account forms and dialogs. Scientific graphs and data tables keep opaque white backgrounds; SVG/PNG rendering is unchanged. Solid fallback and reduced-transparency media rules are included.
- Graph toolbar padding now contains the full keyboard focus ring. Number of graphs remains next to the selection buttons, and chart/sidebar tops remain aligned. Desktop overflow is horizontal rather than wrapping individual toolbar actions.
- Import puts META/FACS tabs and template download on one row; detailed instructions are in Help. Data groups filters/search with export buttons; Edit History groups search/export with Help. Redundant Home/Import/Data/Edit History/User management titles are visually hidden but retained for assistive technology. Account creation controls align at 40px. FACS access rules and scientific tool layout remain unchanged.
- Browser checks with synthetic data verified main tab navigation, META/FACS tab switching, CSV preview, Median source labels, focus ring clearance and chart/sidebar alignment at 1440/1778 widths. No real imports or account changes were made. Changes are development-only until the normal code-only production deployment.

### 2026-11-10 Graph row alignment and glass refinement

- Latest placement supersedes the earlier left-side count selector: Number of graphs is now inside the right-hand preview/export group, immediately before the five action buttons. Its label/value and all five buttons use weight 700.
- Graph grid stretches each pair of cards to its row's tallest content; plot content sits at the card bottom. No fixed board-wide height. Browser verified eight plots at 1280/1440/1778 widths, including deliberately longer content in only one card: both cards in that row grow together, subsequent rows stay paired, and unrelated row heights remain unchanged.
- Shared shape tokens use capsule menu/action buttons, 24px outer panels, 16px inset controls and 14px form fields. Explicit study-button specificity keeps left/right shapes consistent. Apple design-system concepts are a reference, not a claim of native Liquid Glass rendering or an exact universal Apple corner-radius value (https://developer.apple.com/videos/play/wwdc2025/356/).
- More visible neutral glass surfaces now surround both Graph toolbar groups and the sidebar, with brighter edge highlights, gradients, blur and stronger soft shadows. Main navigation and dialogs retain glass treatment; scientific SVGs and tables stay opaque white. Reduced-transparency and no-backdrop-filter fallbacks remain. Focus rings retain full padding.
- Browser screenshot review confirmed the menu/sidebar appearance after compositor settling. No account, password, database, original file, scientific calculation, export format, commit or production deployment changes in this UI refinement.


### 2026-11-10 Viewport-fit Graph pairs and scroll snapping

- The Graph board now displays two cards per viewport-height row with native vertical scroll snapping and overscroll containment. Height derives from actual browser innerHeight and the board's document position, leaving an 18px bottom margin; no 1080px screen-size assumption. A 300px minimum protects very small windows. Scientific SVG viewBoxes scale proportionally to fit the remaining card area, including titles, p-value brackets, axes, labels and footers. Figure generation/export dimensions are unchanged.
- Sidebar maximum height uses the same available height. Fixed menu remains visible; long setting content scrolls internally. Summary and group formatting disclosures remain below the board in the outer page.
- Previous/next pair buttons and a visible Graph range indicator added beside Help. Wheel/trackpad snaps rows; focused board supports PageUp/PageDown and arrow keys. Selecting a sidebar Graph tab brings that pair into view. Once scrolling settles, settings follow the first graph in the visible pair if the previously active graph is outside it. Resize, view switching and rendering updates preserve/clamp the visible row. Reduced-motion preference skips smooth programmatic movement.
- Browser validated 1920x1080, 1920x927 (browser chrome allowance), and 1920x800; full chart/card/sidebar bounds fit. Tested 8 plots, odd count, count reduction, pair buttons, sidebar tabs, native wheel snap, long sidebar settings and leaving/returning to Graph. Synthetic fixtures only; no account/data changes or production deployment.

### Group formatting shape follow-up
The expanded Group colors/order/symbols section now retains the outer panel's rounded bottom corners and transparent glass background. Its six group cards use the shared 16px inset radius, matching borders and highlights, with sufficient inset padding for input focus rings. Form controls, reordering, stored graph settings and data are unchanged. Development CSS only; no deployment.

### Lower disclosure contrast
Group formatting and Summary now have a clearer 1px neutral border and short, restrained shadow. Their backgrounds are clipped to the rounded outer edge; expanded headers have a separator. Removed backdrop blur from these two containers to avoid a diffuse halo while keeping the rest of the glass theme. CSS only; data and deployment unchanged.

### Shared cross-tab controls
Applied the common capsule/rounded-control styling to native file-selector buttons (Import and QA FCS/WSP chooser), with a clear border, bold label, hover/focus/disabled states. File input IDs, accept/multiple attributes and upload behavior remain native and unchanged. Standardized action-button weights, input/table/dialog borders, status pills and uploaded-file rows across tabs. Native checkbox semantics and red import-validation outlines are retained. Development styling only.

### Stable navigation labels
Top navigation uses the same bold font weight in active and inactive states, with nonshrinking buttons. Selection is indicated through background/text color rather than width-changing typography. The document reserves a stable scrollbar gutter so moving between short and long pages does not shift the header horizontally. CSS-only change; navigation behavior and permissions unchanged.

### Metric label overflow
Graph-card and sidebar metric buttons now constrain long labels to their available width with ellipsis. Full label text remains in the DOM for accessibility and is also exposed through a title tooltip; the selection popup remains unchanged. Graph data and rendered/exported scientific titles are not abbreviated by this CSS.


### Data roster download correction
Removed the Data page's obsolete Original roster link to /api/source/seed, which is deliberately unavailable in hosted mode. Replaced it with explicitly labeled Mouse roster CSV, exporting the current loaded roster (ID, Exp, group, diet, weeks, notes, exclusion, version) through the existing escaped/BOM CSV helper. It is not presented as an original uploaded spreadsheet. Original source downloads remain under Original uploaded files. Hosted seed restrictions and production data are unchanged; code not deployed.


### 2026-11-10 Localized file controls and MASLD consolidation draft
- Native file input labels followed the OS language. Added localized visible labels around the original focusable inputs for summary and QA uploads, preserving accept/multiple/validation and native file selection. English/Korean switching, multiple filenames and explicit reset verified in a temporary browser with mocked API responses; no real upload/account change. Production not deployed.
- User authorized a consolidated workbook using Mouse-info.xlsx as authoritative roster: exactly IDs 1–183. User confirmed both Liver T Cell/Treg Count and Neutrophil counts are calculated Absolute Count, cells/µL.
- Added scripts/imports/polish_masld.py: read-only source extraction, exact-identity deduplication, source-cell provenance, percent-format normalization, explicit missing/zero distinction and review holds for uncertain IDs/units/dates/annotations. Original file SHA-256 checked unchanged. Does not connect to or write any DB.
- Exp 5/9 Gut sheets contain 540 duplicated measurements; all source locations retained. Copied material rosters in Exp 4/7/8/10 prevent reliable Pyret-ID mapping. Exp 13 outside the authoritative roster stays review-only. Do not infer IDs from row order or silently repair date years.
- Consolidated workbook is a review draft, NOT a file to import blindly through the current generic Import mapping. Long-format workbook import still needs integration after review. No production upload, backup, commit or push performed.

## 2026-11-10 — Gating 이미지 표시 복구
- Gating은 Graph와 독립된 탭. 원시 FACS의 QA 제한은 그대로 유지한다.
- 빈 화면 원인: 개발 서버가 변경 전 프로세스로 실행 중이었고 strategy 테이블/이미지가 미등록. com.mouselab.server를 재시작했다.
- masld_projectdata의 11개 XLSX 원본 바이트를 개발 DB strategy_sources에 보존하고 이미지 101개 occurrence를 strategy_images에 pending으로 등록했다. 미리보기 가능한 PNG/JPEG 10개가 목록에서 먼저 나온다. EMF/WDP 등은 원본 다운로드 안내를 표시하며 변환 지원으로 오인하지 않는다.
- 관리자만 미검토 이미지와 연결 정보 검토/승인을 볼 수 있다. 일반 사용자에게는 approved만 표시된다. Exp/organ/panel을 자동으로 확정하지 않았다.
- 등록 전후 기존 테이블 비교에서 events만 변경됐으며 측정값/계정은 변경되지 않았다. 원본 파일도 변경하지 않았다.
- Git에는 코드만 포함. data/, archives/, masld_projectdata/, outputs/ 연구자료는 제외. 운영용 데이터는 별도 인증된 직접 업로드를 사용하고 이번 작업에서는 운영 업로드/배포를 수행하지 않았다.
- strategy 단위검증, FCS 접근제어, 보안 회귀검증 총 13개 통과. 개발 서버 strategies.js 응답 200, 비로그인 API는 로그인 요구 확인.

### 2026-11-10 — Gating 화면 높이와 설정 배치
- 이미지 목록 / 전체 이미지 / 오른쪽 설정의 3열로 정리. 필터는 기본 펼침, 업로드·검토·원본 정보는 접이식으로 표시한다.
- 화면의 남은 높이에 맞추고 목록·설정은 각각 스크롤한다. 기본 이미지는 가로/세로 모두 맞춤, 확대 시 이미지 영역 내부만 스크롤한다.
- 긴 Zoom 슬라이더를 오른쪽 위 − / 비율 / + / Fit 버튼으로 교체. 이미지 선택 시 화면 맞춤으로 복귀한다.
- Chrome에서 1920×927 및 1920×1080 이미지/사이드바 하단과 이미지 너비가 영역 안에 들어가는지 검증. 확대·Fit·새로고침 복원 및 브라우저 오류 없음 확인.
- 프런트엔드만 수정. DB·원본·운영 배포 변경 없음.

### 2026-11-10 — Gating 목록 유지 및 드래그 이동
- 이미지 선택 등 재렌더 시 왼쪽 목록과 오른쪽 설정의 scrollTop을 복원한다.
- 확대 이미지 영역은 pointer capture 기반 클릭 드래그로 이동. 기본 브라우저 이미지 드래그를 막고 grab/grabbing 커서 제공. Fit 시 스크롤 원점 복귀, pointer cancel/capture 해제 처리.
- Chrome에서 30개 항목 목록의 스크롤 후 선택 위치 보존, 확대 후 X/Y 드래그 이동, 해제 및 Fit 복귀, 새로고침 확인. JS 문법 및 브라우저 오류 없음.
- 개발 DB 원본 이미지 SHA-256 읽기 전용 검사: 101 occurrence, 96 unique bytes. 미리보기 10 occurrence/7 unique. 내용 유사성 검사는 아니며 모든 이미지가 gating strategy라고 확정한 것이 아니다. 중복 원본/출처 삭제 없음, DB 수정/운영 배포 없음.

### 2026-11-10 — Unmapped media 목록 제외
- 사용자 요청으로 Gating 카탈로그 표시 시 anchor가 `Unmapped media;`로 시작하는 항목을 관리자/일반 사용자 모두 제외한다. 필터 옵션·이전/다음·총 개수에도 포함하지 않는다. 이후 업로드에도 같은 표시 규칙 적용.
- 현재 개발 DB 101개 중 48개 제외하여 53개 표시. 원본 Excel·이미지·검토 이력과 DB 레코드는 삭제하지 않았다. 운영 배포 없음.

### 2026-11-10 — Metabolic 이미지 목록 제외
- Gating 표시에서 `Metabolic Biochemical outcomes` 시트도 제외. 대소문자 및 공백 차이를 정규화하며 향후 업로드에도 적용한다. 기존 Unmapped media 제외와 함께 목록·필터·개수에 반영.
- 현재 53개 중 41개 추가 제외, 12개 표시. 원본 및 DB 변경 없음. 운영 배포 없음.

### 2026-11-10 — Neutrophil 제외 및 메뉴 순서
- Gating 표시에서 Neutrophil panels도 제외. 기존 제외 규칙과 합쳐 현재 7개 표시, 원본·DB 보존.
- 메뉴를 Home → FACS → Gating → Import → Data → Graph → Edit History → User management로 정렬. 기존 FACS QA 접근 제한 및 관리자 메뉴 표시 조건 유지. 운영 배포 없음.

### 2026-11-10 — 개발용 통합 데이터 테스트 Import
- 명시적 사용자 요청으로 QA-001~004, QA-UI-001~002를 전역 제외 처리(삭제 아님). 기존 연구 mouse 제외 상태는 유지, 따라서 roster 총 189는 보존된다.
- `scripts/imports/import_consolidated.py`: 기본 dry-run 전체 트랜잭션 롤백, --apply는 정확한 개발 DB 경로만 허용. 통합 XLSX를 읽고 원본 바이트 및 provenance를 upload에 보존. 파일 해시 기반 중복 실행 차단, 기존 관측값 충돌은 보류. 단위/숫자/roster 검증, 사용자 및 각 변경 audit 기록.
- 통합 workbook SHA256 904cc63cfdc2312275da423c4702dfe2ca8c85cd33c790c61eccb0ad31965df8. 183마리 Exp/diet/weeks 갱신, diet 설명·feeding schedule·원래 group 등은 source metadata에 보존. 기존 표시 group_name은 유지.
- ready 9,374 중 기존 동일 키/값 128 건너뜀, 9,246 추가. review 5,821 및 missing 16은 원본 workbook에 보존하고 입력 보류. MFI Geometric Mean은 기존 명명 방식 Geometric Mean으로 정규화, 형광강도에 분모 비해당 명시. panel/전체 gate 경로 및 원본 header 보존.
- 기존 6,978 관측값·계정 전체가 변경되지 않았음을 확인. 최종 관측값 16,224, metric 317. SQLite integrity/foreign_key_check 통과, snapshot에 신규 9,246 노출 확인.
- 상세 보고서 data/consolidated-test-import-report.json (Git 제외). 연구 데이터·원본은 Git에 올리지 않음. 운영 접속·배포·데이터 업로드 수행하지 않음. 자동 백업은 실행하지 않음.

### 2026-11-10 — QA 6마리 현행 데이터에서 보관 처리
- 사용자 재확인에 따라 전역 제외에 그치지 않고 QA-001~004, QA-UI-001~002 및 측정값 24개를 현행 mice/measurements에서 제거했다.
- 삭제 전 전체 행과 업로드 연결/상태를 qa_retired_data JSON에 보존. QA 전용 업로드는 남은 관측값/roster 연결이 없을 때만 archived로 표시, 원본 바이트는 유지. 변경 이력 기록.
- 현행 mice 183, measurements 16,200. snapshot에서 QA mouse/관측값 0 확인. 연구 측정값 전체와 계정이 변경되지 않았으며 외래키 검사 통과. 운영 서버 변경 없음.

### 2026-11-10 — 운영 데이터 직접 교체 및 CI 테스트 수정
- 사용자 승인 범위: 기존 운영 연구 데이터를 정리된 통합 데이터로 교체, GitHub에는 데이터 업로드하지 않음. SSH nplab_actions 키로 직접 전송. 계정/비밀번호는 보존.
- 운영 기존 183마리·2,236관측값을 retired_research_data 압축 JSON에 보관하고 현행 관측값을 통합 파일 ready 9,374개로 교체. 개발에서 중복으로 제외한 128개도 새 데이터에 포함. 연구 roster 183, QA 0, active source upload 1. 기존 원본 uploads는 archived 상태로 바이트 보존. 계정 10개 전체 행 변경 없음.
- 통합 Excel SHA256 904cc63cfdc2312275da423c4702dfe2ca8c85cd33c790c61eccb0ad31965df8. 239개 사용 metric, review 5,821 및 missing 16은 입력 보류하고 원본 workbook에 보존. 개발의 연구 mouse 제외 상태는 roster와 함께 유지. 미검토 strategy image 101개와 원본 source를 이전했으나 UI의 제외 규칙/승인 조건은 그대로 적용되며 새 코드 배포 후 표시 가능.
- 운영 교체 전 롤백 검증 후 단일 트랜잭션 적용, foreign_key/integrity 검사 및 snapshot 183/9,374 확인. 전송 패키지에는 계정/세션 테이블 없음. 임시 원격 전송 파일 제거. 운영 DB 전체 덮어쓰기/자동 SMB 백업 없음.
- 66dff2a Actions test 실패를 로컬 동일 명령으로 재현: test_i18n.cjs 가상 document에 addEventListener가 없었음. 이벤트 listener/dispatch 및 Event.type을 보완. Python 30개, JS 26개 통과; code-only deploy package preview 통과. Node20 메시지는 경고이며 재현된 실패 원인이 아님.
- 수정된 테스트는 아직 커밋/푸시하지 않음. 자동 배포는 수정본 push 후 재시도 필요. 데이터 반영과 코드 배포는 별개.

### 2026-11-10 — Home 명부 및 측정값 보유 수 구분
- Home 첫 줄에 Total mice / Mice with measurements / Mice without measurements 3개 카드 표시. 고유 roster ID 기준, 유한 숫자 측정값이 하나 이상 있는 마우스를 집계하며 0 포함·NULL 제외·반복 측정 중복 집계 없음.
- 기존 Experiments/Metrics/Recorded values는 둘째 줄에 유지. 한영 번역 제공. 데이터에서 동적으로 계산하며 183/134/49를 하드코딩하지 않음.
- 183/134/49 fixture와 0·반복값·결측값 확인, JS 문법 검증 통과. 코드만 변경, 운영 DB 변경 없음. 커밋/푸시/배포는 수행하지 않음.

### 2026-11-10 — 날짜형 Body weight 추세선
- 원인: 통합 Body weight timepoint가 ISO 날짜인데 기존 Weight-timeline 분류/line 렌더는 숫자 주차만 허용했다. ISO 날짜를 timeline의 dated view로 분류하고 실제 날짜 간격으로 X축 표시, numeric week와 date는 분리하여 처리한다. 임의 실험 주차 변환 없음.
- Weight-timeline 선택 시 Mean 기본, Body weight trend에서 Mean/Median/Off 전환. weightAxis를 panel draft/config에 보존. 기존 endpoint 및 numeric week 기능 유지. 날짜축 라벨은 간격을 줄여 중첩 방지, 원본 시점은 모두 유지.
- 실제 개발 체중 1,208개/59시점을 Mean/Median/Off 각각 렌더 확인. 날짜 유효성, endpoint 분리 및 중앙값/평균 구분 회귀검증 추가. JS 27개 통과. 데이터/운영 변경, 커밋/푸시 없음.

### 2026-11-10 — 체중 타임라인 Exp 분리 및 가독성
- 사용자 확정: 달력 날짜 유지, Exp별로 보기. 체중 line 선택/기존 빈 Exp draft 복원 시 첫 데이터 보유 Exp를 초기 선택하며 우측 Experiment에서 변경 가능. 여러 Exp를 동시에 묶으려 하면 안내문으로 차단, 날짜를 상대 주차로 변환하지 않음.
- 체중 line 개체 점은 기본 숨김, Show individual body weights 토글로 표시. Mean/Median/Off 유지, Median 모드 중심 표식은 median 위치. SEM/SD 오차막대는 기존대로 평균 기준이며 footer에 Mean ± SEM/SD 표기.
- 범례를 가용 폭에 따라 여러 줄로 배치하고 SVG 높이 확보, 부제에 Exp 표시.
- 실제 Exp2/3/6 각각 렌더 확인, 혼합 Exp 차단 및 개체 점 토글 회귀 테스트 포함 JS 28개 통과. 원본/DB/운영 배포 변경 없음.

### 2026-11-10 — 체중 날짜 눈금과 점 정렬
- 기존 날짜 라벨 일부 생략으로 점/날짜 대응이 불명확했다. 모든 실제 측정 날짜에 눈금 표시, 날짜 글자만 가용 픽셀 간격에 맞춰 생략. 실제 날짜 간격은 유지.
- line 개체 점의 가로 jitter 제거하여 측정일 X좌표에 정확히 정렬. 그룹 중심점에 날짜·Mean/Median·값·N 툴팁, 개체 점에도 날짜 추가.
- 날짜 눈금 수와 실제 점 X좌표 일치 테스트 포함 chart 28개 통과. 데이터 수정/운영 배포 없음.

### 2026-11-11 — 탭 시작 영역 통일
- Home의 소개 문구를 제거하고 집계 카드로 시작, Refresh overview는 Workspace 작업 버튼 옆으로 이동.
- Import/Data/Graph/Edit History는 작업 toolbar를 상태·Help보다 앞에 배치. Import의 동적 설명은 Help 안에 유지. User management는 사용자 추가 폼부터, FACS는 도구 ribbon부터 시작하고 QA 상태는 바로 아래에 유지.
- Experiments 일반 소개와 사용자 관리 소개 제거, 반복 제목은 접근성용 sr-only로 유지. 필드 설명·오류·파일 제한·출처 정보는 삭제하지 않음.
- 기존 element ID 및 개수 유지 확인. Chrome에서 Home/Import/Data/Graph/Edit History 이동, 한영 파일 선택 표시, 소개 숨김 및 화면 캡처 확인. 데이터/계정/운영 배포 변경 없음.

### 2026-11-11 — Data/Edit History 곡률 통일
- 큰 카드의 공통 24px radius-panel은 유지하고 Data 표/History 이벤트/Graph 카드에 동일 기준 명시.
- 차이가 남아 있던 page-toolbar의 한 줄 검색창·선택창을 Graph 작업 버튼과 같은 radius-pill로 통일. 텍스트 영역·표 내부 셀·기능은 변경하지 않음.
- 운영 배포 및 데이터 변경 없음.

### 2026-11-11 — 공통 작업 메뉴 그룹 및 FACS 카드
- Import META/FACS 탭, Data 검색/종류 선택 및 내보내기 버튼 그룹에 Graph 상단과 같은 CSS 규칙을 공유하여 padding·곡률·배경·테두리·그림자를 일치시켰다.
- FACS 전체 페이지의 구형 직사각 외곽 border 제거. 도구 ribbon 및 sidebar/main 작업 영역은 공통 radius-panel로 분리, 내부 스크롤/도구 기능 유지.
- Chrome에서 Import/Data/FACS 캡처 및 곡률·외곽 border 확인, 기존 탭 이동/한영 파일 선택 테스트 통과, 브라우저 오류 없음. DB·QA 권한·운영 배포 변경 없음.

### 2026-11-11 — 상단 작업 메뉴 기준선 정렬
- Graph에만 남아 있던 8px 상단 padding 및 다른 좌우 음수 margin을 page-toolbar와 공통 규칙으로 통일.
- Import/Data/Graph 그룹 외곽 높이 58px, radius 28px, 내부 padding 8px. Graph 내부 탭 border를 제거해 외곽 곡선 시작/끝 높이를 맞춤.
- Chrome 1920×1080에서 Import/Data/Graph 외곽 좌표 모두 x=92,y=95,height=58 확인. 탭 이동/파일 선택/언어 전환 검증 통과. 운영 배포·DB 변경 없음.

### 2026-11-11 — Help 공통 위치
- 모든 page의 Help를 페이지 기준 우측 상단(top:-22px,right:0) 여백에 배치하여 메뉴 시작 높이는 그대로 유지. 펼친 도움말은 같은 오른쪽 기준으로 열리며 긴 내용은 내부 스크롤.
- Home/Experiments/Gating/FACS에도 해당 작업용 Help 추가. 기존 Graph/Import/Data/History/Users 설명 및 동적 안내 ID는 유지.
- Chrome에서 주요 8개 탭 모두 summary 위치 x=1209.28125,y=73 일치, 펼침/닫힘 및 기존 파일 선택·언어 전환 확인. 운영 배포/DB 변경 없음.

### 2026-11-11 — Liquid Glass Help 튜토리얼
- 페이지 사이에 끼어 있던 Help는 숨기고 상단 계정 영역의 공통 Help 버튼으로 대체. 기존 동적 안내 DOM ID는 보존.
- static/tutorial.js: 현재 탭별 단계 안내(한국어/영어), 화면 전체 glass blur overlay와 강조 대상의 선명한 spotlight, 이전/다음/완료/닫기 및 Esc. 실제 입력·업로드·gate 수정·저장 동작을 실행하지 않음. 숨김/없는 대상은 건너뜀.
- native modal dialog로 배경 상호작용/포커스 제한, 종료 시 원래 버튼 포커스/문서 스크롤 복원. resize/scroll 시 위치 갱신, reduced motion/transparency 지원. 기존 dialog backdrop blur는 튜토리얼에서 해제해 대상까지 흐려지는 문제 방지.
- Chrome 1920×1080에서 8개 탭 순회, 안내 카드 화면 내 배치, 다음/이전, Esc, 포커스 복원, 한국어 및 API 쓰기 요청 0 검증. 실제 캡처 검토 완료. 배포 allowlist 및 정적 라우트 추가, 패키지 preview 통과. 개발 서버 재시작, 운영 배포/DB 변경 없음.

### 2026-11-11 — Tutorial spotlight refinement
- Reduced surrounding blur to 2px and retained blur-free dialog/backdrop so highlighted controls stay readable.
- Spotlight corner radii now follow each target computed corner radius plus the 6px outer gap, instead of a fixed 20px radius. Percentage/pill radii resolve against target dimensions.
- Asset query versions refreshed. Development UI only; no production deployment or database changes.

### 2026-11-11 — Clearer grouped menu edges
- Header navigation and shared Graph/Import/Data toolbar groups use a darker neutral border and a short contact shadow plus soft outer shadow. Preserved 1px border thickness, dimensions, corner radii and selected states.
- Development CSS only; no database or production changes.

- Follow-up: confirmed live development server serves grouped border rules; increased edge contrast to #8997a5 and contact/outer shadow opacity for visibility on Graph white background. Cache version glass-edge-5.

- Clarification: user meant the inner Data fields versus Graph comparison buttons, not outer group borders. Matched unselected Graph comparison button border (#bac2ca) and inset shadow to Data fields; selected dark state preserved.

### 2026-11-11 — Graph toolbar shadow clipping fix
- Root cause: graph-toolbar overflow-x:auto implicitly made overflow-y:auto, clipping group shadows at a rectangular scroll container edge. Changed toolbar to overflow:visible and flex-wrap:wrap so narrow desktop layouts wrap control groups without clipping shadows. Border styling unchanged. No database/production changes.

### 2026-11-11 — Main navigation drag selection
- Added pointer drag preview to the top navigation; glass indicator follows pointer, destination commits on release using existing navigation/permission handlers. Ordinary click and keyboard activation preserved. Hidden/disabled tabs excluded; Escape, pointer cancellation, resize and leaving the navigation cancel selection.
- Browser checks passed for click, drag preview without early navigation, release navigation, Escape and keyboard; no API writes/browser errors. Development only, no deployment or data changes.

### 2026-11-11 — Click navigation slide
- Main navigation now has one animated selected pill; clicking/keyboard navigation slides its position and width to the active tab (260ms). Drag preview remains separate; hidden tabs, resize and translated labels resynchronize geometry. Reduced-motion disables animation.
- Chrome verified active CSS transition and final target alignment, plus click/drag/Escape/keyboard regression checks. No data or production changes.
