# Mouse Sanctuary — Database ERD

Verified against the running app's SQLite schema on 2026-11-03. Database: `/Users/paul/WorkInProgress/nplab_mouse_web/data/lab.sqlite`.

```mermaid
erDiagram
    users o|--o{ sessions : authenticates
    users o|--o{ uploads : owns
    users o|--o{ events : performs
    mice ||--o{ measurements : has
    metrics ||--o{ measurements : defines
    uploads o|--o{ measurements : supplies

    users {
        INTEGER id PK
        TEXT username UK
        TEXT password "PBKDF2 hash, not plaintext"
        TEXT salt
        TEXT role "admin or editor"
        TEXT created_at
    }
    sessions {
        TEXT token PK "SHA-256 of session token"
        INTEGER user_id FK "nullable in schema"
        TEXT csrf
        REAL expires "Unix timestamp"
    }
    mice {
        TEXT mouse_id PK
        TEXT group_name
        TEXT experiment
        TEXT weeks
        TEXT diet
        TEXT note
        INTEGER excluded "global inclusion state"
        INTEGER version "optimistic concurrency"
        TEXT source "provenance JSON"
    }
    metrics {
        INTEGER id PK
        TEXT identity UK "canonical metric definition JSON"
        TEXT name
        TEXT unit
        TEXT organ
        TEXT gate
        TEXT parent_gate
        TEXT denominator
    }
    uploads {
        TEXT id PK
        TEXT filename
        TEXT sha256
        BLOB original "immutable uploaded bytes"
        INTEGER owner FK "nullable in schema"
        TEXT created_at
        TEXT status "pending or committed"
        TEXT mapping "nullable JSON"
    }
    measurements {
        INTEGER id PK
        TEXT mouse_id FK
        INTEGER metric_id FK
        TEXT timepoint
        TEXT replicate
        REAL value "nullable; zero is a measured value"
        TEXT missing_reason
        INTEGER version
        TEXT upload_id FK "nullable"
        INTEGER source_row "nullable"
    }
    events {
        INTEGER id PK
        INTEGER actor FK "nullable in schema"
        TEXT action
        TEXT entity "logical target table/type"
        TEXT entity_id "logical target ID, not FK"
        TEXT before_json "nullable"
        TEXT after_json "nullable"
        TEXT reason
        TEXT created_at
    }
    presets {
        INTEGER id PK
        TEXT name UK
        TEXT config "graph configuration JSON"
        INTEGER version
        TEXT updated_at
    }
```

## Constraints and interpretation

- `measurements`: UNIQUE (`mouse_id`, `metric_id`, `timepoint`, `replicate`). Each mouse may have many metrics/gates and timepoints, with explicit replicate identifiers.
- Foreign-key lines above represent actual SQLite constraints. Optional parents reflect nullable foreign-key columns, even where normal application writes supply a user/upload ID.
- `events.entity` + `entity_id` reference targets logically; they are not enforced foreign keys. Audit events can describe users, imports, measurements, mice and presets.
- `presets` is a shared, independent table. Metric IDs and formatting are stored in `config` JSON, without SQL foreign keys.
- Exp, diet, organ and gate have no separate tables. Exp/diet are fields on `mice`; organ/gate are fields on `metrics`.
- Triggers prevent UPDATE/DELETE on `events`, UPDATE of `uploads.original`/`sha256`, and DELETE of `uploads`. Observation edits are versioned and audited by the application.
- Usernames can change without changing `users.id`; uploads and audit authors remain linked to that ID. Audit listings join the current username; rename events preserve the previous and new usernames.
- Password changes store a fresh salt and PBKDF2-HMAC-SHA256 hash, revoke all sessions for that user, and log the change without passwords/hashes/salts. The schema itself does not change for the account update.

## 한국어 설명

8개 테이블: 계정(users), 로그인 세션(sessions), 마우스 명단(mice), 측정 정의(metrics), 원본 업로드(uploads), 관측값(measurements), 변경 이력(events), 공유 그래프 서식(presets).

한 마우스의 여러 organ/gate 값은 서로 다른 metric의 관측값으로 저장합니다. 결측은 NULL로 저장하며 0과 구분합니다. 전역 제외는 mice.excluded에 저장하므로 원본 측정값은 삭제하지 않습니다.

## FCS extension (2026-11-03)

The original eight tables are retained. Three additional tables bring the current total to eleven. Files and per-event arrays are kept outside SQLite and must be included in backup bundles.

```mermaid
erDiagram
 users ||--o{ fcs_transfers : uploads
 users ||--o{ fcs_files : owns
 users ||--o{ fcs_runs : analyzes
 fcs_files ||--o{ fcs_runs : source_fcs
 fcs_files o|--o{ fcs_runs : source_wsp
 mice o|--o{ fcs_runs : linked_mouse
 fcs_transfers {
  TEXT id PK
  INTEGER owner FK
  TEXT filename
  INTEGER size
  INTEGER received
  TEXT created_at
  TEXT file_id "logical completed file ID; nullable"
 }
 fcs_files {
  TEXT id PK
  INTEGER owner FK
  TEXT filename
  TEXT kind
  INTEGER size
  TEXT sha256 "content-addressed original and local mirror"
  TEXT created_at
  TEXT note
 }
 fcs_runs {
  TEXT id PK
  INTEGER owner FK
  TEXT fcs_id FK
  TEXT wsp_id FK "nullable"
  TEXT mouse_id FK "nullable"
  TEXT organ
  TEXT status
  TEXT created_at
  TEXT finished_at "nullable"
  TEXT error "nullable"
  TEXT result "nullable JSON; gate definitions/counts, source hashes and artifact directory"
 }
```
