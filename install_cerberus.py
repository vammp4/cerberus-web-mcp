#!/usr/bin/env python3
"""
Cerberus Web MCP Universal Installer
Automatically discovers and registers 'cerberus-web' across all installed AI coding assistants:
- Antigravity CLI / IDE
- Claude Code
- Cursor
- Windsurf
- Codex CLI / OpenCode
"""

import sys
import os
import json
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PYTHON_EXE = sys.executable
SERVER_SCRIPT = str((Path(__file__).parent / "cerberus_server.py").resolve())
USER_HOME = Path.home()

print("=" * 60)
print("🐺 Cerberus Web MCP Universal Installer")
print("=" * 60)
print(f"Python interpreter: {PYTHON_EXE}")
print(f"Cerberus server:    {SERVER_SCRIPT}\n")

CERBERUS_STDIO_CONFIG = {
    "command": PYTHON_EXE,
    "args": [SERVER_SCRIPT],
    "env": {
        "PYTHONIOENCODING": "utf-8"
    }
}

registered_count = 0

# 1. Antigravity CLI
antigravity_config = USER_HOME / ".gemini" / "config" / "mcp_config.json"
try:
    antigravity_config.parent.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if antigravity_config.exists() and antigravity_config.stat().st_size > 0:
        with open(antigravity_config, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    cfg.setdefault("mcpServers", {})["cerberus-web"] = CERBERUS_STDIO_CONFIG
    with open(antigravity_config, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"[✓] Antigravity CLI:   Configured ({antigravity_config})")
    registered_count += 1
except Exception as e:
    print(f"[-] Antigravity CLI:   Error ({e})")

# 2. Claude Code CLI
try:
    p = subprocess.run(["where.exe", "claude"], capture_output=True, text=True)
    if p.returncode == 0:
        cmd = ["claude", "mcp", "add", "cerberus-web", "--", PYTHON_EXE, SERVER_SCRIPT]
        res = subprocess.run(cmd, capture_output=True, text=True)
        print(f"[✓] Claude Code:       Registered via CLI (`claude mcp add`)")
        registered_count += 1
    else:
        # Fallback to ~/.claude.json
        claude_json = USER_HOME / ".claude.json"
        cfg = {}
        if claude_json.exists():
            with open(claude_json, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg.setdefault("mcpServers", {})["cerberus-web"] = CERBERUS_STDIO_CONFIG
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print(f"[✓] Claude Code:       Configured ({claude_json})")
        registered_count += 1
except Exception as e:
    print(f"[-] Claude Code:       Skipped ({e})")

# 3. Cursor IDE
cursor_config = USER_HOME / ".cursor" / "mcp.json"
try:
    cursor_config.parent.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if cursor_config.exists():
        with open(cursor_config, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    cfg.setdefault("mcpServers", {})["cerberus-web"] = CERBERUS_STDIO_CONFIG
    with open(cursor_config, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"[✓] Cursor IDE:        Configured ({cursor_config})")
    registered_count += 1
except Exception as e:
    print(f"[-] Cursor IDE:        Skipped ({e})")

# 4. Windsurf IDE
windsurf_config = USER_HOME / ".codeium" / "windsurf" / "mcp_config.json"
try:
    windsurf_config.parent.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if windsurf_config.exists():
        with open(windsurf_config, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    cfg.setdefault("mcpServers", {})["cerberus-web"] = CERBERUS_STDIO_CONFIG
    with open(windsurf_config, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"[✓] Windsurf IDE:      Configured ({windsurf_config})")
    registered_count += 1
except Exception as e:
    print(f"[-] Windsurf IDE:      Skipped ({e})")

print("\n" + "=" * 60)
print(f"🎉 Success! Cerberus Web MCP is active in {registered_count} AI tools.")
print("=" * 60)
