# Token Widget

Widget de desktop (GNOME/X11) que mostra quantos tokens de IA você gastou hoje, nos últimos 7 dias e no mês, separado entre **Claude** e **Gemini**.

Os dados vêm direto dos arquivos locais, sem chave de API:

| Fonte | Arquivos lidos |
|---|---|
| Claude Code | `~/.claude/projects/**/*.jsonl` (campo `message.usage`) |
| Gemini (Antigravity CLI) | `~/.gemini/antigravity-cli/conversations/*.db` (SQLite com protobuf) |

## Limite da sessão

- **Claude:** a barra mostra quanto da sessão de 5 h já foi usado, quando ela renova e o uso da semana.
  O dado vem da status line do Claude Code: `token_widget/claude_statusline.py` está configurado em
  `~/.claude/settings.json` (`statusLine`) e grava `~/.cache/token-widget/claude-limits.json`.
  Só atualiza enquanto o Claude Code está aberto.
- **Gemini (Antigravity):** o agy não grava a cota em disco nem a entrega para hooks ou servidores
  MCP, então o widget não tem como mostrar. Dá para usar a meta diária manual no lugar.

## Rodar

Precisa do Python do sistema com GTK3 (`python3-gi`, já vem no Ubuntu).

```sh
./token-widget        # abre o widget
./install.sh          # abre sozinho no login (autostart do GNOME)
```

- Arraste com o botão esquerdo para mover (a posição fica salva).
- Botão direito: Configurações…, Sempre na frente, Atualizar, Sair.
- Atualiza sozinho a cada 60 s.

## Configuração

Pelo menu **Configurações…** (botão direito) dá para ajustar opacidade, "sempre na frente",
intervalo de atualização e meta diária; tudo é aplicado na hora.

Os valores ficam em `~/.config/token-widget/config.json`, que também pode ser editado à mão
(feche e abra o widget depois). Campos:

```json
{
  "refresh_seconds": 60,
  "opacity": 0.88,
  "gemini_model_names": { "1418": "Gemini 3.8 Flash" },
  "daily_budget": { "claude": 2000000, "gemini": 500000 }
}
```

- `gemini_model_names`: o Antigravity guarda o modelo como número; aqui você dá nome a ele.
- `daily_budget`: meta diária de tokens; com valor > 0 aparece uma barra de progresso.

## Observação

O formato do Antigravity não é documentado. Os campos (`input`, `output`, `cache`) foram descobertos lendo o protobuf; se uma atualização do CLI mudar o formato, o Gemini pode aparecer zerado.
