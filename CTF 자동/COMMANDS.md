# CTFlex 명령어 레퍼런스

## 준비

1. `problems/` 폴더에 CTF 문제 ZIP 파일 넣기
2. `config.yaml` 에 Gemini API 키 입력
3. **PowerShell(일반 터미널)** 에서 실행 (Claude Code 세션 내 실행 불가 — Claude CLI 중첩 금지)

---

## 기본 실행

```bash
python ctflex/main.py              # 기본 실행
python ctflex/main.py -v           # 상세 로그
python ctflex/main.py -q           # 조용하게 (배너/테이블 숨김)
```

---

## 서버 배포 모드

```bash
python ctflex/main.py --deploy auto     # 자동: EC2 → 로컬Docker → 수동 순
python ctflex/main.py --deploy ec2      # EC2만 사용
python ctflex/main.py --deploy local    # 로컬 Docker만
python ctflex/main.py --deploy manual   # 배포 없음 (servers.json에 URL 직접 입력)
python ctflex/main.py --no-deploy       # --deploy manual 과 동일
python ctflex/main.py --stop-containers # 실행 완료 후 컨테이너 자동 종료 (EC2 요금 절약)
```

> `config.yaml`에서 `stop_containers_after_run: true` 로 설정하면 매번 `--stop-containers` 안 써도 됨

---

## EC2 컨테이너 관리

```bash
# EC2의 모든 ctflex 컨테이너/이미지/파일 즉시 삭제
python ctflex/main.py --purge-ec2
```

`--purge-ec2` 가 하는 일:
- EC2 `/tmp/ctflex/` 하위 모든 `docker compose down`
- `ctflex_` 이름의 컨테이너 강제 삭제
- `ctflex_` 이미지 삭제
- `/tmp/ctflex` 디렉터리 삭제
- `results/servers.json` 에서 EC2 항목 제거

> EC2에 직접 SSH 접속할 시간이 없을 때 사용

---

## 성능 조정

```bash
python ctflex/main.py --parallel 5   # Gemini 동시 분석 수 (기본: config.yaml 값)
python ctflex/main.py --parallel 1   # 절약 모드 (느린 환경)
```

---

## 정리 (대회 종료 후)

```bash
python ctflex/main.py --clean                            # 생성 파일 전부 삭제
python ctflex/main.py --clean --keep-flags               # 플래그(flags.json)는 보존
python ctflex/main.py --clean --keep-cache               # Gemini 캐시 보존 (다음 대회 재사용)
python ctflex/main.py --clean --keep-flags --keep-cache  # 플래그 + 캐시 보존
```

`--clean` 이 삭제하는 것:
- `problems/_extracted/` (압축 해제본)
- `results/generated_exploits/` (익스플로잇 코드)
- `results/logs/`
- `results/analysis_results.json`
- `results/servers.json`
- `results/cache/` (--keep-cache 없을 때)
- `results/flags.json` (--keep-flags 없을 때)

---

## servers.json 수동 등록

서버 URL을 직접 아는 경우 `results/servers.json` 에 작성 후 `--no-deploy` 로 실행:

```json
{
  "문제이름": {
    "url": "http://서버IP:포트",
    "deploy_mode": "manual",
    "status": "manual"
  }
}
```

```bash
python ctflex/main.py --no-deploy -v
```

---

## 실전 패턴

```bash
# 대회 시작
python ctflex/main.py -v

# 일부만 풀렸으면 그냥 재실행 (이미 푼 문제 자동 스킵)
python ctflex/main.py -v

# CTF 끝나고 EC2 컨테이너 남아있으면
python ctflex/main.py --purge-ec2

# 대회 완전 종료 (플래그/캐시 보존)
python ctflex/main.py --clean --keep-flags --keep-cache
```

---

## 저장 위치

```
problems/_extracted/          ← ZIP 압축 해제본
results/
├── flags.json                ← 찾은 플래그 ★
├── analysis_results.json     ← 분석 결과
├── servers.json              ← 문제별 서버 URL
├── generated_exploits/       ← 생성된 익스플로잇 코드
├── cache/                    ← Gemini 분석 캐시 (재사용 가능)
└── logs/                     ← Docker 빌드 로그 등
```

---

## 비용

| 항목 | 비용 |
|------|------|
| Gemini 분석 (문제 1개) | ~$0.001 ~ $0.003 |
| 캐시 적중 | $0 |
| EC2 t2.micro (무료 티어) | $0 |
| EC2 t3.micro | ~$0.013/h |

> `stop_containers_after_run: true` 설정 시 실행 완료 후 EC2 컨테이너 자동 종료 → 불필요한 요금 방지
