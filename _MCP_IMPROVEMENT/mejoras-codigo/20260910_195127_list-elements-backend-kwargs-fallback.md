# list_elements: fallback kwargs en backends sin window_handle / view_scope

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 19:51:27 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | `detection/orchestrator.py` |
| **Tool afectada** | `list_elements` |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Versión MCP** | 0.4.0 |

## Resumen

**Problema:** `list_elements(role="Menu", window_handle=…)` puede fallar con error de keyword
(`window_handle` / `view_scope`) cuando el backend activo es `win32_hwnd` o `jab`, cuyas firmas
no aceptan esos kwargs. El orchestrator solo hace un `except TypeError` quitando `view_scope`, pero
sigue pasando `window_handle` → segundo TypeError no manejado → error al agente.

**Solución:** Cadena de fallback en `orchestrator.list_elements`: (1) full kwargs; (2) sin
`view_scope`; (3) sin `window_handle`; (4) firma mínima legacy. Registrar `backend_kwargs_tier`
en respuesta meta para diagnóstico.

**Dónde:** `detection/orchestrator.py`; test `tests/test_orchestrator_list_kwargs.py`.

## Contexto del turno

- Discover subárbol F-08: agente intentó `list_elements role=Menu` y recibió error `window_handle` kw.
- Documentación MCP_TOOLS_REFERENCE lista `window_handle` como parámetro válido de `list_elements`.

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| TypeError window_handle en list Menu | deteccion | L4 | Sí |

No es solo `ejecucion`: el contrato doc promete `window_handle`; el servidor debe degradar kwargs.

## Cambio propuesto

```python
# orchestrator.py — inside backend loop
def _call_list(b, *, tier: int):
    base = dict(window_title=..., max_depth=..., role=..., tree_mode=..., include_offscreen=...)
    if tier >= 1:
        base["window_handle"] = resolved_hwnd or window_handle
    if tier >= 2:
        base["view_scope"] = view_scope
    try:
        return b.list_elements(**{k: v for k, v in base.items() if _backend_accepts(b, k, tier)})
    except TypeError:
        return _call_list(b, tier=tier - 1)
```

Alternativa: añadir `**kwargs` a `win32_hwnd_backend.list_elements` y `jab_backend.list_elements`.

## Test de abstracción (L4)

Cualquier app que caiga en backend win32/jab durante list filtrado por rol Menu/MenuItem.

## Verificación de duplicados

Sin propuesta previa en `_MCP_IMPROVEMENT/` para kwargs fallback en orchestrator.

## Esfuerzo observado

Error bloqueó inventario Menu; agente continuó con Button scan lento.

## Criterio de aceptación

- [ ] `list_elements(role="Menu", window_handle=<hwnd>)` no lanza TypeError con backend win32 en test mock.
- [ ] Meta `backend_kwargs_tier` en respuesta cuando hubo degradación.
- [ ] `docs/MCP_TOOLS_REFERENCE.md` nota: HWND puede ignorarse en backends legacy.

## Beneficios futuros

Discover en menús Win32/Explorer no falla por parámetros documentados.
