import subprocess
import sys
import re
import json
import shutil
import random
import time
import socket
import threading
import argparse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# ── 설정 ──────────────────────────────────────────────────────────

CATEGORY_FILE = Path(__file__).parent / "category.txt"

# 스텔스 레벨별 딜레이 범위 (초)
STEALTH_LEVELS = {
    "slow":   {"min": 5.0, "max": 10.0, "rate": 3,  "katana_delay": 5,  "js_workers": 1},
    "normal": {"min": 2.0, "max": 5.0,  "rate": 10, "katana_delay": 2,  "js_workers": 3},
    "fast":   {"min": 1.0, "max": 2.5,  "rate": 20, "katana_delay": 1,  "js_workers": 8},
}

# 실제 브라우저 User-Agent 풀
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/110.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/110.0.0.0",
]

# JS 시크릿 탐지 패턴 — confidence: HIGH / MEDIUM / LOW
#   HIGH   : 포맷이 고정적, 오탐 거의 없음 → 즉시 조치
#   MEDIUM : 패턴이 구체적이나 일부 오탐 가능 → 검토 권장
#   LOW    : 광범위 패턴, 수동 검증 필요
SECRET_PATTERNS: dict[str, dict] = {
    # ── HIGH ─────────────────────────────────────────────────────
    "AWS Access Key":  {"pattern": r'AKIA[0-9A-Z]{16}',
                        "confidence": "HIGH"},
    "Google API Key":  {"pattern": r'AIza[0-9A-Za-z\-_]{35}',
                        "confidence": "HIGH"},
    "Firebase Key":    {"pattern": r'AAAA[A-Za-z0-9_\-]{7}:[A-Za-z0-9_\-]{140}',
                        "confidence": "HIGH"},
    "Private Key":     {"pattern": r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----',
                        "confidence": "HIGH"},
    "Slack Webhook":   {"pattern": r'https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+',
                        "confidence": "HIGH"},
    "GitHub Token":    {"pattern": r'gh[pousr]_[A-Za-z0-9]{36,}',
                        "confidence": "HIGH"},
    "Stripe Key":      {"pattern": r'(?:sk|pk)_(test|live)_[A-Za-z0-9]{24,}',
                        "confidence": "HIGH"},
    # ── MEDIUM ───────────────────────────────────────────────────
    "JWT Token":       {"pattern": r'eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}',
                        "confidence": "MEDIUM"},
    "API Key":         {"pattern": r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']([A-Za-z0-9_\-]{20,})["\']',
                        "confidence": "MEDIUM"},
    "AWS Secret Key":  {"pattern": r'(?i)aws[_\-]?secret[_\-]?key\s*[:=]\s*["\']([A-Za-z0-9/+]{40})["\']',
                        "confidence": "MEDIUM"},
    "Bearer Token":    {"pattern": r'(?i)["\']?bearer\s+[A-Za-z0-9_\-\.]{20,}["\']?',
                        "confidence": "MEDIUM"},
    "DB Connection":   {"pattern": r'(?i)(mysql|postgres|mongodb|redis|mssql)://[^\s"\'<>]{8,}',
                        "confidence": "MEDIUM"},
    # ── LOW ──────────────────────────────────────────────────────
    "Basic Auth":      {"pattern": r'(?i)basic\s+[A-Za-z0-9+/=]{20,}',
                        "confidence": "LOW"},
    "Password Hard":   {"pattern": r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']([^"\']{6,})["\']',
                        "confidence": "LOW"},
    "Secret Hard":     {"pattern": r'(?i)(secret|token)\s*[:=]\s*["\']([A-Za-z0-9_\-\.]{10,})["\']',
                        "confidence": "LOW"},
    "Private IP Hard": {"pattern": r'(?i)(host|server|endpoint)\s*[:=]\s*["\']((10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)[0-9.]{4,})["\']',
                        "confidence": "LOW"},
}

