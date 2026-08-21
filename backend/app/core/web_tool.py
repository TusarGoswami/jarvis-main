import re
import httpx
from typing import Dict, Any, List
from urllib.parse import quote_plus

async def search_and_scrape(query: str, max_results: int = 3) -> Dict[str, Any]:
    """
    Performs a live web search via DuckDuckGo and scrapes summary snippets.
    Returns cleaned text results and citations into context.
    """
    clean_q = query.strip()
    if not clean_q:
        return {"status": "error", "action": "web_search", "message": "Query cannot be empty."}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(clean_q)}"
    
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "action": "web_search",
                    "query": clean_q,
                    "message": f"Search engine returned status {resp.status_code}"
                }
            
            html = resp.text
            
            # Simple regex parser for DuckDuckGo HTML results
            results: List[Dict[str, str]] = []
            snippet_blocks = re.findall(
                r'<a class="result__snippet[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                html,
                re.DOTALL
            )
            title_blocks = re.findall(
                r'<a class="result__url[^"]*"[^>]*>(.*?)</a>',
                html,
                re.DOTALL
            )

            # Fallback extraction
            raw_snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
            raw_links = re.findall(r'<a class="result__url[^"]*"[^>]*href="([^"]+)"[^>]*>', html, re.DOTALL)

            for i in range(min(max_results, len(raw_snippets))):
                clean_snippet = re.sub(r'<[^>]+>', '', raw_snippets[i]).strip()
                link = raw_links[i] if i < len(raw_links) else ""
                results.append({
                    "snippet": clean_snippet,
                    "url": link
                })

            if not results:
                # Text fallback
                clean_text = re.sub(r'<[^>]+>', ' ', html)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                return {
                    "status": "success",
                    "action": "web_search",
                    "query": clean_q,
                    "results": [{"snippet": clean_text[:500], "url": "https://duckduckgo.com"}],
                    "total": 1
                }

            return {
                "status": "success",
                "action": "web_search",
                "query": clean_q,
                "results": results,
                "total": len(results)
            }
    except Exception as e:
        return {
            "status": "error",
            "action": "web_search",
            "query": clean_q,
            "message": str(e)
        }
