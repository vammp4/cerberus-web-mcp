#!/usr/bin/env python3
"""
Cerberus Web MCP Server v2.1 (cerberus-web) — Security & Token Hardened Edition
Architecture: 3-Head Tri-Hybrid (Scout / Probe / Breach)

Defensive Components:
1. URLSanitizer: Strips analytics & spy query parameters (utm_*, fbclid, gclid, si).
2. CircuitBreaker: In-memory cooldown tracker for 429/rate-limited endpoints (0.001s fast-path).
3. TokenBombDefuser: Scrubs zero-width characters and invisible token-bloat unicode.
4. SanitizerShield: Neutralizes indirect prompt injections and encapsulates web text in safety boundaries.
"""

import sys
import os
import re
import json
import time
import socket
import asyncio
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Ensure UTF-8 on Windows; Stdio MCP requires stdout to be strictly JSON-RPC.
# Any diagnostic logging MUST go to stderr.
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

from master_fetch.server import MasterFetchServer
import trafilatura

try:
    from mcp.server.fastmcp import FastMCP
    app = FastMCP(
        name="cerberus-web",
        instructions="Cerberus Web MCP: Ultra low-token web intelligence, Cloudflare bypass, YouTube subtitles, and interactive browser automation."
    )
except ImportError:
    from mcp.server.mcpserver import MCPServer
    app = MCPServer(
        name="cerberus-web",
        instructions="Cerberus Web MCP: Ultra low-token web intelligence, Cloudflare bypass, YouTube subtitles, and interactive browser automation."
    )

hound_server = MasterFetchServer()
URL_REGEX = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
SESSIONS_DIR = Path.home() / ".cerberus" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def debug_log(msg: str):
    """Outputs diagnostic messages strictly to stderr so MCP stdio stream is never corrupted."""
    print(f"[cerberus] {msg}", file=sys.stderr, flush=True)


# ==============================================================================
# DEFENSIVE COMPONENT 1: URL Sanitizer & Canonicalizer
# ==============================================================================
class URLSanitizer:
    """Strips tracking, referral, and fingerprinting parameters while preserving legitimate query state."""
    
    TRACKING_KEYS = {
        "fbclid", "gclid", "gbraid", "wbraid", "dclid",
        "si", "_hsenc", "_hsmi", "mc_cid", "mc_eid", "igshid",
        "spm", "scm", "ref_src", "ref_url"
    }

    @classmethod
    def sanitize(cls, url: str) -> str:
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.query:
                return url

            query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            clean_pairs = []
            for k, v in query_pairs:
                k_lower = k.lower()
                # Drop all utm_* keys and blacklisted ad parameters
                if k_lower.startswith("utm_") or k_lower in cls.TRACKING_KEYS:
                    continue
                clean_pairs.append((k, v))

            clean_query = urllib.parse.urlencode(clean_pairs)
            return urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                clean_query,
                parsed.fragment
            ))
        except Exception:
            return url


