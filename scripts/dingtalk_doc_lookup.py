#!/usr/bin/env python3
"""Lookup DingTalk official developer docs through the public search API."""

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


SEARCH_URL = "https://open.dingtalk.com/api/open/search"
OSS_DOC_URL = "https://icms-document.oss-cn-beijing.aliyuncs.com/zh-CN/dingtalk/{namespace}/topics/{slug}.html"


def configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def fetch_text(url, timeout=60):
    req = Request(url, headers={"User-Agent": "dingtalk-doc-lookup/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def strip_inline_html(value):
    text = re.sub(r"<[^>]+>", "", value or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def oss_url_from_doc_link(link):
    path = urlparse(link).path
    match = re.search(r"/document/([^/?#]+)/([^/?#]+)", path)
    if not match:
        return ""
    namespace, slug = match.group(1), match.group(2)
    return OSS_DOC_URL.format(namespace=namespace, slug=slug)


class PlainTextHTMLParser(HTMLParser):
    BLOCK_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "tr", "pre", "code", "table", "section"}

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        data = data.strip()
        if data:
            self.parts.append(data)

    def text(self):
        raw = html.unescape(" ".join(self.parts))
        raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
        raw = re.sub(r"\n\s+", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_text(markup):
    parser = PlainTextHTMLParser()
    parser.feed(markup)
    return parser.text()


def search_docs(query, limit):
    url = f"{SEARCH_URL}?keyword={quote(query)}&page=1&pageSize={limit}"
    data = json.loads(fetch_text(url))
    if not data.get("success"):
        raise RuntimeError(f"DingTalk search failed: {data}")
    search_result = data.get("result", {}).get("searchResult", {})
    results = []
    for item in search_result.get("data", []):
        link = item.get("link", "")
        results.append({
            "title": strip_inline_html(item.get("name", "")),
            "summary": strip_inline_html(item.get("desc", "")),
            "link": link,
            "repository": item.get("repository", ""),
            "oss_url": oss_url_from_doc_link(link),
        })
    return {
        "query": query,
        "total": search_result.get("totalCount", len(results)),
        "results": results,
    }


def main():
    configure_stdio()
    parser = argparse.ArgumentParser(description="Lookup DingTalk official developer docs.")
    parser.add_argument("query", help="Natural-language DingTalk API question or search keywords.")
    parser.add_argument("--limit", type=int, default=5, help="Number of search results to return.")
    parser.add_argument("--fetch-first", action="store_true", help="Fetch and extract text from the first result.")
    parser.add_argument("--text-chars", type=int, default=5000, help="Max text chars when fetching the first result.")
    args = parser.parse_args()

    result = search_docs(args.query, max(1, min(args.limit, 20)))
    if args.fetch_first and result["results"]:
        first = result["results"][0]
        if first.get("oss_url"):
            markup = fetch_text(first["oss_url"])
            first["text"] = html_to_text(markup)[: max(500, args.text_chars)]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise
