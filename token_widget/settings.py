"""Janela de configurações do widget.

Toda mudança é aplicada na hora no widget; o arquivo de configuração é
gravado ao fechar a janela.
"""

from gi.repository import Gtk


class SettingsWindow(Gtk.Window):
    def __init__(self, widget):
        super().__init__(title="Token Widget — Configurações")
        self.tw = widget
        cfg = widget.cfg

        self.set_border_width(18)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.connect("delete-event", self.on_close)

        grid = Gtk.Grid(column_spacing=16, row_spacing=12)
        row = 0

        def label(text, row, hint=None):
            lbl = Gtk.Label(label=text, xalign=0)
            if hint:
                lbl.set_tooltip_text(hint)
            grid.attach(lbl, 0, row, 1, 1)

        def section(text, row):
            lbl = Gtk.Label(xalign=0)
            lbl.set_markup(f"<b>{text}</b>")
            grid.attach(lbl, 0, row, 2, 1)

        # ---- aparência
        section("Aparência", row); row += 1

        label("Opacidade do fundo", row)
        opacity = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.2, 1.0, 0.05)
        opacity.set_value(float(cfg.get("opacity", 0.88)))
        opacity.set_size_request(200, -1)
        opacity.set_value_pos(Gtk.PositionType.RIGHT)
        opacity.connect("format-value", lambda _s, v: f"{v * 100:.0f}%")
        opacity.connect("value-changed", self.on_opacity)
        grid.attach(opacity, 1, row, 1, 1); row += 1

        label("Sempre na frente", row, "Desligado: o widget fica no fundo, atrás das janelas.")
        top = Gtk.Switch(halign=Gtk.Align.START)
        top.set_active(bool(cfg.get("always_on_top")))
        top.connect("notify::active", self.on_top)
        grid.attach(top, 1, row, 1, 1); row += 1

        # ---- atualização
        section("Atualização", row); row += 1
        label("Atualizar a cada (segundos)", row)
        refresh = Gtk.SpinButton.new_with_range(10, 3600, 10)
        refresh.set_value(int(cfg.get("refresh_seconds", 60)))
        refresh.connect("value-changed", self.on_refresh)
        grid.attach(refresh, 1, row, 1, 1); row += 1

        # ---- metas
        section("Meta diária (mil tokens, 0 = sem meta)", row); row += 1
        budget = cfg.get("daily_budget") or {}
        for key, name in (("claude", "Claude"), ("gemini", "Gemini")):
            label(name, row)
            spin = Gtk.SpinButton.new_with_range(0, 100_000_000, 100)
            spin.set_value(int(budget.get(key, 0)) // 1000)
            spin.connect("value-changed", self.on_budget, key)
            grid.attach(spin, 1, row, 1, 1); row += 1

        close = Gtk.Button(label="Fechar", halign=Gtk.Align.END)
        close.connect("clicked", lambda *_: self.on_close())
        grid.attach(close, 1, row, 1, 1)

        self.add(grid)
        self.show_all()

    # ---------------------------------------------------- aplicar na hora
    def on_opacity(self, scale):
        self.tw.cfg["opacity"] = round(scale.get_value(), 2)
        self.tw.area.queue_draw()

    def on_top(self, switch, _param):
        # o item do menu cuida de aplicar e salvar
        self.tw.top_item.set_active(switch.get_active())

    def on_refresh(self, spin):
        self.tw.set_refresh(spin.get_value_as_int())

    def on_budget(self, spin, key):
        budgets = dict(self.tw.cfg.get("daily_budget") or {})
        budgets[key] = spin.get_value_as_int() * 1000
        self.tw.cfg["daily_budget"] = budgets
        self.tw.area.queue_draw()

    def on_close(self, *_):
        from .widget import save_config
        save_config(self.tw.cfg)
        self.tw.settings_win = None
        self.destroy()
        return True
