# Dedup list_elements por runtime_id e IoU

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_codigo |
| **Estado** | aplicada |
| **Fecha** | 2026-09-05 12:09:00 |
| **Usuario sesión** | ariel.ostapow |
| **Módulo** | detection/backends/uia_backend.py, detection/orchestrator.py, tools/ui_automation.py |
| **Tool afectada** | list_elements |
| **Tipo de gap** | deteccion |
| **Nivel** | L4 |
| **Impacto** | medio |

## Resumen

**Problema:** En Calculadora UWP (y otras apps WinUI), `list_elements` devuelve ~64
entradas con solo ~33 controles únicos. El merge UIA+spy deduplica por
`(automation_id, x, y)` pero no cubre: (a) duplicados intra-backend con coords
ligeramente distintas, (b) mismo `automation_id` en árbol pywinauto y sidecar con
offsets distintos, (c) nodos Pane/Group superpuestos sin `automation_id`.

**Solución:** Aplicar `dedupe_elements` (IoU) de `detection/layers/scoring.py` al
resultado final; priorizar clave `runtime_id` cuando exista; exponer metadatos
`raw_count`, `unique_count`, `duplicates_removed` en la respuesta interna y en el
header del tool.

**Dónde:** Post-proceso en `UIABackend.list_elements` y/o `DetectionOrchestrator.list_elements`
antes de cachear.

## Contexto del turno

Ciclo `calc_object_inventory` Standard: `list_elements` reportó 33 únicos / 64
duplicados tras `set_target_window` + `Alt+1`. El agente tuvo que filtrar mentalmente
antes de mapear DisplayControls y StandardFunctions.

## Cambio propuesto (pseudodiff)

```python
# uia_backend.py — tras merge spy + filtro XAML
from detection.layers.scoring import dedupe_elements

def _dedupe_list_result(elements: list[DetectedElement]) -> tuple[list, int]:
    by_runtime: dict[str, DetectedElement] = {}
    no_runtime: list[DetectedElement] = []
    for d in elements:
        rid = (d.runtime_id or "").strip()
        if rid:
            by_runtime.setdefault(rid, d)  # first wins or prefer spy/enabled
        else:
            no_runtime.append(d)
    merged = list(by_runtime.values()) + no_runtime
    deduped = dedupe_elements(merged, iou_threshold=0.65)
    return deduped, len(elements) - len(deduped)

# orchestrator.list_elements return:
return {
    "elements": [...],
    "count": len(deduped),
    "raw_count": len(raw),
    "duplicates_removed": removed,
    "backend_used": bname,
}
```

```python
# ui_automation.py list_elements tool header:
header = f"Found {result['count']} elements ({result.get('duplicates_removed', 0)} duplicates removed) via {backend}"
```

**Regla de prioridad al colisionar:** preferir elemento con `enabled=True`, más
patterns (`Invoke`/`Value`), o fuente spy si IoU > 0.9.

## Verificación de duplicados

- Backlog abierto: sin propuesta previa sobre dedup de `list_elements`.
- Relacionado pero distinto: `observe-ui-depth-cap` (profundidad), no dedup.
- `dedupe_elements` ya existe en `layered_detector` — reutilizar, no duplicar lógica.

## Test de abstracción

Cross-app: WinForms con TableLayoutPanel y UWP con ApplicationFrameHost+CoreWindow
se benefician; no es sintoma solo de Calculadora.

## Criterio de aceptación

- [ ] `tests/test_tree_depth.py` o nuevo `tests/test_list_elements_dedup.py`: fixture
      con dos `DetectedElement` mismo `automation_id`, IoU > 0.7 → uno solo.
- [ ] Respuesta incluye `duplicates_removed` cuando > 0.
- [ ] Sin regresión en count para árboles sin duplicados (WinForms simple).
- [ ] Actualizar `docs/MCP_TOOLS_REFERENCE.md` sección `list_elements`.

## Beneficios futuros

- Inventarios agenticos más cortos y legibles.
- Menos tokens en cada `list_elements` del ciclo Calculadora.
- Base para `list_control_items` y grids sin ruido de contenedores duplicados.
