"""Status line do Claude Code que também alimenta o Token Widget.

O Claude Code chama este script passando um JSON no stdin. Dele tiramos
`rate_limits` (uso da sessão de 5 h e da semana, com horário de renovação),
salvamos em ~/.cache/token-widget/claude-limits.json e imprimimos uma linha
curta para a barra de status.
"""

import json
import os
import sys
import time
from datetime import datetime

CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
                     "token-widget", "claude-limits.json")


def parse_reset(value):
    """Aceita epoch (s ou ms) ou ISO 8601; devolve epoch em segundos."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value / 1000 if value > 1e12 else value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def window(raw):
    if not isinstance(raw, dict):
        return None
    pct = raw.get("used_percentage")
    if pct is None:
        return None
    return {"used_percentage": float(pct), "resets_at": parse_reset(raw.get("resets_at"))}


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    limits = data.get("rate_limits") or {}
    out = {
        "saved_at": time.time(),
        "five_hour": window(limits.get("five_hour")),
        "seven_day": window(limits.get("seven_day")),
    }

    if out["five_hour"] or out["seven_day"]:
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            tmp = CACHE + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(out, fh)
            os.replace(tmp, CACHE)
        except OSError:
            pass

    parts = []
    model = (data.get("model") or {}).get("display_name")
    if model:
        parts.append(model)
    s = out["five_hour"]
    if s:
        txt = f"sessão {s['used_percentage']:.0f}%"
        if s["resets_at"]:
            txt += " · renova " + datetime.fromtimestamp(s["resets_at"]).strftime("%H:%M")
        parts.append(txt)
    w = out["seven_day"]
    if w:
        parts.append(f"semana {w['used_percentage']:.0f}%")
    print("  |  ".join(parts))


if __name__ == "__main__":
    main()
