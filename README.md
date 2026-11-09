# Token Widget

Widget de desktop (GNOME/X11) que mostra quantos tokens de IA você gastou hoje, nos últimos 7 dias e no mês, separado entre **Claude** e **Gemini**.

Os dados vêm direto dos arquivos locais, sem chave de API:

| Fonte | Arquivos lidos |
|---|---|
| Claude Code | `~/.claude/projects/**/*.jsonl` (campo `message.usage`) |
| Gemini (Antigravity CLI) | `~/.gemini/antigravity-cli/conversations/*.db` (SQLite com protobuf) |

## Rodar

Precisa do Python do sistema com GTK3 (`python3-gi`, já vem no Ubuntu).

```sh
./token-widget        # abre o widget
./install.sh          # abre sozinho no login (autostart do GNOME)
```

- Arraste com o botão esquerdo para mover (a posição fica salva).
- Botão direito: Atualizar / Sair.
- Atualiza sozinho a cada 60 s.

## Configuração

`~/.config/token-widget/config.json` é criado ao mover o widget. Campos opcionais:

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
