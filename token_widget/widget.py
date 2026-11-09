"""Widget de desktop (GTK3 + cairo) com o gasto de tokens de Claude e Gemini.

- Janela sem borda, transparente, fica abaixo das outras e em todos os workspaces.
- Arraste com o botão esquerdo para mover (a posição fica salva).
- Botão direito: atualizar / sair.
"""

import json
import math
import os
import signal
from datetime import date, timedelta

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from . import collectors, stats  # noqa: E402
from .settings import SettingsWindow  # noqa: E402

CONFIG_PATH = os.path.expanduser("~/.config/token-widget/config.json")
DEFAULT_CONFIG = {
    "x": None,
    "y": None,
    "refresh_seconds": 60,
    "opacity": 0.88,
    # True = fica na frente das outras janelas; False = fica no fundo (desktop).
    "always_on_top": False,
    # Nomes amigáveis para os ids numéricos de modelo do Antigravity.
    "gemini_model_names": {},
    # Meta diária opcional (tokens). 0 = sem barra de meta.
    "daily_budget": {"claude": 0, "gemini": 0},
}

W, PAD = 300, 16
SECTION_H = 128
PROVIDERS = [
    # (chave, rótulo, cor RGB)
    ("claude", "Claude", (0.85, 0.47, 0.34)),
    ("gemini", "Gemini", (0.40, 0.58, 0.96)),
]
DAY_LETTERS = "STQQSSD"  # seg..dom


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            cfg.update(json.load(fh))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)


