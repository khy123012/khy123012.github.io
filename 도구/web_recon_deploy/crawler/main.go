package main

import (
	"bufio"
	"flag"
	"fmt"
	"math"
	"os"
	"sync"

	"github.com/projectdiscovery/katana/pkg/engine/standard"
	"github.com/projectdiscovery/katana/pkg/output"
	"github.com/projectdiscovery/katana/pkg/types"
)

func main() {
	targetURL  := flag.String("u", "", "대상 URL (필수)")
	outputFile := flag.String("o", "", "URL 목록 저장 파일")
	storeDir   := flag.String("store-response-dir", "", "HTTP 응답 저장 디렉토리")
	depth      := flag.Int("d", 3, "최대 크롤링 깊이")
	delay      := flag.Int("delay", 2, "요청 간 딜레이 (초)")
	rateLimit  := flag.Int("rate-limit", 10, "초당 최대 요청 수")
	jsCrawl    := flag.Bool("jc", true, "JS 파일 내 엔드포인트 크롤링")
	userAgent  := flag.String("ua", "", "User-Agent 헤더")
	flag.Parse()

	if *targetURL == "" {
		fmt.Fprintln(os.Stderr, "사용법: crawler -u <url> [-o <output>] [-store-response-dir <dir>] ...")
		os.Exit(1)
	}

	var (
		mu   sync.Mutex
		urls []string
	)

	headers := []string{}
	if *userAgent != "" {
		headers = append(headers, "User-Agent: "+*userAgent)
	}

	options := &types.Options{
		URLs:             []string{*targetURL},
		MaxDepth:         *depth,
		FieldScope:       "fqdn",
		BodyReadSize:     math.MaxInt,
		Timeout:          30,
		Concurrency:      10,
		Parallelism:      10,
		Delay:            *delay,
		RateLimit:        *rateLimit,
		Strategy:         "depth-first",
		JSCrawl:          *jsCrawl,
		CustomHeaders:    headers,
		StoreResponse:    *storeDir != "",
		StoreResponseDir: *storeDir,
		OnResult: func(result output.Result) {
			u := result.Request.URL
			mu.Lock()
			urls = append(urls, u)
			mu.Unlock()
			fmt.Println(u) // stdout 실시간 출력 (진행 확인용)
		},
	}

	crawlerOptions, err := types.NewCrawlerOptions(options)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] 옵션 초기화 실패: %v\n", err)
		os.Exit(1)
	}
	defer crawlerOptions.Close()

	crawler, err := standard.New(crawlerOptions)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] 크롤러 초기화 실패: %v\n", err)
		os.Exit(1)
	}
	defer crawler.Close()

	if err = crawler.Crawl(*targetURL); err != nil {
		fmt.Fprintf(os.Stderr, "[!] 크롤링 오류 (%s): %v\n", *targetURL, err)
	}

	if *outputFile != "" {
		f, err := os.Create(*outputFile)
		if err != nil {
			fmt.Fprintf(os.Stderr, "[!] 출력 파일 생성 실패: %v\n", err)
			os.Exit(1)
		}
		defer f.Close()
		w := bufio.NewWriter(f)
		for _, u := range urls {
			fmt.Fprintln(w, u)
		}
		_ = w.Flush()
	}

	fmt.Fprintf(os.Stderr, "[+] 크롤링 완료: %d URL 발견\n", len(urls))
}
