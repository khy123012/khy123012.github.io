import subprocess
import sys
import re
import json
import shutil
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# 기존 category.txt 재사용
CATEGORY_FILE = Path(__file__).parent / "category.txt"

# katana 경로 설정
# PATH에 katana가 등록되어 있으면 그대로 사용됩니다.
# 없을 경우 아래 경로를 직접 지정하세요.
# 예) KATANA_PATH = r"C:\Tools\katana\katana.exe"
KATANA_PATH = r"katana"


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

def run_katana(url: str, result_file: Path, responses_dir: Path) -> bool:
    print(f"[*] 크롤링 시작: {url}")
    katana_bin = shutil.which("katana") or KATANA_PATH

    cmd = [
        katana_bin,
        "-u", url,
        "-o", str(result_file),
        "-store-response",
        "-store-response-dir", str(responses_dir),
        "-fs", "fqdn",
        "-d", "3",
    ]

    try:
        subprocess.run(cmd, check=True)
        return True
    except FileNotFoundError:
        print("[!] katana를 찾을 수 없습니다. PATH를 확인하세요.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"[!] katana 오류: {e}")
        return False


# ── JS 파일 수집 ──────────────────────────────────────────────────

def collect_js_files(responses_dir: Path, js_dir: Path, target_domain: str, base_url: str) -> list[str]:
    """HTML responses에서 <script src> 추출 → JS 파일 다운로드"""
    js_dir.mkdir(parents=True, exist_ok=True)

    script_urls: set[str] = set()

    for html_file in responses_dir.rglob("*.txt"):
        try:
            content = html_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for match in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE):
            src = match.group(1).strip()
            if not src or src.startswith("data:"):
                continue
            # 프로토콜 정규화
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

    downloaded: list[str] = []
    seen_names: dict[str, int] = {}

    for js_url in sorted(script_urls):
        name = Path(urlparse(js_url).path).name or "script.js"
        if not name.endswith(".js"):
            name += ".js"

        # 파일명 중복 처리
        if name in seen_names:
            seen_names[name] += 1
            stem, ext = name.rsplit(".", 1)
            name = f"{stem}_{seen_names[name]}.{ext}"
        else:
            seen_names[name] = 0

        save_path = js_dir / name
        print(f"  [JS] {js_url}")

        try:
            req = urllib.request.Request(js_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                save_path.write_bytes(resp.read())
            downloaded.append(js_url)
            print(f"       → {save_path.name} ({save_path.stat().st_size:,} bytes)")
        except Exception as e:
            print(f"       [!] 실패: {e}")

    return downloaded


# ── 엔드포인트 / 파라미터 구조화 ─────────────────────────────────

def extract_endpoints(responses_dir: Path, js_dir: Path, all_urls: list[str]) -> dict:
    endpoints_url: set[str] = set()
    params_url: set[str] = set()
    form_actions: set[str] = set()
    form_params: set[str] = set()
    js_endpoints: set[str] = set()

    # ① katana result.txt URL → path / query param 분리
    for url in all_urls:
        parsed = urlparse(url)
        if parsed.path and parsed.path != "/":
            endpoints_url.add(parsed.path)
        if parsed.query:
            for param in parse_qs(parsed.query):
                params_url.add(param)

    # ② HTML responses → form action, input name
    for html_file in responses_dir.rglob("*.txt"):
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
            r'<(?:input|select|textarea)[^>]+name=["\']([^"\']+)["\']', content, re.IGNORECASE
        ):
            form_params.add(m.group(1))

    # ③ JS 파일 → API 엔드포인트 패턴
    JS_PATTERNS = [
        r'fetch\s*\(\s*["`]([^"`\s]+)["`]',
        r'axios\.[a-z]+\s*\(\s*["`]([^"`\s]+)["`]',
        r'\$\.(?:get|post|ajax)\s*\(\s*["`]([^"`\s]+)["`]',
        r'url\s*[:=]\s*["`]([^"`\s]+)["`]',
        r'["`](/[a-zA-Z0-9_\-/\.?=&%]+)["`]',
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
        "endpoints_from_urls": sorted(endpoints_url),
        "endpoints_from_forms": sorted(form_actions),
        "endpoints_from_js": sorted(js_endpoints),
        "params_from_urls": sorted(params_url),
        "params_from_forms": sorted(form_params),
    }


def save_endpoints_txt(data: dict, output_file: Path):
    """읽기 쉬운 텍스트 형식으로도 저장"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Endpoint / Parameter Report\n")
        f.write(f"# Target    : {data.get('target', '')}\n")
        f.write(f"# Generated : {data.get('timestamp', '')}\n")
        f.write("=" * 60 + "\n\n")

        sections = [
            ("URL에서 추출한 엔드포인트", "endpoints_from_urls"),
            ("Form action에서 추출한 엔드포인트", "endpoints_from_forms"),
            ("JS 파일에서 추출한 엔드포인트", "endpoints_from_js"),
            ("URL 쿼리 파라미터", "params_from_urls"),
            ("Form 입력 파라미터", "params_from_forms"),
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
    if len(sys.argv) < 2:
        print("사용법: python recon.py <URL> [--analyze-only]")
        print("예시:  python recon.py https://주소/")
        print("       python recon.py https://주소/ --analyze-only  (기존 데이터만 분석)")
        sys.exit(1)

    url = sys.argv[1].strip()
    analyze_only = "--analyze-only" in sys.argv

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    domain = urlparse(url).netloc
    if not domain:
        print("[!] 올바른 URL을 입력하세요.")
        sys.exit(1)

    base_dir     = Path(__file__).parent / domain
    result_file  = base_dir / "result.txt"
    filter_file  = base_dir / "filter_result.txt"
    responses_dir = base_dir / "responses"
    js_dir       = base_dir / "js"

    base_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Recon Automation Tool")
    print("=" * 60)
    print(f"[*] 대상  : {url}")
    print(f"[*] 폴더  : {base_dir}")
    if analyze_only:
        print(f"[*] 모드  : 분석 전용 (크롤링 생략)")
    print()

    # 1단계: katana 크롤링 + 소스코드 저장
    if not analyze_only:
        if not run_katana(url, result_file, responses_dir):
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

    # 2단계: 카테고리 필터링
    categories = load_categories(CATEGORY_FILE)
    matched = filter_urls(all_urls, categories)
    save_filter_result(matched, filter_file, url)

    # 3단계: JS 파일 수집 (responses/*.txt 에서 <script src> 추출 → 다운로드)
    print(f"\n[*] JS 파일 수집 중... (responses/ 내 *.txt 파싱)")
    downloaded_js = collect_js_files(responses_dir, js_dir, domain, url)
    print(f"[+] JS 파일 다운로드 완료: {len(downloaded_js)} 개")

    # 4단계: 엔드포인트 / 파라미터 구조화
    print(f"\n[*] 엔드포인트/파라미터 추출 중...")
    endpoint_data = extract_endpoints(responses_dir, js_dir, all_urls)
    endpoint_data["target"]            = url
    endpoint_data["timestamp"]         = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    endpoint_data["js_files_downloaded"] = downloaded_js

    with open(base_dir / "endpoints.json", "w", encoding="utf-8") as f:
        json.dump(endpoint_data, f, ensure_ascii=False, indent=2)
    print(f"[+] endpoints.json 저장: {base_dir / 'endpoints.json'}")

    save_endpoints_txt(endpoint_data, base_dir / "endpoints.txt")

    # 요약
    total_matched  = sum(len(v) for v in matched.values())
    response_count = len([f for f in responses_dir.rglob("*") if f.is_file()])

    print()
    print("=" * 60)
    print(f"  완료 요약")
    print(f"  전체 URL           : {len(all_urls)}")
    print(f"  필터 매칭          : {total_matched}")
    print(f"  저장된 응답        : {response_count} 파일")
    print(f"  JS 파일            : {len(downloaded_js)} 개")
    print(f"  엔드포인트(URL)    : {len(endpoint_data['endpoints_from_urls'])}")
    print(f"  엔드포인트(Form)   : {len(endpoint_data['endpoints_from_forms'])}")
    print(f"  엔드포인트(JS)     : {len(endpoint_data['endpoints_from_js'])}")
    print(f"  파라미터(URL)      : {len(endpoint_data['params_from_urls'])}")
    print(f"  파라미터(Form)     : {len(endpoint_data['params_from_forms'])}")
    print(f"  저장 경로          : {base_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
