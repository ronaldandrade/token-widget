"""Cota da sessão do Gemini, consultada no Google com o login do Antigravity CLI.

O agy guarda o token OAuth no chaveiro do sistema (Secret Service, serviço
"gemini", usuário "antigravity"). Usamos esse token para chamar os mesmos
endpoints que o agy chama (não documentados):

  loadCodeAssist        -> descobre o projeto da conta
  fetchAvailableModels  -> cada modelo traz quotaInfo {remainingFraction, resetTime}

O token dura ~1 h e só o agy o renova. Com o token vencido, o widget mostra o
último valor salvo em ~/.cache/token-widget/gemini-quota.json.
"""

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime

try:  # libsecret é opcional: sem ele, só a cota do Gemini fica indisponível
    import gi

    gi.require_version("Secret", "1")
    from gi.repository import Secret  # noqa: E402
except (ImportError, ValueError):
    Secret = None

BASE = "https://daily-cloudcode-pa.googleapis.com/v1internal:"
CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
                         "token-widget")
CACHE = os.path.join(CACHE_DIR, "gemini-quota.json")

_SCHEMA = Secret.Schema.new(
    "org.freedesktop.Secret.Generic", Secret.SchemaFlags.DONT_MATCH_NAME,
    {"service": Secret.SchemaAttributeType.STRING,
     "username": Secret.SchemaAttributeType.STRING}) if Secret else None

_user_agent = None
_project = None


def _agy_user_agent():
    """O servidor só reconhece o cliente com o User-Agent do antigravity."""
    global _user_agent
    if _user_agent is None:
        version = "1.5.3"
        agy = shutil.which("agy") or os.path.expanduser("~/.local/bin/agy")
        try:
            out = subprocess.run([agy, "--version"], capture_output=True, text=True, timeout=10)
            if out.returncode == 0 and out.stdout.strip():
                version = out.stdout.split()[0]
        except (OSError, subprocess.SubprocessError):
            pass
        _user_agent = f"antigravity/{version} linux/amd64"
    return _user_agent


def _access_token():
    if Secret is None:
        return None, "no_secret"
    raw = Secret.password_lookup_sync(
        _SCHEMA, {"service": "gemini", "username": "antigravity"}, None)
    if not raw:
        return None, "no_login"
    tok = json.loads(raw).get("token") or {}
    expiry = tok.get("expiry")
    if expiry:
        # "2026-11-09T20:15:06.44528432-03:00": corta a fração para o fromisoformat
        base, _, rest = expiry.partition(".")
        tz = rest[next((i for i, c in enumerate(rest) if c in "+-"), len(rest)):]
        try:
            exp = datetime.fromisoformat(base + tz).timestamp()
        except ValueError:
            exp = None
        if exp and exp < time.time() + 30:
            return None, "token_expired"
    return tok.get("access_token"), None


def _call(method, body, token):
    req = urllib.request.Request(
        BASE + method, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json",
                 "User-Agent": _agy_user_agent()})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def _parse_time(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return None


def fetch():
    """Consulta o Google e grava o cache. Devolve (dados, código de erro)."""
    global _project
    token, err = _access_token()
    if not token:
        return None, err
    try:
        if not _project:
            info = _call("loadCodeAssist", {"metadata": {"ideType": "ANTIGRAVITY"}}, token)
            _project = info.get("cloudaicompanionProject")
            if not _project:
                return None, "no_project"
        models = _call("fetchAvailableModels", {"project": _project}, token).get("models") or {}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"[token-widget] cota do Gemini: {exc}")
        return None, "fetch_failed"

    # Os modelos Gemini compartilham a mesma cota; pega o pior caso entre eles.
    best = None
    for model_id, m in models.items():
        q = m.get("quotaInfo") or {}
        if not model_id.startswith("gemini") or "resetTime" not in q:
            continue
        frac = float(q.get("remainingFraction", 1))
        if best is None or frac < best[0]:
            best = (frac, q["resetTime"], model_id)
    if best is None:
        return None, "no_model"

    data = {
        "saved_at": time.time(),
        "five_hour": {
            "used_percentage": round((1 - best[0]) * 100, 1),
            "resets_at": _parse_time(best[1]),
        },
        "model": best[2],
    }
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = CACHE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh)
    os.replace(tmp, CACHE)
    return data, None


def cached():
    try:
        with open(CACHE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    win = data.get("five_hour")
    if win:
        win["renewed"] = bool(win.get("resets_at")) and win["resets_at"] <= time.time()
    return data


if __name__ == "__main__":
    print(fetch())
