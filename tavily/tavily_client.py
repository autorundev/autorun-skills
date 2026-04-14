#!/usr/bin/env python3
"""Tavily API client for extract and search operations."""

import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/vectoros/.env"))

API_KEY = os.environ.get("TAVILY_API_KEY", "")
BASE_URL = "https://api.tavily.com"


def extract(urls: list[str]) -> None:
    if not API_KEY:
        print("ERROR: TAVILY_API_KEY not set. Add it to ~/vectoros/.env")
        sys.exit(1)

    resp = requests.post(
        f"{BASE_URL}/extract",
        json={"api_key": API_KEY, "urls": urls},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    for result in data.get("results", []):
        print(f"\n## {result.get('url', 'unknown')}\n")
        print(result.get("raw_content", result.get("content", "No content")))


def search(query: str) -> None:
    if not API_KEY:
        print("ERROR: TAVILY_API_KEY not set. Add it to ~/vectoros/.env")
        sys.exit(1)

    resp = requests.post(
        f"{BASE_URL}/search",
        json={
            "api_key": API_KEY,
            "query": query,
            "search_depth": "basic",
            "include_raw_content": False,
            "max_results": 5,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    for r in data.get("results", []):
        print(f"\n## {r.get('title', '')}")
        print(f"URL: {r.get('url', '')}")
        print(r.get("content", ""))


def main():
    if len(sys.argv) < 3:
        print("Usage: tavily_client.py extract|search <url_or_query> [url2 ...]")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "extract":
        extract(sys.argv[2:])
    elif mode == "search":
        search(sys.argv[2])
    else:
        print(f"Unknown mode: {mode}. Use 'extract' or 'search'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