# 기술 스택 시그니처
TECH_SIGNATURES = {
    "WordPress":   {"html": ["wp-content", "wp-includes", "wp-json"],           "header": []},
    "Joomla":      {"html": ["/components/com_", "Joomla!"],                     "header": []},
    "Drupal":      {"html": ["Drupal.settings", "/sites/default/files/"],        "header": ["X-Generator: Drupal"]},
    "Laravel":     {"html": ["laravel_session", "_token"],                       "header": ["laravel_session"]},
    "Django":      {"html": ["csrfmiddlewaretoken", "__django"],                 "header": []},
    "Rails":       {"html": ["authenticity_token"],                              "header": ["X-Powered-By: Phusion Passenger"]},
    "Spring Boot": {"html": ["JSESSIONID"],                                      "header": ["X-Application-Context"]},
    "ASP.NET":     {"html": ["__VIEWSTATE", "__EVENTVALIDATION", "ASP.NET_SessionId"], "header": ["X-AspNet-Version", "X-Powered-By: ASP.NET"]},
    "Next.js":     {"html": ["__NEXT_DATA__", "_next/static"],                   "header": []},
    "Nuxt.js":     {"html": ["__nuxt", "__NUXT__", "_nuxt/"],                    "header": []},
    "React":       {"html": ["__react", "data-reactroot", "react-dom"],          "header": []},
    "Vue.js":      {"html": ["data-v-", "__vue__", "vue-router"],                "header": []},
    "Angular":     {"html": ["ng-version", "ng-app", "_nghost"],                 "header": []},
    "jQuery":      {"html": ["jquery.min.js", "jquery-"],                        "header": []},
    "Bootstrap":   {"html": ["bootstrap.min.css", "bootstrap.min.js"],           "header": []},
    "PHP":         {"html": [".php"],                                             "header": ["X-Powered-By: PHP"]},
    "nginx":       {"html": [],                                                   "header": ["Server: nginx"]},
    "Apache":      {"html": [],                                                   "header": ["Server: Apache"]},
    "IIS":         {"html": [],                                                   "header": ["Server: Microsoft-IIS"]},
    "Cloudflare":  {"html": [],                                                   "header": ["CF-Ray", "Server: cloudflare"]},
}

# katana -store-response 가 생성하는 파일 확장자 (버전별 차이 대응)
RESPONSE_EXTENSIONS = {".txt", ".html", ".htm", ".json", ""}


# ── KatanaRunner — Go 라이브러리 기반 크롤러 ─────────────────────

class KatanaRunner:
    """
    katana Go 라이브러리 래퍼.

    우선순위:
      1. crawler/ 폴더의 소스를 go build 해서 생성한 커스텀 바이너리
         (katana.exe 불필요 — Go 라이브러리를 직접 embed)
      2. PATH 또는 스크립트 폴더의 katana / katana.exe (기존 방식 fallback)

    커스텀 바이너리 빌드:
        cd crawler && go mod tidy && go build -o ../crawler.exe .
    또는 KatanaRunner() 생성 시 Go가 PATH에 있으면 자동 빌드.
    """

    CRAWLER_DIR = Path(__file__).parent / "crawler"
    BUILD_HINT = (
        "크롤러 빌드 방법:\n"
        "  cd crawler && go mod tidy && go build -o ../crawler.exe .\n"
        "또는 Go 없이 쓰려면:\n"
        "  https://github.com/projectdiscovery/katana/releases 에서\n"
        "  katana.exe를 이 폴더에 배치하세요."
    )

    def __init__(self, path: str = None):
        self.bin, self.is_custom = self._resolve(path)

    def _resolve(self, hint: str = None) -> tuple[str, bool]:
        script_dir = Path(__file__).parent

        # 1순위: 명시적 경로
        if hint and Path(hint).is_file():
            return hint, False

        # 2순위: 이미 빌드된 커스텀 바이너리
        for name in ("crawler.exe", "crawler"):
            p = script_dir / name
            if p.is_file():
                return str(p), True

        # 3순위: Go가 있으면 소스에서 자동 빌드
        if shutil.which("go") and self.CRAWLER_DIR.is_dir():
            built = self._build()
            if built:
                return built, True

        # 4순위: PATH의 katana 또는 bundled katana.exe (fallback)
        found = shutil.which("katana")
        if found:
            return found, False
        for name in ("katana.exe", "katana"):
            p = script_dir / name
            if p.is_file():
                return str(p), False

        raise FileNotFoundError(
            f"크롤러를 찾을 수 없습니다.\n{self.BUILD_HINT}"
        )

    def _build(self) -> str | None:
        """crawler/ 소스를 go build — 성공 시 바이너리 경로 반환."""
        import platform
        out_name = "crawler.exe" if platform.system() == "Windows" else "crawler"
        out_path = str(Path(__file__).parent / out_name)

        print("[*] crawler/ 소스 빌드 중...")
        try:
            # go mod tidy → go build
            subprocess.run(
                ["go", "mod", "tidy"],
                cwd=str(self.CRAWLER_DIR), check=True,
                capture_output=True,
            )
            subprocess.run(
                ["go", "build", "-o", out_path, "."],
                cwd=str(self.CRAWLER_DIR), check=True,
                capture_output=True,
            )
            print(f"[+] 빌드 완료: {out_path}")
            return out_path
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors="ignore") if e.stderr else ""
            print(f"[!] 빌드 실패: {stderr[:300]}")
            return None

    @property
    def version(self) -> str:
        flag = "--version" if self.is_custom else "-version"
        try:
            r = subprocess.run(
                [self.bin, flag],
                capture_output=True, text=True, timeout=5,
            )
            return (r.stdout or r.stderr).strip()
        except Exception:
            return "custom-build" if self.is_custom else "unknown"

    def crawl(
        self,
        url: str,
        output_file: Path,
        responses_dir: Path,
        *,
        depth: int = 3,
        delay: int = 2,
        rate_limit: int = 10,
        user_agent: str = None,
        js_crawl: bool = True,
        known_files: str = None,
        extra_flags: list[str] = None,
    ) -> bool:
        ua = user_agent or random.choice(USER_AGENTS)

        if self.is_custom:
            # 커스텀 바이너리 플래그 (crawler/main.go 인터페이스)
            cmd = [
                self.bin,
                "-u",                   url,
                "-o",                   str(output_file),
                "-store-response-dir",  str(responses_dir),
                "-d",                   str(depth),
                "-delay",               str(delay),
                "-rate-limit",          str(rate_limit),
                "-ua",                  ua,
            ]
            if js_crawl:
                cmd += ["-jc=true"]
        else:
            # 기존 katana CLI 플래그 (fallback)
            cmd = [
                self.bin,
                "-u",                  url,
                "-o",                  str(output_file),
                "-store-response",
                "-store-response-dir", str(responses_dir),
                "-fs",                 "fqdn",
                "-d",                  str(depth),
                "-delay",              str(delay),
                "-rate-limit",         str(rate_limit),
                "-timeout",            "30",
                "-H",                  f"User-Agent: {ua}",
                "-silent",
            ]
            if js_crawl:
                cmd.append("-jc")
            if known_files:
                cmd += ["-kf", known_files]
            if extra_flags:
                cmd += extra_flags

        try:
            subprocess.run(cmd, check=True)
            return True
        except FileNotFoundError:
            print(f"[!] 실행 불가: {self.bin}\n{self.BUILD_HINT}")
            return False
        except subprocess.CalledProcessError as e:
            print(f"[!] 크롤러 오류: {e}")
            return False


