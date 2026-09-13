# Perfiles por framework — detección sin degradar otras familias

Parte de [awdui-mcp-automejora](../../SKILL.md). Complementa `awdui-app-agnostic.mdc` (prohibido por **app**; **sí** permitido por **framework**).

## Objetivo

Si `find_element` / `list_elements` ya es eficiente en **UWP**, un fix motivado por **Win32/Explorer** no debe entrar como cambio global en el núcleo UIA sin aislar la política al framework que falló.

## Código

| Pieza | Ruta |
|-------|------|
| Perfil | `mcp-servers/awdui-server/detection/frameworks/base.py` → `FrameworkProfile` |
| Registro | `detection/frameworks/registry.py` → `get_profile()`, `get_profile_for_window()` |
| Políticas compartidas | `detection/frameworks/policies.py` (ej. weak backend UWP) |

Cada perfil define, entre otros:

- `auto_list_depth` — `list_elements` con `max_depth=0`
- `backend_order` — cadena UIA / FlaUI / MSAA (`orchestrator`)
- `prefers_spy_invoke`, `prefers_spy_expand_collapse`, `expander_dims_via_spy`
- `quick_resolve_spy_before_find` — Win32/Electron vs UWP

**Nuevo comportamiento por familia:** extender `registry.py` (o módulo `detection/frameworks/<familia>.py` si crece) — evitar `if "Calculadora"` o `if "Explorer"`.

## Clasificar una mejora (fix_in_cycle / improvements.jsonl)

Antes de implementar, responder:

1. ¿La detección **ya era buena** en el framework del turno? (timings en `mcp-usage.jsonl`, `detection_health`)
2. ¿El gap es de **otra familia** o del núcleo compartido?

| `abstraction` | Cuándo | Dónde implementar |
|---------------|--------|-------------------|
| `framework` | Solo falla en uwp / win32 / electron / … | Perfil + rama acotada; tests `tests/frameworks/` |
| `generic` | Bug real en pipeline común | `uia_backend`, `orchestrator`, … + **regresión multi-framework** |
| `skill_only` | Quirk de producto | Skill/repo_hints — no servidor |

Campos obligatorios en lab (en `last_cycle.fix_gate` y línea `fix_applied`):

```json
{
  "framework": "win32",
  "abstraction": "framework",
  "regression_frameworks": ["win32", "uwp"],
  "files_touched": ["mcp-servers/awdui-server/detection/frameworks/registry.py"]
}
```

Si `abstraction` es `generic` y `files_touched` incluye núcleo compartido (`uia_backend.py`, `orchestrator.py`, `uia_find.py`, `element_scope.py`), **`regression_frameworks` debe listar ≥2 familias** con evidencia (pytest + re-VERIFY o timings citados). El hook `fix_in_cycle_gate` bloquea si falta.

## Checklist antes de cerrar fix en lab

1. ¿Podía ser solo perfil/framework? → mover fuera del núcleo.
2. pytest del módulo tocado + al menos un test de perfil (`tests/test_framework_profiles.py`).
3. Si tocaste núcleo: correr tests de otra familia “golden” (ej. UWP calc + Win32 scope).
4. Documentar `abstraction` y `regression_frameworks` en `improvements.jsonl`.

## Manifest de baseline (no object repo)

| Artefacto | Rol |
|-----------|-----|
| `lab-apps/detection-baseline.schema.json` | Esquema |
| `.cursor/mcp-improvement-cycle/matrices/detection_baseline.json` | Agregado **framework × tool × uia_role** (p50/p95, muestras) |
| `scripts/merge_detection_baseline.py` | Regenera desde `runs/*/mcp-usage.jsonl` |
| Hook cobertura lab | Tras cada turno, `incremental_lab_coverage` actualiza el baseline |

En lab, cada línea `mcp-usage.jsonl` debe incluir **`framework`**, **`timing_ms`** y **`uia_role`** cuando aplique (plantilla `lab-apps/mcp-usage.template.jsonl`).

El gate `fix_in_cycle` añade **texto advisory** si `abstraction=generic` pero el baseline marca esa celda como ya eficiente.

## Evolución

- Extraer ramas restantes de `ui_automation.py` / `element_scope.py` a perfiles.
