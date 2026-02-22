# pg-here

[![PyPI](https://img.shields.io/pypi/v/pg-here)](https://pypi.org/project/pg-here/)
[![Downloads](https://img.shields.io/pypi/dm/pg-here)](https://pypi.org/project/pg-here/)
[![CI](https://github.com/jinto/pg-here/actions/workflows/python-package.yml/badge.svg)](https://github.com/jinto/pg-here/actions/workflows/python-package.yml)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/pg-here)](https://pypi.org/project/pg-here/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

명령어 하나로 프로젝트 폴더에 로컬 PostgreSQL을 실행하세요.

```bash
uvx pg-here
```

끝. Docker도, Homebrew도, 시스템 설치도 필요 없습니다. PostgreSQL이 프로젝트 안의 `./pg_local/`에서 실행되고, Ctrl+C로 깔끔하게 종료됩니다.

> **Python 포팅** — [pg-here](https://github.com/mayfer/pg-here) (Node.js, [@mayfer](https://github.com/mayfer))에서 영감을 받았습니다.
> 같은 컨셉, 독립적 구현 — `uv`/`uvx` 생태계를 위해 Python으로 처음부터 새로 작성했습니다.

[English README](README.md)

## 왜 필요한가?

로컬 개발 환경에서 PostgreSQL 셋업은 번거롭습니다:

| 방법 | 문제점 |
|------|--------|
| **Docker** | 무겁고, 시작 느리고, 데몬 필요, 포트 매핑 번거로움 |
| **Homebrew / apt** | 시스템 전체 설치, 프로젝트 간 버전 충돌 |
| **클라우드 DB** | 네트워크 지연, 비용 발생, 오프라인 불가 |
| **바이너리 직접 설치** | 다운로드, 압축 해제, initdb, pg_ctl, 설정... 매번 반복 |

pg-here는 이 모든 과정을 명령어 하나로 해결합니다. 프로젝트마다 독립된 PostgreSQL 바이너리와 데이터 디렉토리를 사용합니다. 충돌 없음. 설정 없음.

## 주요 기능

- **명령어 하나**: `uvx pg-here` — 그 외 아무것도 필요 없음
- **설정 불필요**: 합리적인 기본값, 바로 동작
- **프로젝트별 격리**: 데이터가 `./pg_local/`에 저장, gitignore 가능
- **자동 다운로드**: 첫 실행 시 PostgreSQL 바이너리 자동 다운로드 (~30MB)
- **즉시 재시작**: 바이너리가 캐시되어 이후 실행은 수 초 내 시작
- **pg_stat_statements**: 쿼리 성능 분석을 위해 사전 구성
- **Python API**: 테스트와 스크립트에서 라이브러리로 사용 가능
- **크로스 플랫폼**: macOS (Apple Silicon & Intel), Linux (x86_64 & ARM64)
- **깔끔한 종료**: Ctrl+C로 PostgreSQL 정상 종료

## 설치

```bash
# 설치 없이 바로 실행
uvx pg-here

# 또는 전역 설치
uv tool install pg-here

# 또는 프로젝트에 추가
uv add --dev pg-here
```

Python 3.10 이상과 [uv](https://docs.astral.sh/uv/)가 필요합니다.

## 사용법

### 빠른 시작

```bash
uvx pg-here
```

출력:

```
PostgreSQL 17.4.0 running on port 55432

  psql postgresql://postgres:postgres@localhost:55432/postgres

Press Ctrl+C to stop.
```

연결 문자열을 복사해서 아무 PostgreSQL 클라이언트에서 사용하면 됩니다.

### 데이터베이스 지정

```bash
uvx pg-here -d myapp
```

`myapp` 데이터베이스가 없으면 자동으로 생성합니다.

### 전체 옵션

```
Usage: pg-here [OPTIONS]

Options:
  -u, --username TEXT   PostgreSQL 슈퍼유저 이름 (기본값: postgres)
  --password TEXT       연결 문자열용 비밀번호 (기본값: postgres)
  --port INTEGER        포트 번호 (기본값: 55432)
  -d, --database TEXT   데이터베이스 이름 (기본값: postgres)
  --pg-version TEXT     PostgreSQL 버전 (예: 17.4.0)
  --help                도움말 표시
```

### 프로젝트에서 사용

`pyproject.toml`에 추가:

```toml
[dependency-groups]
dev = ["pg-here"]
```

그리고:

```bash
uv run pg-here
```

### 앱에서 연결

```python
import psycopg

conn = psycopg.connect("postgresql://postgres:postgres@localhost:55432/myapp")
```

```bash
psql postgresql://postgres:postgres@localhost:55432/myapp
```

### Python API

테스트나 스크립트에서 프로그래밍 방식으로 사용:

```python
from pg_here import start_pg_here

# 로컬 PostgreSQL 인스턴스 시작
handle = start_pg_here(port=55432, database="myapp")
print(handle.connection_string)
# postgresql://postgres:postgres@localhost:55432/myapp

# 추가 데이터베이스 생성
handle.ensure_database("testdb")

# 다른 데이터베이스의 연결 문자열 가져오기
uri = handle.connection_string_for("testdb")

# 완료 시 종료
handle.stop()
```

#### pytest fixture 예제

```python
import pytest
from pg_here import start_pg_here

@pytest.fixture
def pg(tmp_path):
    handle = start_pg_here(project_dir=tmp_path, port=0)  # 0 = 자동 포트
    yield handle
    handle.stop()

def test_my_app(pg):
    conn = psycopg.connect(pg.connection_string)
    # ...
```

## 동작 원리

```
uvx pg-here
    │
    ├─ 1. Maven Central(Zonky)에서 PostgreSQL 바이너리 다운로드
    ├─ 2. ./pg_local/bin/17.4.0/ 에 압축 해제
    ├─ 3. initdb → ./pg_local/data/ 에 데이터 클러스터 초기화
    ├─ 4. pg_ctl start → 포트 55432에서 PostgreSQL 실행
    ├─ 5. 데이터베이스 생성 + pg_stat_statements 설치
    └─ 6. Ctrl+C 대기 → pg_ctl stop (정상 종료)
```

모든 파일은 `./pg_local/` 아래에 저장됩니다. `.gitignore`에 추가하세요:

```
# .gitignore
pg_local/
```

### 디렉토리 구조

```
your-project/
├── pg_local/              ← pg-here가 생성 (gitignored)
│   ├── bin/17.4.0/        ← PostgreSQL 바이너리 (캐시됨)
│   │   ├── bin/
│   │   ├── lib/
│   │   └── share/
│   └── data/              ← 데이터베이스 클러스터
│       ├── PG_VERSION
│       ├── postgresql.conf
│       └── ...
└── ...
```

## 비교

| | pg-here (Python) | pg-here (Node.js) | Docker Postgres | Homebrew |
|---|---|---|---|---|
| 명령어 하나 | `uvx pg-here` | `bunx pg-here` | `docker run ...` | `brew install` + 설정 |
| 프로젝트별 격리 | Yes | Yes | 볼륨 마운트 | No |
| 데몬 불필요 | Yes | Yes | No (Docker 데몬) | No (brew services) |
| 첫 실행 이후 오프라인 | Yes | Yes | 이미지 필요 | Yes |
| Python API | Yes | No | No | No |
| 크기 | ~30MB 바이너리 | ~30MB 바이너리 | ~400MB 이미지 | ~100MB |

## 감사의 말

- [pg-here](https://github.com/mayfer/pg-here) (Node.js, [@mayfer](https://github.com/mayfer))에서 영감을 받았습니다. 독립적인 Python 구현이며, 코드를 복사하지 않았습니다. 같은 비전을 공유합니다: 모든 프로젝트를 위한 원커맨드 로컬 PostgreSQL.
- [Zonky embedded-postgres-binaries](https://github.com/zonkyio/embedded-postgres-binaries) (Apache 2.0)를 통해 Maven Central에서 사전 빌드된 PostgreSQL 배포판을 사용합니다.

## 라이선스

MIT
