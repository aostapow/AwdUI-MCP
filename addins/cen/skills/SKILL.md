# COBIS CEN — Skill de producto (addin `cen` v0.6.0)

Habilitar: `~/.awdui-mcp/addins.json` → `"cen": { "enabled": true }`

## Punto de entrada agentico

```
set_target_window("COBIS")
cen_analyze_form          # snapshot completo: perfil + modal + toolbar + sugerencias
cen_suggest_next_action   # si analyze no alcanza
```

## Conocimiento estático (v0.6)

| Archivo | Contenido |
|---------|-----------|
| `forms_catalog.json` | 1447 forms: toolbar, grids, fields, bb_*, user_controls, popups |
| `forms_catalog_index.json` | Índice liviano por producto |
| `messages_catalog.json` | 6393 mensajes COBISMessageBox categorizados |
| `popups_registry.json` | 276 clases ShowPopup + mapa por form host |

Regenerar todo:

```powershell
python scripts/extract_cen_knowledge.py "<Productos (Nuevo)>"
```

## Tools clave v0.6

| Tool | Cuándo |
|------|--------|
| `cen_analyze_form` | **Siempre primero** — un solo call con todo el contexto |
| `cen_click_toolbar_intent` | `intent=search\|next\|exit\|transmit` — no hardcodear caption |
| `cen_resolve_toolbar` | Solo resolver caption sin click |
| `cen_classify_message` / `cen_match_dialog` | Diálogos COBIS con acción sugerida |
| `cen_set_moneda` | Forms con `cmdMoneda_UserControl1` |
| `cen_wait_toolbar_enabled` | Tras `mskCuenta` / Leave RPC |
| `cen_wait_field_stable` | Esperar valor estable post-validación |
| `cen_get_popup_hints` | Qué sub-forms abre un form (ShowPopup) |
| `cen_catalog_stats` | Conteos por producto |

## Secuencia consulta (v0.6)

```
cen_analyze_form
cen_set_field name=txtconvenio value=...
cen_click_toolbar_intent intent=search
cen_read_grid name=grdRegistros
cen_grid_pagination name=grdRegistros
cen_click_toolbar_intent intent=exit
```

## Cuenta corriente (RPC)

```
cen_set_field name=mskCuenta value=...
cen_wait_field_stable name=mskCuenta
cen_wait_toolbar_enabled caption=Buscar
cen_click_toolbar_intent intent=search
```

## Moneda compuesta

```
cen_drill_usercontrol name=cmdMoneda_UserControl1
cen_set_moneda value=ARS
```

## Reglas críticas

1. **Preferir `cen_click_toolbar_intent`** sobre caption literal
2. **`cen_analyze_form`** antes de improvisar
3. **Modales** — `cen_detect_modal` + sub-flujo completo
4. **Mensajes** — `cen_match_dialog` → `cen_handle_dialog(action=auto)`
5. **Popups** — `cen_get_popup_hints(form_id=...)` para anticipar sub-forms

Ver catálogo completo: `docs/ADDIN_CEN_TOOLS.md`
