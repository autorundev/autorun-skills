---
name: tavily
description: >
  URL content extraction (extract) and web search (search) via Tavily API. Automatic fallback
  when WebFetch fails. Triggers on: WebFetch returns 403/429/timeout/empty content, "fetch url",
  "extract content from url", "search the web", "web search for".
allowed-tools: Bash
---

# Tavily -- Fallback for WebFetch

Use when WebFetch returns an error (403, 429, timeout), garbled HTML, or empty content.
**Rule:** WebFetch failed → use Tavily immediately, without asking the user.

## Modes

### Extract -- Get content from a URL

```bash
python3 ~/.claude/skills/tavily/tavily_client.py extract "https://example.com/article"
```

Multiple URLs (up to 20):
```bash
python3 ~/.claude/skills/tavily/tavily_client.py extract "URL1" "URL2" "URL3"
```

**Output format:** For each URL, prints a markdown header with the URL followed by the extracted text content.

### Search -- Web search

```bash
python3 ~/.claude/skills/tavily/tavily_client.py search "your search query"
```

**Output format:** Up to 5 results, each with title, URL, and content snippet.

## Setup

Requires `TAVILY_API_KEY` in `~/vectoros/.env`. Get one at https://tavily.com.

**Free tier:** 1,000 requests/month. No credit card required.

If the key is missing, tell the user to add `TAVILY_API_KEY=tvly-xxx` to `~/vectoros/.env`.

## Dependencies

The client script requires `requests` and `python-dotenv`:
```bash
pip3 install requests python-dotenv
```

## Error Handling

| Situation | Action |
|-----------|--------|
| No API key | Tell user to add `TAVILY_API_KEY` to `~/vectoros/.env` |
| URL extraction failed | Report the failure, try a different URL or fall back to search |
| Timeout | Retry once. If still failing, report to user |
| Rate limit (429) | Free tier exhausted for the month. Report to user |

## When to Use Extract vs Search

- **Extract**: You have a specific URL and need its content (article, docs page, blog post)
- **Search**: You need to find information but don't have a specific URL
- **Extract after Search**: Search to find relevant URLs, then extract full content from the best ones
