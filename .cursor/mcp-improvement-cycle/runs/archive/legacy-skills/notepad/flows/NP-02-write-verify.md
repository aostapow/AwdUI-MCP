# NP-02 — Escribir + verificar editor

## Objetivo
Validar ValuePattern en Document id=15 y alternativas de lectura.

## Precondiciones
- NP-01 completado
- Editor vacío

## Pasos

### 1. Escribir vía ValuePattern
```
set_element_value(automation_id="15", value="Harness MCP Notepad - prueba maxima cobertura", window_title="Bloc de notas")
```
**Resultado:** Value set via ValuePattern (~200ms fast)

### 2. Verificar (NO usar get_all_values — bug)
```
spy_inspect(automation_id="15")
  → patterns.Value.value == texto esperado ✓
```

### 3. Alternativa type_text
```
send_keys("ctrl+a")  → seleccionar todo
type_text("Segunda linea via type_text")
spy_inspect(automation_id="15")  → verify
```

### 4. Verificación integrada
```
wait_for_condition(automation_id="15", value_contains="type_text", window_title="Bloc de notas")
```

## Bug documentado
`get_all_values` devuelve `"Editor de texto"` (name) en lugar del value real cuando `backend_used=cache`.

**Workaround:** `spy_inspect` o `get_element_properties` con Value pattern.

## Evidencia
| Tool | timing_ms | verdict |
|------|-----------|---------|
| set_element_value | ~200 | fast |
| spy_inspect verify | ~350 | ok |
| get_all_values | ~400 | fail (valor incorrecto) |
