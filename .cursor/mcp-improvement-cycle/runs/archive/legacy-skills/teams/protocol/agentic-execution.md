# Protocolo agentico — harness Teams

Complementa [awdui-flow-exploration/SKILL.md](../../awdui-flow-exploration/SKILL.md) y [message-safety.md](message-safety.md).

## Reglas duras

| # | Regla |
|---|-------|
| R1 | Una tool MCP por paso — esperar resultado |
| R2 | Narrar en chat: tool, params, esperado |
| R3 | Verify empírica antes de paso N+1 |
| R4 | Tras pop-out / modal → `list_windows` + `set_target_window` |
| R5 | Recovery [recovery.md](recovery.md) antes de reintentar |
| R6 | Screenshot en hitos TE-02, TE-07, TE-20 |
| R7 | Tabla resumen al cerrar cada TE-XX |
| R8 | **TE-07 solo Awamori** — ver message-safety |

## Electron

- `detect_framework` → `electron`
- Árbol vacío: `list_elements(max_depth=8)` → `spy_tree` → documentar gap
- Evitar `max_depth=-1` salvo TE-02 discovery controlado

## Plantilla paso

```markdown
### Paso N — <nombre>
| | |
|---|---|
| **Act** | `tool`(params) |
| **Esperado** | ... |
| **Verify** | `tool` → ... |
| **Si falla** | L? recovery → reintentar |
```