# ==============================================================================
# DEFENSIVE COMPONENT 2: Token Bomb Defuser (Zero-Width Scrubber)
# ==============================================================================
class TokenBombDefuser:
    """Eliminates zero-width characters and invisible unicode that bloats token counts."""

    # Matches zero-width spaces, joiners, formatting characters, soft hyphens
    ZERO_WIDTH_REGEX = re.compile(r'[\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFEFF\u00AD]')

    @classmethod
    def defuse(cls, text: str) -> str:
        if not text:
            return ""
        # 1. Remove zero-width characters
        cleaned = cls.ZERO_WIDTH_REGEX.sub('', text)
        # 2. Collapse excessive whitespace
        cleaned = re.sub(r'[ \t]{4,}', '    ', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()


# ==============================================================================
# DEFENSIVE COMPONENT 3: Anti-Prompt-Injection Shield
# ==============================================================================
class SanitizerShield:
    """Neutralizes indirect prompt injections embedded in scraped text."""

    INJECTION_PATTERNS = [
        re.compile(r'(?i)\b(system\s+override|system\s+instruction|system\s+prompt)\b'),
        re.compile(r'(?i)\b(ignore\s+(all\s+)?(previous|prior)\s+instructions?)\b'),
        re.compile(r'(?i)\b(disregard\s+(all\s+)?(previous|prior)\s+instructions?)\b'),
        re.compile(r'(?i)\b(you\s+are\s+now\s+in\s+developer\s+mode)\b'),
        re.compile(r'(?i)\b(new\s+system\s+directive:)\b'),
    ]

    @classmethod
    def protect(cls, raw_text: str, source_url: str = "") -> str:
        if not raw_text:
            return ""

        # Step 1: Defuse active prompt injection markers
        safe_text = raw_text
        for pattern in cls.INJECTION_PATTERNS:
            safe_text = pattern.sub('[DEFUSED: PROMPT INJECTION MARKER REDACTED]', safe_text)

        # Step 2: Encapsulate in defensive boundary tags
        return (
            f"<untrusted_web_content source=\"{source_url}\">\n"
            f"{safe_text}\n"
            f"</untrusted_web_content>"
        )


# ==============================================================================
# DEFENSIVE COMPONENT 4: Smart Circuit Breaker (Rate-Limit Memory)
# ==============================================================================
class CircuitBreaker:
    """In-memory cooldown tracker to immediately bypass 429/rate-limited APIs (0.001s fast-path)."""

    def __init__(self):
        self._cooldowns: Dict[str, float] = {}

    def is_tripped(self, target: str) -> bool:
        expire_time = self._cooldowns.get(target, 0)
        if time.time() < expire_time:
            return True
        if target in self._cooldowns:
            del self._cooldowns[target]
        return False

    def trip(self, target: str, cooldown_seconds: int = 900):
        self._cooldowns[target] = time.time() + cooldown_seconds
        debug_log(f"Circuit tripped for '{target}'! In cooldown for {cooldown_seconds}s.")

    def get_remaining_cooldown(self, target: str) -> int:
        expire_time = self._cooldowns.get(target, 0)
        remaining = int(expire_time - time.time())
        return max(0, remaining)


circuit_breaker = CircuitBreaker()


def clean_and_defend_text(raw_content: Any, source_url: str = "") -> str:
    """Normalizes content, defuses token bombs, and protects against prompt injection."""
    if isinstance(raw_content, list):
        joined = "\n\n".join(str(item) for item in raw_content)
    else:
        joined = str(raw_content or "")

    # 1. Defuse zero-width characters
    defused = TokenBombDefuser.defuse(joined)
    # 2. Apply security encapsulation shield
    return SanitizerShield.protect(defused, source_url)


def get_session_file(url: str) -> Path:
    """Generates an isolated, safe session state path per host to prevent concurrency collisions."""
    try:
        netloc = urllib.parse.urlparse(url).netloc.replace(":", "_") or "general"
    except Exception:
        netloc = "general"
    return SESSIONS_DIR / f"{netloc}_state.json"


# ─── HEAD 1: SCOUT (SEARCH & RETRIEVAL) ─────────────────────────────

async def search_ddg_lite(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Fast DDG Lite HTML stream search (0.5s - 1.0s latency)."""
    q_encoded = urllib.parse.quote_plus(query)
    url = f"https://lite.duckduckgo.com/lite/?q={q_encoded}"
    try:
        res = await asyncio.wait_for(
            hound_server.smart_fetch(url=url, timeout=4000, extraction_type="text"),
            timeout=4.5
        )
        text = clean_and_defend_text(getattr(res, "content", ""), url)
    except Exception as e:
        debug_log(f"DDG Lite search failed: {e}")
        return []

    results = []
    blocks = re.split(r'\|\s*(\d+)\.\s*\|', text)
    i = 1
    while i < len(blocks) - 1:
        content_block = blocks[i + 1]
        rows = [r.strip().strip('|').strip() for r in content_block.split('\n') if r.strip().strip('|').strip()]
        rows = [r for r in rows if len(r) > 3]

        title, snippet, found_url = "", "", ""
        if len(rows) >= 1:
            title = re.sub(r'\s*\\\|.*$', '', rows[0]).replace('**', '').strip()
        if len(rows) >= 2:
            snippet = rows[1].replace('**', '').strip()[:250]
        if len(rows) >= 3:
            raw_url = re.sub(r'^[\s|]+', '', rows[2]).strip()
            if not raw_url.startswith('http'):
                raw_url = f"https://{raw_url}"
            # Apply URL sanitizer
            found_url = URLSanitizer.sanitize(raw_url)

        if title and found_url:
            results.append({"title": title, "url": found_url, "snippet": snippet})
        if len(results) >= max_results:
            break
        i += 2

    return results


async def fetch_cascading(url: str, focus: Optional[str] = None) -> Dict[str, Any]:
    """
    Self-Healing Cascading Retrieval with Full Security Suite:
    Tier 0: DNS Pre-Flight Check (0.02s) to fail fast on dead domains.
    Tier 1: Fast HTTP + Rust TLS primp (1-2s).
    Tier 2: Patchright C++ Stealth (Cloudflare Turnstile bypass).
    Tier 3: Wayback Archive Mirror.
    """
    clean_url = URLSanitizer.sanitize(url)

    # ── Tier 0: Fast DNS verification
    try:
        host = urllib.parse.urlparse(clean_url).netloc.split(':')[0]
        if host:
            socket.gethostbyname(host)
    except socket.gaierror:
        return {
            "ok": False,
            "tier": "dns_preflight",
            "status": 0,
            "url": clean_url,
            "error": f"DNS resolution failed: Host '{host}' does not exist on the network."
        }

    # Check Circuit Breaker for host
    if circuit_breaker.is_tripped(host):
        remaining = circuit_breaker.get_remaining_cooldown(host)
        debug_log(f"Host '{host}' is in Circuit Breaker cooldown ({remaining}s remaining). Skipping direct HTTP.")
        # Fast-track directly to Tier 2 or Tier 3
    else:
        # ── Tier 1: Fast HTTP with Rust TLS
        try:
            res = await asyncio.wait_for(
                hound_server.smart_fetch(
                    url=clean_url,
                    extraction_type="markdown",
                    use_trafilatura=True,
                    focus=focus,
                    timeout=4000,
                    max_content_chars=35000,
                    solve_cloudflare=False
                ),
                timeout=4.5
            )
            raw_content = getattr(res, "content", "")
            status = getattr(res, "status", 200)

            if status in [404, 410]:
                return {
                    "ok": False,
                    "tier": "http_fast",
                    "status": status,
                    "url": clean_url,
                    "error": f"Resource not found (HTTP {status}). Aborting escalation."
                }

            if status == 429:
                circuit_breaker.trip(host, cooldown_seconds=900)

            raw_str = str(raw_content).lower()
            is_bot_blocked = (
                status in [403, 429, 503] or
                "challenge-platform" in raw_str or
                "attention required" in raw_str or
                "just a moment" in raw_str or
                (len(str(raw_content)) < 80 and status != 200)
            )

            if not is_bot_blocked and len(str(raw_content)) >= 80:
                protected_content = clean_and_defend_text(raw_content, clean_url)
                return {
                    "ok": True,
                    "tier": "http_fast",
                    "status": status,
                    "url": clean_url,
                    "tokens_est": len(protected_content) // 4,
                    "content": protected_content
                }
        except Exception as e:
            debug_log(f"Tier 1 error for {clean_url}: {e}")

    # ── Tier 2: Patchright Stealth Browser
    debug_log(f"Escalating {clean_url} to Tier 2 (Patchright Stealth)...")
    try:
        from master_fetch.browser import StealthyBrowser
        state_file = get_session_file(clean_url)

        session = StealthyBrowser(
            headless=True, solve_cloudflare=True,
            hide_canvas=True, block_webrtc=True, timeout=8000
        )
        try:
            await asyncio.wait_for(session.start(), timeout=5.0)
            await asyncio.wait_for(session.fetch(clean_url, solve_cloudflare=True, wait=1500), timeout=8.0)
            await session._context.storage_state(path=str(state_file))

            page = session._context.pages[0] if session._context.pages else None
            html_content = await page.content() if page else ""
        finally:
            try:
                await asyncio.wait_for(session.close(), timeout=2.0)
            except Exception:
                pass

        clean_md = (trafilatura.extract(html_content, output_format="markdown") or "").strip()
        if len(clean_md) >= 80:
            protected_content = clean_and_defend_text(clean_md, clean_url)
            return {
                "ok": True,
                "tier": "stealth_patchright",
                "status": 200,
                "url": clean_url,
                "tokens_est": len(protected_content) // 4,
                "content": protected_content,
                "state_file": str(state_file)
            }
    except Exception as e:
        debug_log(f"Tier 2 failed: {e}")

    # ── Tier 3: Wayback Archive Mirror
    debug_log(f"Attempting Tier 3 (Archive fallback) for {clean_url}...")
    try:
        arch_res = await asyncio.wait_for(
            hound_server.smart_fetch(
                url=f"https://web.archive.org/web/{clean_url}",
                extraction_type="markdown", use_trafilatura=True, timeout=4000
            ),
            timeout=4.5
        )
        arch_content = getattr(arch_res, "content", "")
        if len(str(arch_content)) >= 100:
            protected_content = clean_and_defend_text(arch_content, clean_url)
            return {
                "ok": True,
                "tier": "archive_mirror",
                "status": 200,
                "url": clean_url,
                "tokens_est": len(protected_content) // 4,
                "content": protected_content
            }
    except Exception as e:
        debug_log(f"Tier 3 failed: {e}")

    return {
        "ok": False,
        "tier": "exhausted",
        "url": clean_url,
        "error": "All retrieval tiers exhausted. Target unreachable or actively blocked."
    }


# ─── HEAD 2: PROBE (SPECIALIST EXTRACTOR) ───────────────────────────

async def probe_platform(platform: str, target: str, action: str = "read", lang: str = "uk,en,en-orig") -> Dict[str, Any]:
    """Extracts from YouTube, GitHub, Reddit, Twitter with CircuitBreaker protection."""
    plat = platform.lower().strip()
    act = action.lower().strip()
    clean_target = URLSanitizer.sanitize(target)

    # Check CircuitBreaker
    breaker_key = f"{plat}:{act}"
    if circuit_breaker.is_tripped(breaker_key):
        rem = circuit_breaker.get_remaining_cooldown(breaker_key)
        debug_log(f"Probe '{breaker_key}' is in CircuitBreaker cooldown ({rem}s). Fast-falling back to Hound...")
        fallback_res = await fetch_cascading(clean_target)
        return {"ok": fallback_res.get("ok", False), "source": "hound_circuit_breaker", "data": fallback_res}

    args = [plat, act, clean_target]
    if plat == "youtube" and act == "subtitle":
        args.extend(["--lang", lang])

    try:
        import subprocess
        proc = await asyncio.to_thread(
            subprocess.run,
            ["agent-reach"] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10
        )
        stdout_text = proc.stdout.strip()
        json_match = re.search(r'(\{[\s\S]*\})', stdout_text)
        if json_match:
            data = json.loads(json_match.group(1))
            if data.get("ok"):
                # Apply TokenDefuser and SanitizerShield on items
                for item in data.get("items", []):
                    if "text" in item:
                        item["text"] = clean_and_defend_text(item["text"], clean_target)
                return {"ok": True, "source": "agent_reach", "data": data}

            # Check if platform rate-limited us
            err = data.get("error", {})
            if isinstance(err, dict) and err.get("code") == "RATE_LIMITED":
                circuit_breaker.trip(breaker_key, cooldown_seconds=1200)

            debug_log(f"Agent-Reach returned error: {err}")
    except Exception as e:
        debug_log(f"Specialist probe error: {e}")

    # Triangular Fallback to Head 1 (Hound)
    debug_log(f"Triangular fallback: passing {clean_target} to Head 1 (Hound)...")
    fallback_res = await fetch_cascading(clean_target)
    return {
        "ok": fallback_res.get("ok", False),
        "source": "hound_fallback",
        "data": fallback_res
    }


# ─── HEAD 3: BREACH (INTERACTIVE DOM & STATE GENERATOR) ─────────────

async def prepare_breach_state(url: str) -> Dict[str, Any]:
    """Generates Playwright-compatible storageState with Cloudflare clearance."""
    from master_fetch.browser import StealthyBrowser
    clean_url = URLSanitizer.sanitize(url)
    state_file = get_session_file(clean_url)

    session = StealthyBrowser(
        headless=True, solve_cloudflare=True,
        hide_canvas=True, block_webrtc=True, timeout=12000
    )
    try:
        await asyncio.wait_for(session.start(), timeout=5.0)
        await asyncio.wait_for(session.fetch(clean_url, solve_cloudflare=True, wait=1500), timeout=10.0)
        await session._context.storage_state(path=str(state_file))
        cookies = await session._context.cookies()

        return {
            "ok": True,
            "url": clean_url,
            "state_file": str(state_file),
            "cookies_count": len(cookies),
            "cf_clearance": any(c.get("name") == "cf_clearance" for c in cookies),
            "message": f"Session cleared and saved to {state_file.name}. Playwright MCP can now enter without CAPTCHA."
        }
    except Exception as e:
        return {"ok": False, "url": clean_url, "error": str(e)}
    finally:
        try:
            await asyncio.wait_for(session.close(), timeout=2.0)
        except Exception:
            pass


# ==============================================================================
# MCP EXPOSED TOOLS
# ==============================================================================

@app.tool()
async def cerberus_query(query_or_url: str, focus: str = "") -> str:
    """
    Universal Web Intelligence Engine (Cerberus Head 1: Scout).
    Protected against prompt injection, zero-width token bombs, and tracking params.
    """
    input_str = query_or_url.strip()
    urls = URL_REGEX.findall(input_str)

    if urls:
        raw_target = urls[0] if urls[0].startswith("http") else f"https://{urls[0]}"
        target_url = URLSanitizer.sanitize(raw_target)
        focus_term = focus or URL_REGEX.sub("", input_str).strip()
        res = await fetch_cascading(target_url, focus=focus_term or None)
        return json.dumps(res, ensure_ascii=False, indent=2)

    # Search mode
    search_results = await search_ddg_lite(input_str, max_results=4)
    if not search_results:
        return json.dumps({"ok": False, "query": input_str, "error": "No search results found."}, ensure_ascii=False)

    top_url = search_results[0]["url"]
    page_data = await fetch_cascading(top_url, focus=input_str)

    return json.dumps({
        "ok": True,
        "query": input_str,
        "search_results": search_results,
        "top_source": page_data
    }, ensure_ascii=False, indent=2)


@app.tool()
async def cerberus_social_probe(platform: str, target: str, action: str = "read", lang: str = "uk,en,en-orig") -> str:
    """
    Walled Garden Specialist (Cerberus Head 2: Probe).
    Equipped with CircuitBreaker rate-limit memory and content sanitization.
    """
    res = await probe_platform(platform, target, action, lang)
    return json.dumps(res, ensure_ascii=False, indent=2)


@app.tool()
async def cerberus_breach_prep(url: str) -> str:
    """
    Interactive Breach Preparation (Cerberus Head 3: Breach Bridge).
    Solves Cloudflare Turnstile on target URL, saves authenticated cookies,
    and enables Playwright MCP to interact without triggering CAPTCHAs.
    """
    res = await prepare_breach_state(url)
    return json.dumps(res, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    app.run(transport="stdio")
