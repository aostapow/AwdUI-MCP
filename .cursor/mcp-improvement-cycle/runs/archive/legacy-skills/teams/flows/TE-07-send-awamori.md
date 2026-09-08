# TE-07 — Enviar mensaje harness a Nicolás Awamori

**Estado:** pending | **Recovery:** L2  
**ÚNICO flujo con envío real**

Ver [message-safety.md](../protocol/message-safety.md).

## Precondiciones

- TE-05 met — chat 1:1 abierto
- Header del chat = **Nicolás Awamori** (STOP si otro nombre)
- TE-02 completó mapa compose + botón Enviar

## Mensaje canónico

```
[AwdUI-MCP-TE] harness TE-07 verificación agentica — OK si recibís esto en prueba MCP.
```

## Pasos

### Paso 0 — Verify destinatario
| | |
|---|---|
| **Act** | `spy_inspect` header chat **o** `list_elements` título |
| **Verify** | name contiene `Awamori` |
| **Si falla** | STOP — no enviar |

### Paso 1 — Focus compose
| | |
|---|---|
| **Act** | `click_element` compose (element-map) |
| **Verify** | compose focused |

### Paso 2 — Escribir
| | |
|---|---|
| **Act** | `type_text` mensaje canónico |
| **Verify** | Value/name compose contiene `[AwdUI-MCP-TE]` |

### Paso 3 — Enviar
| | |
|---|---|
| **Act** | `invoke_element` **Enviar** **o** `press_key` Enter |
| **Verify** | success; timing citado |

### Paso 4 — Verify historial
| | |
|---|---|
| **Act** | `list_elements` panel mensajes / `read_element` |
| **Verify** | Burbuja con prefijo `[AwdUI-MCP-TE]` **o** mensaje harness previo <24h |

### Paso 5 — Hito
| | |
|---|---|
| **Act** | `screenshot(scope=window)` |
| **Evidencia** | teams_matrix TE-07 → met |

## Reuse mensaje previo

Si ya hay burbuja `[AwdUI-MCP-TE]` reciente: marcar **met** con nota `reuse harness` — no reenviar.

## Prohibido

- Otro contacto, canal, reunión
- Mensaje sin prefijo `[AwdUI-MCP-TE]`

## Checkpoints

| CP | Gate | Verify |
|----|------|--------|
| CP-0 | Destinatario | Header Awamori |
| CP-1 | Envío | historial contiene prefijo |
| CP-final | Hito | screenshot citado |
