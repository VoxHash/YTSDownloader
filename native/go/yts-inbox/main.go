// yts-inbox: concurrent companion inbox consumer for YTSDownloader.
// Reads drop files and JSONL in parallel (outside the Python GIL), prints NDJSON items.
//
// Usage:
//
//	yts-inbox consume --inbox DIR --jsonl PATH
//
// Each stdout line: {"url":"...","title":"...","source":"...","page_url":"..."}
package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
)

var urlRe = regexp.MustCompile(`(?i)https?://[^\s<>"']+`)

type item struct {
	URL     string `json:"url"`
	Title   string `json:"title,omitempty"`
	Source  string `json:"source,omitempty"`
	PageURL string `json:"page_url,omitempty"`
}

func main() {
	if len(os.Args) < 2 {
		fatal("usage: yts-inbox consume --inbox DIR --jsonl PATH")
	}
	cmd := os.Args[1]
	fs := flag.NewFlagSet(cmd, flag.ExitOnError)
	inbox := fs.String("inbox", "", "companion inbox directory")
	jsonl := fs.String("jsonl", "", "companion NDJSON append path")
	_ = fs.Parse(os.Args[2:])

	switch cmd {
	case "consume":
		items := consume(*inbox, *jsonl)
		enc := json.NewEncoder(os.Stdout)
		enc.SetEscapeHTML(false)
		seen := map[string]struct{}{}
		for _, it := range items {
			if it.URL == "" {
				continue
			}
			if _, ok := seen[it.URL]; ok {
				continue
			}
			seen[it.URL] = struct{}{}
			_ = enc.Encode(it)
		}
	default:
		fatal("unknown command: " + cmd)
	}
}

func fatal(msg string) {
	fmt.Fprintln(os.Stderr, msg)
	os.Exit(1)
}

func consume(inboxDir, jsonlPath string) []item {
	var (
		mu    sync.Mutex
		out   []item
		wg    sync.WaitGroup
		files []string
	)

	if inboxDir != "" {
		entries, err := os.ReadDir(inboxDir)
		if err == nil {
			for _, e := range entries {
				if e.IsDir() {
					continue
				}
				name := e.Name()
				if strings.HasPrefix(name, ".") || strings.HasSuffix(name, ".processed") {
					continue
				}
				lower := strings.ToLower(name)
				ok := false
				for _, suf := range []string{".txt", ".url", ".json", ".jsonl", ".urls"} {
					if strings.HasSuffix(lower, suf) {
						ok = true
						break
					}
				}
				if !ok {
					continue
				}
				files = append(files, filepath.Join(inboxDir, name))
			}
		}
	}

	for _, path := range files {
		path := path
		wg.Add(1)
		go func() {
			defer wg.Done()
			data, err := os.ReadFile(path)
			if err != nil {
				return
			}
			parsed := parsePayload(string(data))
			mu.Lock()
			out = append(out, parsed...)
			mu.Unlock()
			_ = markProcessed(path)
		}()
	}
	wg.Wait()

	if jsonlPath != "" {
		if data, err := os.ReadFile(jsonlPath); err == nil && len(strings.TrimSpace(string(data))) > 0 {
			out = append(out, parsePayload(string(data))...)
			_ = os.WriteFile(jsonlPath, []byte{}, 0o644)
		}
	}
	return out
}

func markProcessed(path string) error {
	target := path + ".processed"
	_ = os.Remove(target)
	if err := os.Rename(path, target); err != nil {
		return os.Remove(path)
	}
	return nil
}

func parsePayload(text string) []item {
	text = strings.TrimSpace(text)
	if text == "" {
		return nil
	}
	if text[0] == '{' || text[0] == '[' {
		var v any
		if err := json.Unmarshal([]byte(text), &v); err == nil {
			switch t := v.(type) {
			case map[string]any:
				if it := itemFromMap(t); it != nil {
					return []item{*it}
				}
				for _, key := range []string{"urls", "items", "links"} {
					if arr, ok := t[key].([]any); ok {
						return itemsFromList(arr)
					}
				}
			case []any:
				return itemsFromList(t)
			}
		}
	}

	var out []item
	sawJSON := false
	sc := bufio.NewScanner(strings.NewReader(text))
	// Allow long companion lines.
	buf := make([]byte, 0, 64*1024)
	sc.Buffer(buf, 1024*1024)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if line[0] == '{' || line[0] == '[' {
			var v any
			if err := json.Unmarshal([]byte(line), &v); err == nil {
				sawJSON = true
				switch t := v.(type) {
				case map[string]any:
					if it := itemFromMap(t); it != nil {
						out = append(out, *it)
					}
				case []any:
					out = append(out, itemsFromList(t)...)
				case string:
					if it := itemFromURL(t, "", "", ""); it != nil {
						out = append(out, *it)
					}
				}
				continue
			}
		}
		for _, u := range extractURLs(line) {
			out = append(out, item{URL: u})
		}
	}
	if !sawJSON && len(out) == 0 {
		for _, u := range extractURLs(text) {
			out = append(out, item{URL: u})
		}
	}
	return out
}

func itemsFromList(values []any) []item {
	var out []item
	for _, v := range values {
		switch t := v.(type) {
		case string:
			if it := itemFromURL(t, "", "", ""); it != nil {
				out = append(out, *it)
			}
		case map[string]any:
			if it := itemFromMap(t); it != nil {
				out = append(out, *it)
			}
		}
	}
	return out
}

func itemFromMap(m map[string]any) *item {
	urlStr := strField(m, "url", "href", "media_url")
	title := strField(m, "title", "name")
	source := strField(m, "source", "origin")
	page := strField(m, "page_url", "referrer")
	return itemFromURL(urlStr, title, source, page)
}

func strField(m map[string]any, keys ...string) string {
	for _, k := range keys {
		if v, ok := m[k]; ok {
			if s, ok := v.(string); ok {
				return s
			}
		}
	}
	return ""
}

func itemFromURL(raw, title, source, page string) *item {
	urls := extractURLs(raw)
	if len(urls) == 0 {
		return nil
	}
	return &item{
		URL:     urls[0],
		Title:   strings.TrimSpace(title),
		Source:  strings.TrimSpace(source),
		PageURL: strings.TrimSpace(page),
	}
}

func extractURLs(text string) []string {
	matches := urlRe.FindAllString(text, -1)
	seen := map[string]struct{}{}
	var out []string
	for _, m := range matches {
		m = strings.TrimRight(m, ").,;]'\"")
		u, err := url.Parse(m)
		if err != nil || (u.Scheme != "http" && u.Scheme != "https") || u.Host == "" {
			continue
		}
		if _, ok := seen[m]; ok {
			continue
		}
		seen[m] = struct{}{}
		out = append(out, m)
	}
	return out
}