# ── 스텔스 엔진 ───────────────────────────────────────────────────

def get_stealth_headers(referer: str = None) -> dict:
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent":      ua,
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(["ko-KR,ko;q=0.9,en-US;q=0.8", "en-US,en;q=0.9", "ja-JP,ja;q=0.9,en;q=0.8"]),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection":      "keep-alive",
        "Cache-Control":   random.choice(["max-age=0", "no-cache"]),
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest":  "document",
        "Sec-Fetch-Mode":  "navigate",
        "Sec-Fetch-Site":  "none",
        "Sec-Fetch-User":  "?1",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def stealth_sleep(level: str = "normal"):
    cfg = STEALTH_LEVELS.get(level, STEALTH_LEVELS["normal"])
    time.sleep(random.uniform(cfg["min"], cfg["max"]))


def stealth_request(url: str, referer: str = None, level: str = "normal",
                    max_retry: int = 3, timeout: int = 15) -> bytes | None:
    for attempt in range(max_retry):
        try:
            headers = get_stealth_headers(referer)
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                wait = (2 ** attempt) * random.uniform(8, 15)
                print(f"  [!] HTTP {e.code} — {wait:.1f}초 대기 후 재시도 ({attempt+1}/{max_retry})")
                time.sleep(wait)
            else:
                print(f"  [!] HTTP {e.code}: {url}")
                return None
        except Exception:
            if attempt < max_retry - 1:
                stealth_sleep(level)
    return None


def stealth_request_with_headers(url: str, timeout: int = 15) -> tuple[bytes | None, dict]:
    try:
        headers = get_stealth_headers()
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return None, dict(e.headers) if e.headers else {}
    except Exception:
        return None, {}


# ── 응답 파일 이터레이터 (Fix 5) ─────────────────────────────────

def iter_response_files(responses_dir: Path):
    """
    katana -store-response 결과 파일 이터레이터.
    버전에 따라 .txt / .html / 확장자 없음 등으로 저장되므로
    확장자 무관하게 텍스트 파일을 모두 순회한다.
    """
    for f in responses_dir.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix.lower() in RESPONSE_EXTENSIONS:
            yield f


# ── category 필터 ─────────────────────────────────────────────────

def load_categories(filepath: Path) -> dict[str, list[str]]:
    if not filepath.exists():
        print(f"[!] category.txt 없음: {filepath}")
        sys.exit(1)

    categories: dict[str, list[str]] = {}
    current = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current = line[1:-1]
                categories[current] = []
            elif current:
                categories[current].append(line)

    for c in [c for c, kws in categories.items() if not kws]:
        del categories[c]

    return categories


def filter_urls(urls: list[str], categories: dict[str, list[str]]) -> dict[str, list[str]]:
    matched: dict[str, list[str]] = {cat: [] for cat in categories}
    for url in urls:
        url_lower = url.lower()
        for category, keywords in categories.items():
            if any(kw in url_lower for kw in keywords):
                matched[category].append(url)
                break
    return {cat: urls for cat, urls in matched.items() if urls}


