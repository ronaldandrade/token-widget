"""Agregações usadas pelo widget."""

from collections import defaultdict
from datetime import date, timedelta


def local_day(u):
    return u.ts.astimezone().date()


def summarize(usages, days=7):
    """Retorna dict por provider com hoje, semana, mês e série diária."""
    today = date.today()
    start_series = today - timedelta(days=days - 1)
    month_start = today.replace(day=1)

    result = {}
    for prov in ("claude", "gemini"):
        result[prov] = {
            "today": defaultdict(int),
            "week": 0,
            "month": 0,
            "series": [0] * days,
            "models_today": defaultdict(int),
        }

    for u in usages:
        r = result.get(u.provider)
        if r is None:
            continue
        d = local_day(u)
        if d == today:
            r["today"]["input"] += u.input
            r["today"]["output"] += u.output
            r["today"]["cache"] += u.cache_read + u.cache_write
            r["today"]["total"] += u.total
            r["models_today"][u.model] += u.total
        if d >= today - timedelta(days=6):
            r["week"] += u.total
        if d >= month_start:
            r["month"] += u.total
        if d >= start_series:
            r["series"][(d - start_series).days] += u.total
    return result


def fmt(n):
    n = float(n)
    for unit in ("", "k", "M", "B"):
        if abs(n) < 1000:
            return f"{n:.0f}{unit}" if unit == "" else f"{n:.1f}{unit}"
        n /= 1000
    return f"{n:.1f}T"
