#!/usr/bin/env python3
"""
Cerberus Environment & Tool Auditor for Autonomous Agents.
Outputs a clean JSON report of available components, legacy tools, and client configs.
"""

import sys
import os
import json
import shutil
from pathlib import Path

# UTF-8 safety
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def check_import(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False

def check_cli(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def audit():
    server_path = (Path(__file__).parent / "cerberus_server.py").resolve()
    user_home = Path.home()

    # 1. Core Cerberus Components
    hound_installed = check_import("master_fetch")
    patchright_installed = check_import("patchright")
    agent_reach_cli = check_cli("agent-reach")
    playwright_mcp_cli = check_cli("npx") and (user_home / "node_modules" / "@playwright" / "mcp").exists() or check_cli("playwright")

    # 2. Legacy / Existing Browser Tools Check (to deprioritize without deleting)
    legacy_tools = {}
    
    # claude-in-chrome detection
    claude_ext_paths = [
        user_home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Extensions",
        user_home / ".claude" / "extensions",
        user_home / ".config" / "google-chrome" / "Default" / "Extensions"
    ]
    claude_in_chrome_found = False
    for p in claude_ext_paths:
        if p.exists() and any("claude" in item.name.lower() for item in p.iterdir()):
            claude_in_chrome_found = True
            break
    legacy_tools["claude_in_chrome"] = {
        "detected": claude_in_chrome_found or check_cli("claude-in-chrome"),
        "policy": "PRESERVE_AND_DEPRIORITIZE (Keep P3 dormant fallback, do not delete)"
    }
    legacy_tools["playwright_cli"] = {
        "detected": check_cli("playwright-cli"),
        "policy": "PRESERVE_AND_DEPRIORITIZE"
    }

    # 3. Client Config Targets
    client_configs = {
        "antigravity": str(user_home / ".gemini" / "config" / "mcp_config.json"),
        "claude_code": str(user_home / ".claude.json"),
        "cursor": str(user_home / ".cursor" / "mcp.json"),
        "windsurf": str(user_home / ".codeium" / "windsurf" / "mcp_config.json")
    }

    report = {
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "cerberus_server_path": str(server_path),
        "heads_status": {
            "head_1_hound_scout": hound_installed,
            "head_2_agent_reach_probe": agent_reach_cli,
            "head_3_breach_patchright": patchright_installed
        },
        "all_heads_operational": bool(hound_installed and agent_reach_cli and patchright_installed),
        "legacy_tools_audit": legacy_tools,
        "client_config_targets": client_configs,
        "recommended_mcp_config": {
            "cerberus-web": {
                "command": sys.executable,
                "args": [str(server_path)],
                "env": {
                    "PYTHONIOENCODING": "utf-8"
                }
            }
        }
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    audit()