def save_filter_result(matched: dict[str, list[str]], output_file: Path, target_url: str):
    total = sum(len(v) for v in matched.values())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Katana Filter Result\n")
        f.write(f"# Target : {target_url}\n")
        f.write(f"# Date   : {timestamp}\n")
        f.write(f"# Total  : {total} URLs matched\n")
        f.write("=" * 60 + "\n\n")
        for category, urls in matched.items():
            f.write(f"[{category}]  ({len(urls)} 개)\n")
            f.write("-" * 40 + "\n")
            for url in sorted(urls):
                f.write(f"  {url}\n")
            f.write("\n")

    print(f"[+] filter_result.txt 저장: {output_file}")


# ── katana 크롤링 ─────────────────────────────────────────────────

def run_katana(url: str, result_file: Path, responses_dir: Path,
               level: str = "normal") -> bool:
    print(f"[*] 크롤링 시작: {url}  (stealth={level})")
    cfg = STEALTH_LEVELS.get(level, STEALTH_LEVELS["normal"])

    runner = KatanaRunner()
    print(f"    katana {runner.version}")

    return runner.crawl(
        url,
        result_file,
        responses_dir,
        depth=3,
        delay=cfg["katana_delay"],
        rate_limit=cfg["rate"],
        js_crawl=True,
    )


# ── JS 파일 수집 (Fix 2: 병렬 다운로드) ──────────────────────────

def collect_js_files(responses_dir: Path, js_dir: Path,
                     target_domain: str, base_url: str,
                     level: str = "normal") -> list[str]:
    """HTML responses에서 <script src> 추출 → 병렬 스텔스 JS 다운로드"""
    js_dir.mkdir(parents=True, exist_ok=True)

    script_urls: set[str] = set()

    for html_file in iter_response_files(responses_dir):   # Fix 5 적용
        try:
            content = html_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for match in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE):
            src = match.group(1).strip()
            if not src or src.startswith("data:"):
                continue
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                parsed_base = urlparse(base_url)
                src = f"{parsed_base.scheme}://{parsed_base.netloc}{src}"
            elif not src.startswith("http"):
                src = base_url.rstrip("/") + "/" + src

            parsed_src = urlparse(src)
            if target_domain in parsed_src.netloc:
                script_urls.add(src)

    workers = STEALTH_LEVELS.get(level, STEALTH_LEVELS["normal"])["js_workers"]
    js_list = sorted(script_urls)
    random.shuffle(js_list)

    downloaded: list[str] = []
    seen_names: dict[str, int] = {}
    lock = threading.Lock()

    def download_one(js_url: str) -> str | None:
        with lock:
            name = Path(urlparse(js_url).path).name or "script.js"
            if not name.endswith(".js"):
                name += ".js"
            if name in seen_names:
                seen_names[name] += 1
                stem, ext = name.rsplit(".", 1)
                name = f"{stem}_{seen_names[name]}.{ext}"
            else:
                seen_names[name] = 0
            save_path = js_dir / name

        print(f"  [JS] {js_url}")
        data = stealth_request(js_url, referer=base_url, level=level)
        if data:
            save_path.write_bytes(data)
            size = save_path.stat().st_size
            print(f"       → {save_path.name} ({size:,} bytes)")
            stealth_sleep(level)
            return js_url
        else:
            print(f"       [!] 다운로드 실패")
            return None

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(download_one, url): url for url in js_list}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                downloaded.append(result)

    return downloaded


# ── 서브도메인 DNS 검증 (Fix 3) ───────────────────────────────────

def verify_subdomains_dns(subdomains: list[str],
                          workers: int = 30) -> dict[str, list[str]]:
    """DNS 조회로 살아있는 서브도메인과 죽은 서브도메인을 분류한다."""
    alive, dead = [], []

    def check(sub: str) -> tuple[str, bool]:
        try:
            socket.getaddrinfo(sub, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            return sub, True
        except (socket.gaierror, OSError):
            return sub, False

    print(f"  [DNS] {len(subdomains)}개 서브도메인 검증 중 (workers={workers})...")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(check, s): s for s in subdomains}
        for fut in as_completed(futures):
            try:
                sub, is_alive = fut.result(timeout=10)
            except Exception:
                sub = futures[fut]
                is_alive = False
            (alive if is_alive else dead).append(sub)

    return {"alive": sorted(alive), "dead": sorted(dead)}


# ── 서브도메인 수집 (crt.sh) ──────────────────────────────────────

