# Addin COBIS CEN — Tools `cen_*` (v0.6.0)

**48 tools** | **1447 forms** | **6393 messages** | **276 popup classes**

Habilitar: `~/.awdui-mcp/addins.json` → `{ "cen": { "enabled": true } }`

Skill: `addins/cen/skills/SKILL.md`

## Regenerar conocimiento

```powershell
python scripts/extract_cen_knowledge.py "<Productos (Nuevo)>"
```

## Agentic (usar primero)

| Tool | Descripción |
|------|-------------|
| `cen_analyze_form` | Snapshot: perfil + modal + toolbar live + sugerencias |
| `cen_suggest_next_action` | Siguiente paso recomendado |
| `cen_click_toolbar_intent` | Click por intent: search/next/exit/transmit/create/delete/choose/print/export |
| `cen_resolve_toolbar` | Resolver intent → caption sin click |

## Catálogo

| Tool | Descripción |
|------|-------------|
| `cen_list_forms` | Listar (usa índice liviano) |
| `cen_get_form_profile` | Perfil completo |
| `cen_search_forms` | Búsqueda por id |
| `cen_match_form_profile` | Match ventana activa |
| `cen_catalog_stats` | Stats por producto |
| `cen_get_popup_hints` | ShowPopup hosts → clases hijas |

## Diálogos

| Tool | Descripción |
|------|-------------|
| `cen_classify_message` | Categorizar texto COBISMessageBox |
| `cen_match_dialog` | Leer + clasificar diálogo visible |
| `cen_handle_dialog` | OK/Cancel (+ auto_classify) |
| `cen_detect_dialog` | Detectar #32770 |

## Validación / RPC

| Tool | Descripción |
|------|-------------|
| `cen_wait_toolbar_enabled` | Poll hasta Buscar/etc. habilitado |
| `cen_wait_field_stable` | Poll hasta campo estable |

## UserControl moneda

| Tool | Descripción |
|------|-------------|
| `cen_drill_usercontrol` | Hijos de cmdMoneda_UserControl |
| `cen_set_moneda` | Seleccionar en cmbMoneda |

## TriState / picVisto / Spread context

| Tool | Descripción |
|------|-------------|
| `cen_tristate_list_nodes` / `cen_tristate_toggle` | Permisos ADM |
| `cen_toggle_row_visto` | picVisto FTRAN024 |
| `cen_open_grid_context` / `cen_grid_context_action` | FGrdOpciones |

## Resto (v0.4–0.5)

Detección, campos, F5, grillas, lookup, tabs, outline, paginación, status, security — ver secciones anteriores en git history o `cen_get_addin_info`.
