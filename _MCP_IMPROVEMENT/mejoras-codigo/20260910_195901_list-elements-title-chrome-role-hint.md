# list_elements — hint cuando role filter devuelve solo chrome de título

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 19:59:01 |
| **Usuario sesión** | ariel.ostapow |
| **Tool afectada** | `list_elements` |
| **Módulo código** | `tools/ui_automation.py`, `detection/spatial_cluster.py` (banda superior) |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **MCP versión** | v0.4.0 |

## Resumen

**Problema:** Con ventana objetivo Explorador y flyout de breadcrumbs abierto,
`list_elements(role="MenuItem")` devolvió elementos accionables pero **solo del menú Sistema**
(banda superior), sin segmentos de ruta. El agente interpretó el listado como verify del flyout
incorrecto. No hay señal MCP de que el filtro por rol cayó en chrome ajeno al popup activo.

**Solución:** Tras un list filtrado por `role`, si **todos** los nodos devueltos caen en la
**banda espacial dominante superior** (title bar / system menu — cluster genérico por ventana,
sin listas por app) **y** el nombre coincide con patrones de chrome Win32 (`Sistema`, `Minimizar`,
`Maximizar`, `Cerrar`), incluir en la respuesta JSON:

```json
"role_filter_note": "matches_title_chrome_only",
"suggested_roles": ["ListItem", "Hyperlink", "Menu", "SplitButton"]
```

Opcional: parámetro `exclude_title_band=true` (default false) para excluir nodos en esa banda.

**Dónde:** `list_elements` handler; tests en `tests/test_list_elements*.py`.

## Contexto del turno

F-12 execute: invoke SplitButton OK; list MenuItem 895 ms — solo Sistema; verify screenshot.
Ver `improvements.jsonl` flow F-12.

## Cambio propuesto (pseudodiff)

1. Tras recolectar elementos con filtro `role`, clasificar bbox Y vs `client_rect` / cluster
   superior (reutilizar lógica `spatial_cluster` existente).
2. Si `len(matches) > 0` y `all(in_title_band)` → set `role_filter_note` + `suggested_roles`
   (constantes genéricas MSAA/UIA, no nombres de producto).
3. Documentar en `docs/MCP_TOOLS_REFERENCE.md` § list_elements.

## Test de abstracción (L4)

Cualquier ventana Win32 con menú sistema + contenido cliente — el hint no menciona Explorador.

## Verificación de duplicados

| Propuesta | Acción |
|-----------|--------|
| `20260910_195900_explorer-breadcrumb-flyout-verify-routing` | Skill — implementar junto |
| `20260907_234600_list-elements-topmost-overlay-foreign-leak` | Distinto — overlays ajenos |

## Criterio de aceptación / tests

- [ ] pytest: fixture mock tree con MenuItem solo en banda Y<10% client → note presente.
- [ ] pytest: MenuItem en cliente (menú bar) → sin note o note distinto.
- [ ] Live F-12: tras invoke breadcrumbs, list MenuItem incluye hint; list ListItem sin hint falso.

## Beneficios futuros

Agente corrige rol sin screenshot; menos routing_tool en lab shell; patrón reutilizable en MDI.