def collect_subdomains_crtsh(domain: str, output_file: Path,
                              level: str = "normal") -> list[str]:
    print(f"[*] crt.sh 서브도메인 수집 중: {domain}")
    api_url = f"https://crt.sh/?q=%.{domain}&output=json"

    data = stealth_request(api_url, level=level, timeout=30)
    if not data:
        print("  [!] crt.sh 응답 없음")
        return []

    try:
        entries = json.loads(data.decode("utf-8", errors="ignore"))
    except Exception:
        print("  [!] crt.sh JSON 파싱 실패")
        return []

    subdomains: set[str] = set()
    for entry in entries:
        name_val = entry.get("name_value", "")
        for name in name_val.splitlines():
            name = name.strip().lstrip("*.")
            if name and domain in name and " " not in name:
                subdomains.add(name.lower())

    all_subs = sorted(subdomains)
    print(f"    crt.sh 발견: {len(all_subs)} 개")

    # Fix 3: DNS 검증
    dns_result = verify_subdomains_dns(all_subs)
    alive_subs = dns_result["alive"]
    dead_subs  = dns_result["dead"]
    print(f"    DNS 응답: {len(alive_subs)} alive / {len(dead_subs)} dead")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Subdomains — crt.sh + DNS 검증\n")
        f.write(f"# Target : {domain}\n")
        f.write(f"# Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total  : {len(all_subs)} (alive: {len(alive_subs)}, dead: {len(dead_subs)})\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"[ALIVE — DNS 응답 있음]  ({len(alive_subs)} 개)\n")
        f.write("-" * 40 + "\n")
        for sub in alive_subs:
            f.write(f"  {sub}\n")

        f.write(f"\n[DEAD — DNS 응답 없음]  ({len(dead_subs)} 개)\n")
        f.write("-" * 40 + "\n")
        for sub in dead_subs:
            f.write(f"  {sub}\n")

    print(f"[+] subdomains.txt 저장: {output_file}")
    return alive_subs


# ── 과거 URL 수집 (Wayback Machine) ──────────────────────────────

def collect_wayback_urls(domain: str, output_file: Path,
                         level: str = "normal") -> list[str]:
    print(f"[*] Wayback Machine URL 수집 중: {domain}")
    api_url = (
        f"http://web.archive.org/cdx/search/cdx"
        f"?url=*.{domain}/*&output=text&fl=original&collapse=urlkey&limit=5000"
    )

    stealth_sleep(level)
    data = stealth_request(api_url, level=level, timeout=60)
    if not data:
        print("  [!] Wayback Machine 응답 없음")
        return []

    lines = data.decode("utf-8", errors="ignore").splitlines()
    urls = sorted(set(l.strip() for l in lines if l.strip().startswith("http")))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Wayback Machine URLs\n")
        f.write(f"# Target : {domain}\n")
        f.write(f"# Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total  : {len(urls)}\n")
        f.write("=" * 60 + "\n\n")
        for url in urls:
            f.write(f"{url}\n")

    print(f"[+] wayback_urls.txt 저장: {output_file}  ({len(urls)} 개)")
    return urls


# ── JS 시크릿 탐지 (Fix 4: confidence 등급) ──────────────────────

def detect_js_secrets(js_dir: Path, responses_dir: Path,
                      secrets_txt: Path, secrets_json: Path) -> dict:
    print(f"[*] JS 시크릿 탐지 중...")

    # { pat_name: [ {source, match, line, confidence}, ... ] }
    findings: dict[str, list[dict]] = {pat: [] for pat in SECRET_PATTERNS}

    def scan_content(content: str, source: str):
        for pat_name, meta in SECRET_PATTERNS.items():
            for m in re.finditer(meta["pattern"], content):
                val = m.group(0)[:200]
                entry = {
                    "source":     source,
                    "match":      val,
                    "line":       content[:m.start()].count("\n") + 1,
                    "confidence": meta["confidence"],
                }
                if not any(e["match"] == val and e["source"] == source
                           for e in findings[pat_name]):
                    findings[pat_name].append(entry)

    for f in js_dir.rglob("*.js"):
        try:
            scan_content(f.read_text(encoding="utf-8", errors="ignore"), "js/" + f.name)
        except Exception:
            continue

    for f in iter_response_files(responses_dir):             # Fix 5 적용
        try:
            scan_content(f.read_text(encoding="utf-8", errors="ignore"),
                         "responses/" + f.name)
        except Exception:
            continue

    findings = {k: v for k, v in findings.items() if v}
    total = sum(len(v) for v in findings.values())

    # confidence 별 카운트
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for items in findings.values():
        for item in items:
            counts[item["confidence"]] += 1

    CONF_LABEL = {"HIGH": "🔴 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "⚪ LOW"}

    with open(secrets_txt, "w", encoding="utf-8") as f:
        f.write(f"# JS Secret Detection Report\n")
        f.write(f"# Date      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total     : {total} 개 발견\n")
        f.write(f"# HIGH      : {counts['HIGH']} 개  (즉시 조치)\n")
        f.write(f"# MEDIUM    : {counts['MEDIUM']} 개  (검토 권장)\n")
        f.write(f"# LOW       : {counts['LOW']} 개  (수동 검증)\n")
        f.write("=" * 60 + "\n\n")

        if not findings:
            f.write("발견된 시크릿 없음\n")

        # HIGH → MEDIUM → LOW 순서로 출력
        for confidence in ("HIGH", "MEDIUM", "LOW"):
            section = {k: v for k, v in findings.items()
                       if v and v[0]["confidence"] == confidence}
            if not section:
                continue
            f.write(f"\n{'='*60}\n")
            f.write(f"  {CONF_LABEL[confidence]}\n")
            f.write(f"{'='*60}\n")
            for pat_name, items in section.items():
                f.write(f"\n[{pat_name}]  ({len(items)} 개)\n")
                f.write("-" * 40 + "\n")
                for item in items:
                    f.write(f"  출처  : {item['source']}  (line {item['line']})\n")
                    f.write(f"  매칭  : {item['match']}\n\n")

    with open(secrets_json, "w", encoding="utf-8") as f:
        json.dump(findings, f, ensure_ascii=False, indent=2)

    if findings:
        print(f"[+] secrets.txt 저장: {secrets_txt}")
        print(f"    HIGH={counts['HIGH']}  MEDIUM={counts['MEDIUM']}  LOW={counts['LOW']}")
    else:
        print(f"[+] secrets.txt 저장: 발견 없음")

    return findings


# ── 보안 헤더 + CORS + 기술 스택 분석 ────────────────────────────

def analyze_security_and_tech(url: str, responses_dir: Path,
                               output_file: Path, level: str = "normal"):
    print(f"[*] 보안 헤더 + 기술 스택 분석 중...")

    stealth_sleep(level)
    _, resp_headers = stealth_request_with_headers(url)

    security_checks = {
        "CORS (Access-Control-Allow-Origin)": resp_headers.get("Access-Control-Allow-Origin", ""),
        "CSP (Content-Security-Policy)":      resp_headers.get("Content-Security-Policy", ""),
        "HSTS (Strict-Transport-Security)":   resp_headers.get("Strict-Transport-Security", ""),
        "X-Frame-Options":                    resp_headers.get("X-Frame-Options", ""),
        "X-Content-Type-Options":             resp_headers.get("X-Content-Type-Options", ""),
        "Referrer-Policy":                    resp_headers.get("Referrer-Policy", ""),
        "Permissions-Policy":                 resp_headers.get("Permissions-Policy", ""),
        "Server (노출)":                       resp_headers.get("Server", ""),
        "X-Powered-By (노출)":                resp_headers.get("X-Powered-By", ""),
        "X-AspNet-Version (노출)":            resp_headers.get("X-AspNet-Version", ""),
    }

    cors_val  = security_checks["CORS (Access-Control-Allow-Origin)"]
    cors_risk = "CRITICAL — 와일드카드(*) 설정" if cors_val == "*" else \
                "주의 — 특정 오리진 허용" if cors_val else "없음 (기본)"

    detected_tech: list[str] = []
    all_html = ""

    for html_file in list(iter_response_files(responses_dir))[:10]:   # Fix 5 적용
        try:
            all_html += html_file.read_text(encoding="utf-8", errors="ignore")[:50000]
        except Exception:
            continue

    header_str = " ".join(f"{k}: {v}" for k, v in resp_headers.items())

    for tech, sigs in TECH_SIGNATURES.items():
        matched = any(kw.lower() in all_html.lower() for kw in sigs["html"]) or \
                  any(kw.lower() in header_str.lower() for kw in sigs["header"])
        if matched:
            detected_tech.append(tech)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Security Headers & Tech Stack Report\n")
        f.write(f"# Target : {url}\n")
        f.write(f"# Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        f.write("[보안 헤더 상태]\n")
        f.write("-" * 40 + "\n")
        for header, val in security_checks.items():
            status = "✓ 설정됨" if val else "✗ 없음"
            f.write(f"  {status}  {header}\n")
            if val:
                f.write(f"          값: {val[:120]}\n")
        f.write(f"\n[CORS 위험도]\n  {cors_risk}\n\n")

        f.write("[감지된 기술 스택]\n")
        f.write("-" * 40 + "\n")
        if detected_tech:
            for tech in detected_tech:
                f.write(f"  • {tech}\n")
        else:
            f.write("  감지 없음\n")

        f.write("\n[전체 응답 헤더]\n")
        f.write("-" * 40 + "\n")
        for k, v in resp_headers.items():
            f.write(f"  {k}: {v}\n")

    print(f"[+] security_headers.txt 저장: {output_file}")
    print(f"    CORS: {cors_risk}")
    print(f"    기술 스택: {', '.join(detected_tech) if detected_tech else '미감지'}")


# ── 엔드포인트 / 파라미터 구조화 ─────────────────────────────────

def extract_endpoints(responses_dir: Path, js_dir: Path,
                      all_urls: list[str]) -> dict:
    endpoints_url: set[str] = set()
    params_url:    set[str] = set()
    form_actions:  set[str] = set()
    form_params:   set[str] = set()
    js_endpoints:  set[str] = set()

    for url in all_urls:
        parsed = urlparse(url)
        if parsed.path and parsed.path != "/":
            endpoints_url.add(parsed.path)
        if parsed.query:
            for param in parse_qs(parsed.query):
                params_url.add(param)

    for html_file in iter_response_files(responses_dir):    # Fix 5 적용
        try:
            content = html_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for m in re.finditer(r'<form[^>]+action=["\']([^"\']+)["\']', content, re.IGNORECASE):
            action = m.group(1).strip()
            if not action or action.startswith(("javascript", "#", "mailto")):
                continue
            if action.startswith("http"):
                p = urlparse(action)
                if p.path:
                    form_actions.add(p.path)
            else:
                form_actions.add(action)

        for m in re.finditer(
            r'<(?:input|select|textarea)[^>]+name=["\']([^"\']+)["\']',
            content, re.IGNORECASE,
        ):
            form_params.add(m.group(1))

    JS_PATTERNS = [
        r'fetch\s*\(\s*["`]([^"`\s]+)["`]',
        r'axios\.[a-z]+\s*\(\s*["`]([^"`\s]+)["`]',
        r'\$\.(?:get|post|ajax)\s*\(\s*["`]([^"`\s]+)["`]',
        r'url\s*[:=]\s*["`]([^"`\s]+)["`]',
        r'["`](/api/[a-zA-Z0-9_\-/\.?=&%]+)["`]',  # /api/ 로 시작하는 경로만 (오탐 감소)
    ]

    for js_file in js_dir.rglob("*.js"):
        try:
            content = js_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern in JS_PATTERNS:
            for m in re.finditer(pattern, content):
                val = m.group(1)
                if val.startswith("/") and len(val) > 1 and " " not in val and len(val) < 200:
                    js_endpoints.add(val)

    return {
        "endpoints_from_urls":  sorted(endpoints_url),
        "endpoints_from_forms": sorted(form_actions),
        "endpoints_from_js":    sorted(js_endpoints),
        "params_from_urls":     sorted(params_url),
        "params_from_forms":    sorted(form_params),
    }


def save_endpoints_txt(data: dict, output_file: Path):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Endpoint / Parameter Report\n")
        f.write(f"# Target    : {data.get('target', '')}\n")
        f.write(f"# Generated : {data.get('timestamp', '')}\n")
        f.write("=" * 60 + "\n\n")

        sections = [
            ("URL에서 추출한 엔드포인트",        "endpoints_from_urls"),
            ("Form action에서 추출한 엔드포인트", "endpoints_from_forms"),
            ("JS 파일에서 추출한 엔드포인트",     "endpoints_from_js"),
            ("URL 쿼리 파라미터",                "params_from_urls"),
            ("Form 입력 파라미터",               "params_from_forms"),
        ]

        for title, key in sections:
            items = data.get(key, [])
            f.write(f"[{title}]  ({len(items)} 개)\n")
            f.write("-" * 40 + "\n")
            for item in items:
                f.write(f"  {item}\n")
            f.write("\n")

        js_files = data.get("js_files_downloaded", [])
        f.write(f"[다운로드된 JS 파일]  ({len(js_files)} 개)\n")
        f.write("-" * 40 + "\n")
        for js in js_files:
            f.write(f"  {js}\n")

    print(f"[+] endpoints.txt 저장: {output_file}")


# ── main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Recon Automation Tool — 탐지 없이 정찰 only",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("url", help="대상 URL  예) https://abc.or.kr/")
    parser.add_argument(
        "--analyze-only", action="store_true",
        help="크롤링 생략, 기존 responses/ 데이터로 분석만 재실행",
    )
    parser.add_argument(
        "--stealth-level", choices=["slow", "normal", "fast"], default="normal",
        help="slow(딜레이 5-10s) / normal(2-5s, 기본값) / fast(1-2s)",
    )
    parser.add_argument(
        "--no-wayback", action="store_true",
        help="Wayback Machine URL 수집 생략",
    )
    parser.add_argument(
        "--no-subdomains", action="store_true",
        help="crt.sh 서브도메인 수집 생략",
    )
    args = parser.parse_args()

    url   = args.url.strip()
    level = args.stealth_level

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    domain = urlparse(url).netloc
    if not domain:
        print("[!] 올바른 URL을 입력하세요.")
        sys.exit(1)

    base_dir      = Path(__file__).parent / domain
    result_file   = base_dir / "result.txt"
    filter_file   = base_dir / "filter_result.txt"
    responses_dir = base_dir / "responses"
    js_dir        = base_dir / "js"

    base_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Recon Automation Tool  [stealth edition]")
    print("=" * 60)
    print(f"[*] 대상          : {url}")
    print(f"[*] 폴더          : {base_dir}")
    print(f"[*] 스텔스 레벨   : {level}  (딜레이 {STEALTH_LEVELS[level]['min']}-{STEALTH_LEVELS[level]['max']}s)")
    if args.analyze_only:
        print(f"[*] 모드          : 분석 전용 (크롤링 생략)")
    print()

    # ── 1단계: katana 크롤링 ──────────────────────────────────────
    if not args.analyze_only:
        if not run_katana(url, result_file, responses_dir, level):
            sys.exit(1)

    if not result_file.exists():
        print("[!] result.txt가 없습니다. 먼저 크롤링을 실행하세요.")
        sys.exit(1)

    all_urls = [
        l.strip()
        for l in result_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        if l.strip()
    ]
    print(f"\n[+] 발견된 URL: {len(all_urls)} 개")

    # ── 2단계: 카테고리 필터링 ────────────────────────────────────
    categories = load_categories(CATEGORY_FILE)
    matched    = filter_urls(all_urls, categories)
    save_filter_result(matched, filter_file, url)

    # ── 3단계: JS 파일 수집 ───────────────────────────────────────
    print(f"\n[*] JS 파일 수집 중 (workers={STEALTH_LEVELS[level]['js_workers']})...")
    downloaded_js = collect_js_files(responses_dir, js_dir, domain, url, level)
    print(f"[+] JS 파일 다운로드 완료: {len(downloaded_js)} 개")

    # ── 4단계: 엔드포인트 / 파라미터 ─────────────────────────────
    print(f"\n[*] 엔드포인트/파라미터 추출 중...")
    endpoint_data = extract_endpoints(responses_dir, js_dir, all_urls)
    endpoint_data["target"]              = url
    endpoint_data["timestamp"]           = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    endpoint_data["js_files_downloaded"] = downloaded_js

    with open(base_dir / "endpoints.json", "w", encoding="utf-8") as f:
        json.dump(endpoint_data, f, ensure_ascii=False, indent=2)
    print(f"[+] endpoints.json 저장: {base_dir / 'endpoints.json'}")
    save_endpoints_txt(endpoint_data, base_dir / "endpoints.txt")

    # ── 5단계: 서브도메인 수집 (crt.sh) ──────────────────────────
    subdomains = []
    if not args.no_subdomains:
        print()
        root_domain = ".".join(domain.split(".")[-2:])
        subdomains = collect_subdomains_crtsh(root_domain, base_dir / "subdomains.txt", level)

    # ── 6단계: Wayback Machine URL ────────────────────────────────
    wayback_urls = []
    if not args.no_wayback:
        print()
        root_domain = ".".join(domain.split(".")[-2:])
        wayback_urls = collect_wayback_urls(root_domain, base_dir / "wayback_urls.txt", level)

    # ── 7단계: JS 시크릿 탐지 ────────────────────────────────────
    print()
    secrets = detect_js_secrets(
        js_dir, responses_dir,
        base_dir / "secrets.txt",
        base_dir / "secrets.json",
    )

    # ── 8단계: 보안 헤더 + 기술 스택 ─────────────────────────────
    print()
    analyze_security_and_tech(url, responses_dir, base_dir / "security_headers.txt", level)

    # ── 최종 요약 ─────────────────────────────────────────────────
    total_matched  = sum(len(v) for v in matched.values())
    response_count = len([f for f in responses_dir.rglob("*") if f.is_file()])
    secret_counts  = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for items in secrets.values():
        for item in items:
            secret_counts[item["confidence"]] += 1

    print()
    print("=" * 60)
    print("  완료 요약")
    print(f"  전체 URL           : {len(all_urls)}")
    print(f"  필터 매칭          : {total_matched}")
    print(f"  저장된 응답        : {response_count} 파일")
    print(f"  JS 파일            : {len(downloaded_js)} 개")
    print(f"  서브도메인 (alive) : {len(subdomains)} 개")
    print(f"  Wayback URL        : {len(wayback_urls)} 개")
    print(f"  시크릿 HIGH        : {secret_counts['HIGH']} 개")
    print(f"  시크릿 MEDIUM      : {secret_counts['MEDIUM']} 개")
    print(f"  시크릿 LOW         : {secret_counts['LOW']} 개")
    print(f"  엔드포인트(URL)    : {len(endpoint_data['endpoints_from_urls'])}")
    print(f"  엔드포인트(Form)   : {len(endpoint_data['endpoints_from_forms'])}")
    print(f"  엔드포인트(JS)     : {len(endpoint_data['endpoints_from_js'])}")
    print(f"  파라미터(URL)      : {len(endpoint_data['params_from_urls'])}")
    print(f"  파라미터(Form)     : {len(endpoint_data['params_from_forms'])}")
    print(f"  저장 경로          : {base_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
