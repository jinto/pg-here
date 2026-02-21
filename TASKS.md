# pg-here (Python) — uvx pg-here

> 목표: `uvx pg-here` 한 줄로 현재 프로젝트 폴더에 로컬 PostgreSQL 인스턴스를 실행.
> 원본: https://github.com/mayfer/pg-here (TypeScript/Node.js)

## 아키텍처 개요

```
uvx pg-here
    ↓
CLI (click) → startPgHere()
    ↓
BinaryManager: PostgreSQL 바이너리 다운로드/캐시
    ↓
InstanceManager: initdb → pg_ctl start → DB 생성 → 대기
    ↓
사용자에게 연결 정보 출력, Ctrl+C로 graceful shutdown
```

### 핵심 설계 결정

1. **바이너리 소스**: Zonky embedded-postgres-binaries (Maven Central)
   - 신뢰성 높음, 다양한 OS/arch 지원
   - URL: `https://repo1.maven.org/maven2/io/zonky/test/postgres/embedded-postgres-binaries-{platform}/{version}/...`
   - jar 파일 = zip 파일, 내부에 PostgreSQL 바이너리 포함

2. **의존성 최소화**: httpx (다운로드), click (CLI), psycopg (DB 작업)

3. **디렉토리 구조** (런타임):
   ```
   ./pg_local/
   ├── bin/{version}/     # PostgreSQL 바이너리
   └── data/              # 데이터 클러스터
   ```

4. **패키지 구조**:
   ```
   src/pg_here/
   ├── __init__.py        # Public API (start_pg_here, stop_pg_here)
   ├── __main__.py        # python -m pg_here 지원
   ├── cli.py             # Click CLI
   ├── binary.py          # 바이너리 다운로드/캐시 관리
   ├── instance.py        # pg_ctl, initdb 래퍼
   ├── database.py        # DB 생성, 확장 설치
   └── platform_compat.py # 플랫폼별 로직 (libxml2 등)
   ```

---

## 태스크

### Phase 0: 프로젝트 스캐폴딩
- [x] **T0.1** pyproject.toml 작성 (메타데이터, 의존성, `[project.scripts]` 엔트리포인트)
- [x] **T0.2** src/pg_here/ 패키지 구조 생성 (빈 모듈들)
- [x] **T0.3** .gitignore 작성

### Phase 1: 바이너리 관리 (`binary.py`)
- [x] **T1.1** 플랫폼/아키텍처 감지 (darwin-arm64, darwin-amd64, linux-amd64 등)
- [x] **T1.2** Zonky Maven Central에서 PostgreSQL 바이너리 다운로드
- [x] **T1.3** jar(zip) 파일 추출 → pg_local/bin/{version}/ 에 설치
- [x] **T1.4** 이미 설치된 버전 감지 (재다운로드 방지)
### Phase 2: 인스턴스 관리 (`instance.py`)
- [x] **T2.1** `initdb` 래퍼 (데이터 디렉토리 초기화)
- [x] **T2.2** `pg_ctl start` 래퍼 (인스턴스 시작)
- [x] **T2.3** `pg_ctl stop` 래퍼 (인스턴스 종료)
- [x] **T2.4** postgresql.conf 관리 (포트, shared_preload_libraries 등)
- [x] **T2.5** 시그널 핸들링 (SIGINT, SIGTERM → graceful shutdown)

### Phase 3: 데이터베이스 관리 (`database.py`)
- [x] **T3.1** 데이터베이스 존재 여부 확인 및 생성
- [x] **T3.2** pg_stat_statements 확장 설치
- [x] **T3.3** 연결 문자열 생성

### Phase 4: CLI (`cli.py`)
- [x] **T4.1** Click 기반 CLI 구현 (--username, --password, --port, --database, --pg-version)
- [x] **T4.2** 시작 정보 출력 (연결 문자열, 버전, 포트 등)
- [x] **T4.3** 에러 처리 및 진단 메시지 (Linux libxml2 등)

### Phase 5: Public API (`__init__.py`)
- [ ] **T5.1** start_pg_here() / stop_pg_here() API
- [ ] **T5.2** PgHereHandle 데이터 클래스

### Phase 6: 테스트 및 마무리
- [ ] **T6.1** 통합 테스트 (실제 PostgreSQL 시작/종료/DB 생성)
- [ ] **T6.2** README.md 작성
- [ ] **T6.3** 로컬에서 `uvx` 테스트 (uv tool install --editable .)

---

## 참고: 원본(Node) 기본값

| 옵션 | 기본값 |
|------|--------|
| username | postgres |
| password | postgres |
| port | 55432 |
| database | postgres |
| pg-version | 17.4.0 (기본값, 이미 설치된 버전 우선) |
