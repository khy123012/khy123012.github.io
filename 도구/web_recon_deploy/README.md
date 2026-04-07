# Recon Automation Tool

정보 수집 / 소스코드 수집 자동화 도구  
**주의: 공격 행위 금지 — 정보 수집 / 소스코드 수집만 수행**

---

## 사전 준비

### katana 설치
```bash
go install github.com/projectdiscovery/katana/cmd/katana@latest
```
또는 [릴리즈 페이지](https://github.com/projectdiscovery/katana/releases)에서 바이너리 다운로드 후 PATH에 추가.

PATH에 등록하지 않을 경우 `recon.py` 상단 `KATANA_PATH`에 절대 경로를 직접 입력하세요.

### Python 버전
Python 3.10 이상 (표준 라이브러리만 사용, 별도 설치 불필요)

---

## 사용법

```
python recon.py <URL> [옵션]
```

---

## 옵션

| 옵션 | 설명 |
|---|---|
| (없음) | 크롤링 + JS 수집 + 엔드포인트 분석 전체 실행 |
| `--analyze-only` | 크롤링 생략, 기존 responses/ 데이터로 분석만 재실행 |

---

## 명령어 예시

### 전체 실행 (크롤링 → JS → 분석)
```bash
python recon.py https://example.com/
```

### 기존 데이터 재분석 (크롤링 생략)
```bash
python recon.py https://example.com/ --analyze-only
```

---

## 실행 단계

| 단계 | 내용 |
|---|---|
| 1 | katana 크롤링 (`-fs fqdn -d 3`) → `result.txt`, `responses/` |
| 2 | category.txt 기반 URL 필터링 → `filter_result.txt` |
| 3 | responses/*.txt 파싱 → `<script src>` 추출 → JS 다운로드 → `js/` |
| 4 | HTML/JS 분석 → 엔드포인트/파라미터 추출 → `endpoints.json`, `endpoints.txt` |

---

## 출력 폴더 구조

```
web_recon_deploy/
└── example.com/                  ← 도메인명으로 자동 생성
    ├── result.txt                ← katana 수집 전체 URL
    ├── filter_result.txt         ← 카테고리별 분류 (어드민, API, 로그인 등)
    ├── responses/                ← 페이지 소스코드 (HTTP 요청+응답 원문)
    │   └── example.com/
    │       └── <hash>.txt
    ├── js/                       ← 다운로드된 JS 파일
    │   ├── common.js
    │   └── ...
    ├── endpoints.json            ← 구조화 데이터 (JSON)
    └── endpoints.txt             ← 구조화 데이터 (읽기용)
```

---

## endpoints.txt / endpoints.json 항목

| 항목 | 출처 |
|---|---|
| `endpoints_from_urls` | katana result.txt의 path 부분 |
| `endpoints_from_forms` | HTML `<form action="...">` |
| `endpoints_from_js` | JS 내 fetch / axios / $.get / url= 패턴 |
| `params_from_urls` | URL 쿼리스트링 `?param=value` |
| `params_from_forms` | HTML `<input name="...">` |
| `js_files_downloaded` | 다운로드된 JS 파일 URL 목록 |

---

## 설정 파일

| 파일 | 설명 |
|---|---|
| `category.txt` | URL 필터링 키워드 (어드민/API/로그인/백업 등) |
| `recon.py` 상단 `KATANA_PATH` | katana PATH 미등록 시 절대 경로 지정 |
