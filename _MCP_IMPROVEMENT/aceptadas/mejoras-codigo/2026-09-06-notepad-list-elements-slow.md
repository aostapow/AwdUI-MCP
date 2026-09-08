# list_elements lento en Notepad Win32

| Campo | Valor |
|-------|-------|
| **Estado** | aplicada |
| **Fecha** | 2026-09-06 |
| **Origen** | harness Notepad NP-01..NP-20 |

## Fricción

- `list_elements` role=MenuItem depth=4: **1724–4885ms** en ventana Notepad.
- `list_control_items` fuentes: **6705ms**.
- Bloquea loops agenticos (una tool por paso).

## Propuesta

1. Cache TTL por HWND en `orchestrator.list_elements` ya existe — reducir re-walk con `max_depth` default 3 para win32.
2. Fast path MenuItem: leer solo hijos de MenuBar sin árbol completo.
3. Exponer timing en respuesta `list_elements` (ya parcial).

## Evidencia

- Notepad skill timing-baseline.md
- state.json notepad_evidence 2026-09-06
