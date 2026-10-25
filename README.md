# Cerberus Web MCP 🐺

> **3-рівнева система веб-інтелекту для AI-агентів**  
> Захищена від prompt injection, оптимізована по токенах, обходить Cloudflare.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Що це?

Cerberus — це персональний MCP-сервер який дає будь-якому AI-агенту (Claude Code, Cursor, Windsurf, Antigravity) повноцінний доступ до веба через три спеціалізовані голови:

| Інструмент | Голова | Що вміє |
|---|---|---|
| `cerberus_query` | 🔍 Scout | Пошук + 4-рівневий waterfall fetch (DNS → HTTP → Stealth Chrome → Archive) |
| `cerberus_social_probe` | 🎯 Probe | YouTube субтитри, GitHub репо, Reddit, Twitter через Agent-Reach |
| `cerberus_breach_prep` | 🔥 Breach | Вирішує Cloudflare Turnstile, зберігає сесію для Playwright MCP |

### Захисні компоненти (завжди активні)

- **URLSanitizer** — зрізає `utm_*`, `fbclid`, `gclid`, `si` трекери
- **TokenBombDefuser** — вилучає невидимі zero-width Unicode символи (захист від 10k–50k token bloat)
- **SanitizerShield** — нейтралізує indirect prompt injection, ізолює зовнішній контент
- **CircuitBreaker** — in-memory захист від 429/rate-limit з 0.002ms fast-path

---

## Встановлення

### Залежності

```bash
# Обов'язково
pip install hound-mcp trafilatura primp

# Голова 2: Agent-Reach
pip install agent-reach

# Голова 3: Стелс браузер (одне з двох)
pip install patchright
# АБО
npm install -g @playwright/mcp
```

### Підключення до AI-клієнта

Додай у конфіг свого клієнта:

**Antigravity / Cursor / Windsurf** (`~/.gemini/config/mcp_config.json` / `~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "cerberus-web": {
      "type": "stdio",
      "command": "/path/to/python3",
      "args": ["/path/to/cerberus_server.py"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

**Claude Code** (`~/.claude.json`):
```json
{
  "mcpServers": {
    "cerberus-web": {
      "type": "stdio",
      "command": "/path/to/python3",
      "args": ["/path/to/cerberus_server.py"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

### Автономне встановлення через AI-агента

Скопіюй вміст `PROMPT_FOR_ANY_AGENT.txt` і відправ будь-якому AI-агенту — він сам знайде шляхи, перевірить компоненти і зареєструє сервер у свій конфіг.

---

## Перевірка встановлення

```bash
python audit_env.py
```

Очікуваний результат: `"all_heads_operational": true`

```bash
# E2E тест протоколу MCP
python -c "
import subprocess, json
p = subprocess.Popen(['python', 'cerberus_server.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
req = json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'1.0'}}}) + chr(10)
out, _ = p.communicate(input=req, timeout=5)
print(json.loads(out)['result']['serverInfo'])
"
```

---

## Використання

Дивись `cerberus_power_prompts.md` — повна бібліотека промптів українською з прикладами для кожної голови.

Найпростіший старт:

```
Використай cerberus_query щоб знайти [тема] і дай мені резюме.
```

---

## Структура файлів

```
cerberus_server.py          # MCP сервер v2.1 — всі 3 голови + 4 захисні компоненти
audit_env.py                # Діагностика оточення (0.05s)
install_cerberus.py         # Автоінсталятор для Antigravity, Claude Code, Cursor, Windsurf
CERBERUS_ONBOARDING.md      # Runbook для автономних AI-агентів
PROMPT_FOR_ANY_AGENT.txt    # Промпт для делегування встановлення будь-якому агенту
cerberus_power_prompts.md   # Бібліотека промптів для максимального використання
```

---

## Сумісність

| Клієнт | Статус |
|---|---|
| Antigravity CLI / IDE | ✅ |
| Claude Code | ✅ |
| Cursor IDE | ✅ |
| Windsurf IDE | ✅ |
| Codex CLI | ✅ |
| OpenCode | ✅ |

---

## Ліцензія

MIT — вільне використання, модифікація та поширення.
