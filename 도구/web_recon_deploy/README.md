<div align="center">

# 웹 정찰 도구

### 크롤링 * 소스코드 수집

<br>

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Go](https://img.shields.io/badge/Go-1.21%2B-00ADD8?style=for-the-badge&logo=go&logoColor=white)](https://go.dev/)
[![Katana](https://img.shields.io/badge/Crawler-katana-FF6B35?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyTDIgN2wxMCA1IDEwLTV6TTIgMTdsOSA1IDktNXYtNWwtOSA1LTktNXoiLz48L3N2Zz4=)](https://github.com/projectdiscovery/katana)
[![License](https://img.shields.io/badge/License-Educational-8B5CF6?style=for-the-badge)](/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-0EA5E9?style=for-the-badge&logo=windows&logoColor=white)](/)

<br>

[![Deps](https://img.shields.io/badge/Python%20Deps-Zero-22C55E?style=flat-square&logo=checkmarx&logoColor=white)](/)
[![UA Pool](https://img.shields.io/badge/User--Agent%20Pool-20종-F59E0B?style=flat-square)](/)
[![Secret Patterns](https://img.shields.io/badge/Secret%20Patterns-16종-EF4444?style=flat-square)](/)
[![Tech Detection](https://img.shields.io/badge/Tech%20Detection-20종-6366F1?style=flat-square)](/)

<br>

> **버그바운티 / 정찰**를 위한 웹 정보 수집 도구
>
> katana Go 라이브러리를 직접 embed — 외부 바이너리 설치 없이 동작

</div>

<br>


---

## 목차

- [기능](#기능)
- [요구사항](#요구사항)
- [설치](#설치)
- [사용법](#사용법)
- [옵션](#옵션)
- [스텔스 엔진](#스텔스-엔진)
- [실행 단계](#실행-단계)
- [출력 구조](#출력-구조)
- [JS 시크릿 탐지](#js-시크릿-탐지)
- [기술 스택 식별](#기술-스택-식별)
- [설정](#설정)

---

## 기능

<table>
<tr>
<td width="50%">

**수집**
| 카테고리 | 내용 |
|:---:|---|
| 크롤링 | katana Go 라이브러리 기반 FQDN 크롤링 |
| JS 수집 | `<script src>` 자동 파싱 → 병렬 다운로드 |
| 서브도메인 | crt.sh 인증서 투명성 API |
| 과거 URL | Wayback Machine CDX API |

</td>
<td width="50%">

**분석**
| 카테고리 | 내용 |
|:---:|---|
| 엔드포인트 | URL / Form / JS 세 소스 통합 추출 |
| 시크릿 탐지 | HIGH / MEDIUM / LOW 3등급 16종 패턴 |
| 보안 헤더 | CORS · CSP · HSTS · X-Frame-Options |
| 기술 스택 | 응답 헤더 + HTML 패턴 기반 20종 |

</td>
</tr>
</table>

<details>
<summary><b>탐지 회피 (스텔스 엔진)</b></summary>
<br>

| 기법 | 내용 |
|---|---|
| User-Agent 풀 | 실제 브라우저 UA 20종 — 매 요청마다 랜덤 교체 |
| 브라우저 헤더 | `Accept` / `Accept-Language` / `Sec-Fetch-*` 완전 모사 |
| 랜덤 딜레이 | 요청마다 다른 대기시간 — 패턴 기반 탐지 방지 |
| 레이트 리밋 | 크롤러 rate-limit 자동 조절 |
| 429 / 503 백오프 | 지수 백오프 자동 재시도 (최대 3회, 8–15s 대기) |
| 요청 순서 셔플 | JS 파일 다운로드 순서 무작위화 |

</details>

---

## 요구사항

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Go](https://img.shields.io/badge/Go-1.21%2B_(선택)-00ADD8?style=flat-square&logo=go&logoColor=white)](https://go.dev/)

| 항목 | 필수 | 비고 |
|---|:---:|---|
| Python 3.10+ | ✅ | 표준 라이브러리만 사용 (pip install 불필요) |
| Go 1.21+ | ⬜ | 있으면 `crawler/` 소스를 자동 빌드 |
| katana.exe | ⬜ | Go 없을 때 fallback용 (동봉) |

> [!NOTE]
> Go가 PATH에 있으면 첫 실행 시 `crawler/` 소스를 자동으로 빌드
> Go도 없고 katana.exe도 없으면 크롤링 단계에서 안내 메시지가 출력됨

---

## 설치

```bash
git clone https://github.com/khy123012/recon-stealth.git
cd recon-stealth
```

**[선택] 크롤러 사전 빌드 (Go 설치된 경우)**

```bash
cd crawler && go mod tidy && go build -o ../crawler.exe .
```

**폴더 구조**

```
recon-stealth/
├── recon.py          ← 메인 스크립트
├── category.txt      ← URL 필터 키워드
├── crawler/
│   ├── main.go       ← katana Go 라이브러리 embed
│   └── go.mod
├── crawler.exe       ← 빌드 후 생성 (자동)
└── katana.exe        ← fallback 바이너리
```

---

## 사용법

```bash
python recon.py <URL> [옵션]
```

**기본 전체 실행**

```bash
python recon.py https://target.com/
```

**WAF · IDS가 있는 대상 — 느린 스텔스 모드**

```bash
python recon.py https://target.com/ --stealth-level slow
```

**기존 수집 데이터 재분석 (크롤링 생략)**

```bash
python recon.py https://target.com/ --analyze-only
```

**서브도메인 · Wayback 생략 (빠른 수집만)**

```bash
python recon.py https://target.com/ --no-subdomains --no-wayback
```

---

## 옵션

| 옵션 | 기본값 | 설명 |
|---|:---:|---|
| `--stealth-level slow` | | 딜레이 5–10s / JS workers 1 / katana rate 3 |
| `--stealth-level normal` | ✓ | 딜레이 2–5s / JS workers 3 / katana rate 10 |
| `--stealth-level fast` | | 딜레이 1–2s / JS workers 8 / katana rate 20 |
| `--analyze-only` | | 크롤링 생략, 기존 데이터로 분석만 재실행 |
| `--no-subdomains` | | crt.sh 서브도메인 수집 생략 |
| `--no-wayback` | | Wayback Machine URL 수집 생략 |

---

## 스텔스 엔진

> [!IMPORTANT]
> `--stealth-level slow`는 WAF 또는 IDS가 설치된 대상에 권장합니다.
> `--stealth-level fast`는 탐지 수준이 낮은 내부망·테스트 환경에 적합합니다.

```
slow   ──────────────────────────────────────  딜레이 5–10s  │ rate  3/s  │ JS workers 1
normal ─────────────────────────────          딜레이 2–5s   │ rate 10/s  │ JS workers 3
fast   ─────────────────                      딜레이 1–2s   │ rate 20/s  │ JS workers 8
        낮은 탐지율 ◀──────────────────────────────▶ 빠른 수집
```

---

## 실행 단계

```
┌─ 1. 크롤링 ──────────────────────── result.txt, responses/
├─ 2. URL 필터링 ──────────────────── filter_result.txt
├─ 3. JS 파일 수집 (병렬) ─────────── js/
├─ 4. 엔드포인트 추출 ─────────────── endpoints.json, endpoints.txt
├─ 5. 서브도메인 수집 + DNS 검증 ──── subdomains.txt
├─ 6. Wayback Machine URL ─────────── wayback_urls.txt
├─ 7. JS 시크릿 탐지 ──────────────── secrets.txt, secrets.json
└─ 8. 보안 헤더 + 기술 스택 분석 ──── security_headers.txt
```

---

## 출력 구조

실행 후 대상 도메인 이름의 폴더가 자동 생성됩니다.

```
recon-stealth/
└── target.com/
    ├── result.txt              # katana 수집 전체 URL
    ├── filter_result.txt       # 카테고리별 분류 URL
    ├── responses/              # 페이지 소스코드 원문
    │   └── target.com/
    │       └── *.txt
    ├── js/                     # 다운로드된 JS 파일
    ├── endpoints.json          # 엔드포인트·파라미터 (JSON)
    ├── endpoints.txt           # 엔드포인트·파라미터 (읽기용)
    ├── subdomains.txt          # crt.sh 서브도메인 + DNS 검증
    ├── wayback_urls.txt        # Wayback Machine 과거 URL
    ├── secrets.txt             # 시크릿 탐지 결과 (등급별 정렬)
    ├── secrets.json            # 시크릿 구조화 데이터
    └── security_headers.txt    # 보안 헤더 + 기술 스택
```

---

## JS 시크릿 탐지

JS 파일 및 HTML 응답 전체를 신뢰도 등급별로 스캔합니다.

<table>
<tr>
<th>🔴 HIGH — 즉시 조치</th>
<th>🟡 MEDIUM — 검토 권장</th>
<th>⚪ LOW — 수동 검증</th>
</tr>
<tr>
<td valign="top">

- AWS Access Key (`AKIA...`)
- Google API Key (`AIza...`)
- Firebase Key
- Private Key (PEM)
- GitHub Token (`ghp_` 등)
- Stripe Key (`sk_live_` 등)
- Slack Webhook URL

</td>
<td valign="top">

- JWT Token (`eyJ...`)
- API Key 하드코딩
- AWS Secret Key
- Bearer Token
- DB Connection URI

</td>
<td valign="top">

- Basic Auth
- Password 하드코딩
- Secret / Token 키워드
- Private IP 하드코딩

</td>
</tr>
</table>

---

## 기술 스택 식별

응답 헤더와 HTML 패턴을 기반으로 자동 식별합니다.

![WordPress](https://img.shields.io/badge/-WordPress-21759B?style=flat-square&logo=wordpress&logoColor=white)
![Joomla](https://img.shields.io/badge/-Joomla-F44321?style=flat-square&logo=joomla&logoColor=white)
![Drupal](https://img.shields.io/badge/-Drupal-0678BE?style=flat-square&logo=drupal&logoColor=white)
![Laravel](https://img.shields.io/badge/-Laravel-FF2D20?style=flat-square&logo=laravel&logoColor=white)
![Django](https://img.shields.io/badge/-Django-092E20?style=flat-square&logo=django&logoColor=white)
![Rails](https://img.shields.io/badge/-Rails-CC0000?style=flat-square&logo=rubyonrails&logoColor=white)
![Spring](https://img.shields.io/badge/-Spring%20Boot-6DB33F?style=flat-square&logo=springboot&logoColor=white)
![ASP.NET](https://img.shields.io/badge/-ASP.NET-512BD4?style=flat-square&logo=dotnet&logoColor=white)
![Next.js](https://img.shields.io/badge/-Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![Nuxt.js](https://img.shields.io/badge/-Nuxt.js-00DC82?style=flat-square&logo=nuxtdotjs&logoColor=white)
![React](https://img.shields.io/badge/-React-61DAFB?style=flat-square&logo=react&logoColor=black)
![Vue.js](https://img.shields.io/badge/-Vue.js-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![Angular](https://img.shields.io/badge/-Angular-DD0031?style=flat-square&logo=angular&logoColor=white)
![jQuery](https://img.shields.io/badge/-jQuery-0769AD?style=flat-square&logo=jquery&logoColor=white)
![Bootstrap](https://img.shields.io/badge/-Bootstrap-7952B3?style=flat-square&logo=bootstrap&logoColor=white)
![PHP](https://img.shields.io/badge/-PHP-777BB4?style=flat-square&logo=php&logoColor=white)
![nginx](https://img.shields.io/badge/-nginx-009639?style=flat-square&logo=nginx&logoColor=white)
![Apache](https://img.shields.io/badge/-Apache-D22128?style=flat-square&logo=apache&logoColor=white)
![IIS](https://img.shields.io/badge/-IIS-0078D4?style=flat-square&logo=microsoft&logoColor=white)
![Cloudflare](https://img.shields.io/badge/-Cloudflare-F38020?style=flat-square&logo=cloudflare&logoColor=white)

---

## 설정

`recon.py` 상단의 상수를 수정해 동작을 커스터마이즈할 수 있습니다.

| 상수 | 설명 |
|---|---|
| `STEALTH_LEVELS` | 레벨별 딜레이·레이트·JS workers 값 |
| `USER_AGENTS` | UA 풀 목록 (추가·수정 가능) |
| `SECRET_PATTERNS` | 시크릿 탐지 정규식 + confidence 등급 |
| `TECH_SIGNATURES` | 기술 스택 식별 시그니처 |
| `RESPONSE_EXTENSIONS` | 응답 파일 확장자 목록 |

`category.txt` 파일을 편집해 URL 필터 키워드를 추가·제거할 수 있습니다.

---

<div align="center">

> [!CAUTION]
> 이 도구는 그냥 katana를 더 쉽게 쓰기위한 도구입니다
> 나중에 로컬 LLM이랑 연동해서 업그레이드 할 예정입니다.

<br>

[![Made with Python](https://img.shields.io/badge/Made%20with-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](/)
[![Powered by katana](https://img.shields.io/badge/Powered%20by-katana-FF6B35?style=for-the-badge)](https://github.com/projectdiscovery/katana)

</div>
