"""Textos da interface em português e inglês.

`language` no config.json: "auto" (segue o LANG do sistema), "pt" ou "en".
"""

import os

STRINGS = {
    "pt": {
        "title": "TOKENS DE IA",
        "updated": "atualizado {time}",
        "today": "hoje",
        "days7": "7 dias",
        "month": "mês",
        "days": "STQQSSD",  # segunda..domingo
        "session_claude": "sessão (5 h)",
        "session_gemini": "cota da sessão",
        "renewed": "renovada · abra {app}",
        "resets": "renova {time}",
        "week": "semana {pct}",
        "stale": "dado antigo",
        "budget": "meta diária",
        "claude_no_data": "sessão: abra o Claude Code para carregar",
        "gemini_off": "cota: desligada (botão direito → Configurações)",
        "gemini_loading": "consultando…",
        "gemini_err": "cota: {msg}",
        "gerr_no_secret": "instale gir1.2-secret-1",
        "gerr_no_login": "sem login do agy no chaveiro",
        "gerr_token_expired": "token do agy vencido (abra o agy)",
        "gerr_no_project": "conta sem projeto do Code Assist",
        "gerr_fetch_failed": "falha na consulta",
        "gerr_no_model": "nenhum modelo Gemini com cota",
        "menu_settings": "Configurações…",
        "menu_on_top": "Sempre na frente",
        "menu_refresh": "Atualizar",
        "menu_quit": "Sair",
        "set_title": "Token Widget — Configurações",
        "set_appearance": "Aparência",
        "set_language": "Idioma",
        "set_lang_auto": "Automático (sistema)",
        "set_opacity": "Opacidade do fundo",
        "set_on_top": "Sempre na frente",
        "set_on_top_tip": "Desligado: o widget fica no fundo, atrás das janelas.",
        "set_gemini": "Gemini",
        "set_gemini_quota": "Cota da sessão via login do agy",
        "set_gemini_quota_tip": "Usa o login do Antigravity CLI (chaveiro do sistema) para consultar "
                                "a cota no Google, pelos mesmos endpoints não oficiais que o agy usa. "
                                "Podem mudar sem aviso.",
        "set_refresh_section": "Atualização",
        "set_refresh": "Atualizar a cada (segundos)",
        "set_budget": "Meta diária manual (mil tokens, 0 = sem meta)",
        "set_budget_hint": "Só aparece quando não há limite de sessão.",
        "set_close": "Fechar",
        "sl_session": "sessão {pct}",
        "sl_resets": "renova {time}",
        "sl_week": "semana {pct}",
    },
    "en": {
        "title": "AI TOKENS",
        "updated": "updated {time}",
        "today": "today",
        "days7": "7 days",
        "month": "month",
        "days": "MTWTFSS",
        "session_claude": "session (5 h)",
        "session_gemini": "session quota",
        "renewed": "reset · open {app}",
        "resets": "resets {time}",
        "week": "week {pct}",
        "stale": "stale",
        "budget": "daily budget",
        "claude_no_data": "session: open Claude Code to load",
        "gemini_off": "quota: off (right click → Settings)",
        "gemini_loading": "loading…",
        "gemini_err": "quota: {msg}",
        "gerr_no_secret": "install gir1.2-secret-1",
        "gerr_no_login": "no agy login in keyring",
        "gerr_token_expired": "agy token expired (open agy)",
        "gerr_no_project": "account has no Code Assist project",
        "gerr_fetch_failed": "request failed",
        "gerr_no_model": "no Gemini model with quota",
        "menu_settings": "Settings…",
        "menu_on_top": "Always on top",
        "menu_refresh": "Refresh",
        "menu_quit": "Quit",
        "set_title": "Token Widget — Settings",
        "set_appearance": "Appearance",
        "set_language": "Language",
        "set_lang_auto": "Automatic (system)",
        "set_opacity": "Background opacity",
        "set_on_top": "Always on top",
        "set_on_top_tip": "Off: the widget stays on the desktop, behind other windows.",
        "set_gemini": "Gemini",
        "set_gemini_quota": "Session quota via agy login",
        "set_gemini_quota_tip": "Uses the Antigravity CLI login (system keyring) to ask Google for "
                                "the quota, through the same undocumented endpoints agy uses. "
                                "They may change without notice.",
        "set_refresh_section": "Refresh",
        "set_refresh": "Refresh every (seconds)",
        "set_budget": "Manual daily budget (thousand tokens, 0 = none)",
        "set_budget_hint": "Shown only when there is no session limit.",
        "set_close": "Close",
        "sl_session": "session {pct}",
        "sl_resets": "resets {time}",
        "sl_week": "week {pct}",
    },
}

APP_NAMES = {"claude": "Claude Code", "gemini": "agy"}

_lang = "pt"


def system_language():
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            return "pt" if value.lower().startswith("pt") else "en"
    return "en"


def set_language(choice):
    global _lang
    _lang = choice if choice in STRINGS else system_language()


def t(key, **kw):
    text = STRINGS[_lang].get(key) or STRINGS["en"].get(key) or key
    return text.format(**kw) if kw else text
