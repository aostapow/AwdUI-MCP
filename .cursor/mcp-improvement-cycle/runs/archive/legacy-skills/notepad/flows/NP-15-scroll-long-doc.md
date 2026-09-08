# NP-15 — Scroll documento largo

**Estado:** partial · **2026-09-06**

## Retest scroll bug
`scroll(pages=1, direction=down)` → **met** ~120ms (PageDown keyboard).

## Evidencia
Documento corto → `wait_for_change` 0% diff (esperado).

## Pendiente
Documento 200+ líneas para verificar ScrollBar UIA + `scroll_element`.
