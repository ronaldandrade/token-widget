#!/bin/sh
# Instala o Token Widget: comando `token-widget`, abertura no login do GNOME e,
# se você quiser, a status line do Claude Code que informa o limite da sessão.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PY=/usr/bin/python3

# ---- dependências
if ! $PY -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' 2>/dev/null; then
  echo "Falta o GTK3 para Python. Instale com:"
  echo "  sudo apt install python3-gi gir1.2-gtk-3.0"
  exit 1
fi
if ! $PY -c 'import gi; gi.require_version("Secret", "1")' 2>/dev/null; then
  echo "Aviso: sem gir1.2-secret-1 a cota do Gemini fica indisponível (o resto funciona)."
  echo "  sudo apt install gir1.2-secret-1"
fi
if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
  echo "Aviso: sessão Wayland. O widget foi feito para X11; mover, fixar no fundo e"
  echo "lembrar a posição podem não funcionar. Na tela de login, escolha 'Ubuntu on Xorg'."
fi

# ---- comando e autostart
chmod +x "$DIR/token-widget"
mkdir -p "$HOME/.config/autostart" "$HOME/.local/bin"
ln -sf "$DIR/token-widget" "$HOME/.local/bin/token-widget"
cat > "$HOME/.config/autostart/token-widget.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Token Widget
Comment=Gasto de tokens do Claude Code e Gemini (Antigravity)
Exec=$DIR/token-widget
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
DESK
echo "Comando 'token-widget' e abertura no login instalados."

# ---- status line do Claude Code (limite da sessão)
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
if [ -d "$CLAUDE_DIR" ]; then
  answer=n
  if [ -t 0 ]; then
    printf "Configurar a status line do Claude Code para mostrar o limite da sessão? [S/n] "
    read -r answer || answer=n
    [ -z "$answer" ] && answer=s
  fi
  case "$answer" in
    [sS]*)
      $PY - "$CLAUDE_DIR/settings.json" "$DIR/token_widget/claude_statusline.py" <<'PYEOF'
import json, os, shlex, shutil, sys
path, script = sys.argv[1], sys.argv[2]
command = "/usr/bin/python3 " + shlex.quote(script)
settings = {}
if os.path.exists(path):
    with open(path, encoding="utf-8") as fh:
        settings = json.load(fh)
current = settings.get("statusLine")
if current and current.get("command") == command:
    print("A status line já está configurada.")
    sys.exit(0)
if current:
    print("Você já tem uma status line no Claude Code; não mexi nela.")
    print("Para usar a do widget, troque o comando em", path, "por:")
    print("  " + command)
    sys.exit(0)
backup = os.path.exists(path)
if backup:
    shutil.copy2(path, path + ".bak-token-widget")
settings["statusLine"] = {"type": "command", "command": command, "refreshInterval": 60}
with open(path, "w", encoding="utf-8") as fh:
    json.dump(settings, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
print("Status line configurada." + (" Backup em settings.json.bak-token-widget." if backup else ""))
PYEOF
      ;;
    *) echo "Status line não configurada. Veja o README para fazer depois." ;;
  esac
fi

echo "Pronto. Rode 'token-widget' agora ou faça logout/login."
