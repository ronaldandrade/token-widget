#!/bin/sh
# Instala o widget para abrir junto com a sessão do GNOME.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
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
echo "Instalado. Rode 'token-widget' agora ou faça logout/login."