def rounded_rect(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


class TokenWidget(Gtk.Window):
    def __init__(self):
        super().__init__(title="Token Widget")
        self.cfg = load_config()
        self.data = None
        self.updated_at = None

        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.apply_layer()
        self.stick()
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)

        height = PAD * 2 + 26 + SECTION_H * len(PROVIDERS)
        self.set_default_size(W, height)
        self.set_size_request(W, height)

        area = Gtk.DrawingArea()
        area.connect("draw", self.on_draw)
        self.add(area)
        self.area = area

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self.on_click)
        self.connect("configure-event", self.on_configure)
        self.connect("destroy", Gtk.main_quit)

        self.settings_win = None
        self.menu = Gtk.Menu()
        cfg_item = Gtk.MenuItem(label="Configurações…")
        cfg_item.connect("activate", lambda *_: self.open_settings())
        self.menu.append(cfg_item)
        top = Gtk.CheckMenuItem(label="Sempre na frente")
        top.set_active(bool(self.cfg.get("always_on_top")))
        top.connect("toggled", self.on_toggle_top)
        self.menu.append(top)
        self.top_item = top
        for label, cb in (("Atualizar", lambda *_: self.refresh()),
                          ("Sair", lambda *_: Gtk.main_quit())):
            item = Gtk.MenuItem(label=label)
            item.connect("activate", cb)
            self.menu.append(item)
        self.menu.show_all()

        self.place()
        self.refresh()
        self._timer = None
        self.set_refresh(self.cfg["refresh_seconds"])

    # ---------------------------------------------------------------- janela
    def place(self):
        if self.cfg.get("x") is not None and self.cfg.get("y") is not None:
            self.move(self.cfg["x"], self.cfg["y"])
        else:
            geo = Gdk.Display.get_default().get_primary_monitor() or \
                Gdk.Display.get_default().get_monitor(0)
            r = geo.get_workarea()
            self.move(r.x + r.width - W - 24, r.y + 24)

    def set_refresh(self, seconds):
        seconds = max(10, int(seconds))
        self.cfg["refresh_seconds"] = seconds
        if self._timer:
            GLib.source_remove(self._timer)
        self._timer = GLib.timeout_add_seconds(seconds, self.refresh)

    def open_settings(self):
        if self.settings_win:
            self.settings_win.present()
        else:
            self.settings_win = SettingsWindow(self)

    def apply_layer(self):
        on_top = bool(self.cfg.get("always_on_top"))
        self.set_keep_below(not on_top)
        self.set_keep_above(on_top)

    def on_toggle_top(self, item):
        self.cfg["always_on_top"] = item.get_active()
        self.apply_layer()
        save_config(self.cfg)

    def on_configure(self, *_):
        x, y = self.get_position()
        if (x, y) != (self.cfg.get("x"), self.cfg.get("y")):
            self.cfg["x"], self.cfg["y"] = x, y
            # grava com atraso para não escrever a cada pixel do arraste
            if getattr(self, "_save_src", None):
                GLib.source_remove(self._save_src)
            self._save_src = GLib.timeout_add(800, self._save_pos)
        return False

    def _save_pos(self):
        self._save_src = None
        save_config(self.cfg)
        return False

    def on_click(self, _w, ev):
        if ev.button == 1:
            self.begin_move_drag(ev.button, int(ev.x_root), int(ev.y_root), ev.time)
        elif ev.button == 3:
            self.menu.popup_at_pointer(ev)
        return True

    # ----------------------------------------------------------------- dados
    def refresh(self):
        usages = collectors.claude_usage() + \
            collectors.gemini_usage(self.cfg.get("gemini_model_names"))
        self.data = stats.summarize(usages)
        self.updated_at = GLib.DateTime.new_now_local().format("%H:%M")
        self.area.queue_draw()
        return True

    # --------------------------------------------------------------- desenho
    def on_draw(self, _area, cr):
        alloc_w = self.get_allocated_width()
        alloc_h = self.get_allocated_height()

        cr.set_operator(0)  # CLEAR
        cr.paint()
        cr.set_operator(2)  # OVER

        rounded_rect(cr, 0, 0, alloc_w, alloc_h, 14)
        cr.set_source_rgba(0.09, 0.10, 0.12, self.cfg.get("opacity", 0.88))
        cr.fill()

        cr.select_font_face("Sans")
        y = PAD + 12
        cr.set_font_size(11)
        cr.set_source_rgba(1, 1, 1, 0.55)
        cr.move_to(PAD, y)
        cr.show_text("TOKENS DE IA")
        if self.updated_at:
            txt = f"atualizado {self.updated_at}"
            ext = cr.text_extents(txt)
            cr.move_to(alloc_w - PAD - ext.width, y)
            cr.show_text(txt)
        y += 14

        if not self.data:
            return
        for key, label, color in PROVIDERS:
            self.draw_provider(cr, PAD, y, alloc_w - 2 * PAD, key, label, color)
            y += SECTION_H

    def draw_provider(self, cr, x, y, w, key, label, color):
        d = self.data[key]
        today = d["today"]

        # separador
        cr.set_source_rgba(1, 1, 1, 0.08)
        cr.rectangle(x, y + 4, w, 1)
        cr.fill()

        # nome + bolinha
        cr.set_source_rgb(*color)
        cr.arc(x + 5, y + 22, 4.5, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.set_font_size(13)
        cr.move_to(x + 16, y + 27)
        cr.show_text(label)

        # total de hoje à direita
        cr.set_font_size(22)
        big = stats.fmt(today.get("total", 0))
        ext = cr.text_extents(big)
        cr.move_to(x + w - ext.width - ext.x_bearing, y + 30)
        cr.show_text(big)
        cr.set_font_size(10)
        cr.set_source_rgba(1, 1, 1, 0.5)
        hoje = "hoje"
        e2 = cr.text_extents(hoje)
        cr.move_to(x + w - ext.width - e2.width - 8, y + 30)
        cr.show_text(hoje)

        # detalhe in / out / cache
        cr.set_font_size(10.5)
        cr.set_source_rgba(1, 1, 1, 0.6)
        cr.move_to(x + 16, y + 46)
        cr.show_text(
            f"in {stats.fmt(today.get('input', 0))}  ·  "
            f"out {stats.fmt(today.get('output', 0))}  ·  "
            f"cache {stats.fmt(today.get('cache', 0))}"
        )

        # meta diária opcional
        budget = (self.cfg.get("daily_budget") or {}).get(key) or 0
        bar_top = y + 54
        if budget:
            frac = min(1.0, today.get("total", 0) / budget)
            rounded_rect(cr, x, bar_top, w, 4, 2)
            cr.set_source_rgba(1, 1, 1, 0.1)
            cr.fill()
            if frac > 0:
                rounded_rect(cr, x, bar_top, max(4, w * frac), 4, 2)
                cr.set_source_rgb(*((0.93, 0.33, 0.31) if frac >= 1 else color))
                cr.fill()

        # barras dos últimos 7 dias
        series = d["series"]
        chart_top, chart_h = y + 66, 34
        n = len(series)
        gap = 6
        bw = (w - 110 - gap * (n - 1)) / n
        peak = max(series) or 1
        start = date.today() - timedelta(days=n - 1)
        for i, v in enumerate(series):
            bx = x + i * (bw + gap)
            h = max(2, chart_h * v / peak) if v else 2
            rounded_rect(cr, bx, chart_top + chart_h - h, bw, h, min(3, bw / 2))
            alpha = 1.0 if i == n - 1 else 0.55
            cr.set_source_rgba(*color, alpha if v else 0.15)
            cr.fill()
            cr.set_font_size(8.5)
            cr.set_source_rgba(1, 1, 1, 0.4)
            letter = DAY_LETTERS[(start + timedelta(days=i)).weekday()]
            le = cr.text_extents(letter)
            cr.move_to(bx + bw / 2 - le.width / 2, chart_top + chart_h + 12)
            cr.show_text(letter)

        # semana / mês
        sx = x + w - 96
        for j, (lbl, val) in enumerate((("7 dias", d["week"]), ("mês", d["month"]))):
            ty = chart_top + 6 + j * 24
            cr.set_font_size(9)
            cr.set_source_rgba(1, 1, 1, 0.45)
            cr.move_to(sx, ty)
            cr.show_text(lbl)
            cr.set_font_size(13)
            cr.set_source_rgba(1, 1, 1, 0.85)
            v = stats.fmt(val)
            ve = cr.text_extents(v)
            cr.move_to(x + w - ve.width - ve.x_bearing, ty + 1)
            cr.show_text(v)


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    win = TokenWidget()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
