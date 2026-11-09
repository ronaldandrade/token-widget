"""Coletores de uso de tokens a partir dos arquivos locais.

Cada coletor devolve uma lista de `Usage` (um registro por resposta do modelo).
Os resultados são cacheados por arquivo + mtime, então o refresh periódico só
relê o que mudou.
"""

import glob
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from . import protobuf as pb

CLAUDE_DIR = os.path.expanduser("~/.claude/projects")
ANTIGRAVITY_DIR = os.path.expanduser("~/.gemini/antigravity-cli/conversations")


@dataclass
class Usage:
    provider: str          # "claude" | "gemini"
    model: str
    ts: datetime           # UTC
    input: int = 0         # entrada sem cache
    output: int = 0        # saída (inclui thinking)
    cache_read: int = 0
    cache_write: int = 0

    @property
    def total(self):
        return self.input + self.output + self.cache_read + self.cache_write


_cache = {}  # path -> (mtime, [Usage])


def _cached(path, loader):
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return []
    hit = _cache.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        rows = loader(path)
    except Exception as exc:  # arquivo em escrita, formato novo etc.
        print(f"[token-widget] falha lendo {path}: {exc}")
        rows = hit[1] if hit else []
    _cache[path] = (mtime, rows)
    return rows


# --------------------------------------------------------------------------
# Claude Code: ~/.claude/projects/<projeto>/<sessao>.jsonl (+ subagents/)
# --------------------------------------------------------------------------

def _load_claude(path):
    rows = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"usage"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            msg = d.get("message") or {}
            u = msg.get("usage")
            if not u or msg.get("role") != "assistant":
                continue
            model = msg.get("model") or "?"
            if model == "<synthetic>":
                continue
            # Uma resposta vira várias linhas (uma por bloco de conteúdo),
            # todas com o mesmo id e o mesmo usage; fica a última.
            key = msg.get("id") or d.get("uuid")
            ts = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
            rows[key] = Usage(
                provider="claude",
                model=model,
                ts=ts,
                input=u.get("input_tokens") or 0,
                output=u.get("output_tokens") or 0,
                cache_read=u.get("cache_read_input_tokens") or 0,
                cache_write=u.get("cache_creation_input_tokens") or 0,
            )
    return list(rows.values())


def claude_usage():
    files = glob.glob(os.path.join(CLAUDE_DIR, "**", "*.jsonl"), recursive=True)
    out = []
    for f in files:
        out.extend(_cached(f, _load_claude))
    return out


# --------------------------------------------------------------------------
# Antigravity CLI (Gemini): conversations/<id>.db, tabela `steps`
#
# Estrutura descoberta por engenharia reversa do blob `steps.metadata`:
#   1  -> timestamp {1: segundos, 2: nanos}
#   9  -> uso da chamada ao modelo:
#           1 = id numérico do modelo   2 = input (sem cache)
#           3 = output total            5 = cache read
#           9 = thinking               10 = resposta
# --------------------------------------------------------------------------

def _load_antigravity(path, model_names):
    uri = f"file:{path}?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=1)
    try:
        rows = []
        for (meta,) in con.execute("SELECT metadata FROM steps WHERE metadata IS NOT NULL"):
            try:
                fields = pb.parse(meta)
                usage_raw = pb.first(fields, 9)
                if not isinstance(usage_raw, bytes):
                    continue
                u = dict(pb.parse(usage_raw))
                ts_raw = pb.first(fields, 1)
                secs = dict(pb.parse(ts_raw)).get(1, 0) if ts_raw else 0
            except (ValueError, IndexError):
                continue
            if not isinstance(u.get(2, 0), int):
                continue
            model_id = u.get(1)
            rows.append(Usage(
                provider="gemini",
                model=model_names.get(str(model_id), f"gemini #{model_id}"),
                ts=datetime.fromtimestamp(secs, tz=timezone.utc),
                input=u.get(2, 0),
                output=u.get(3, 0),
                cache_read=u.get(5, 0),
            ))
        return rows
    finally:
        con.close()


def gemini_usage(model_names=None):
    model_names = model_names or {}
    out = []
    for f in glob.glob(os.path.join(ANTIGRAVITY_DIR, "*.db")):
        out.extend(_cached(f, lambda p: _load_antigravity(p, model_names)))
    return out


# --------------------------------------------------------------------------
# Limite da sessão do Claude (gravado pela status line, ver claude_statusline.py)
# --------------------------------------------------------------------------

CLAUDE_LIMITS = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
                             "token-widget", "claude-limits.json")


def claude_limits():
    """Devolve {"five_hour": {...}, "seven_day": {...}, "saved_at": ts} ou None.

    Se a janela já renovou desde a última leitura, marca `renewed=True`
    (o uso real da nova janela só aparece quando o Claude Code rodar de novo)."""
    try:
        with open(CLAUDE_LIMITS, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    now = datetime.now(timezone.utc).timestamp()
    for key in ("five_hour", "seven_day"):
        win = data.get(key)
        if win:
            win["renewed"] = bool(win.get("resets_at")) and win["resets_at"] <= now
    return data
