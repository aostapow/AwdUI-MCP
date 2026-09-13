# Lab: append JSONL con UTF-8 (prohibir Add-Content sin encoding)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-07 23:21:00 |
| **Skill objetivo** | awdui-mcp-automejora/references/evaluacion-lab.md |
| **Tipo de gap** | ejecucion |
| **Nivel** | L3 |

## Resumen

**Problema:** Durante corrida lab `calculadora-2026-09-07`, el agente appendeó líneas a
`mcp-usage.jsonl` / `evidence.jsonl` con **PowerShell `Add-Content`** sin encoding UTF-8.
Caracteres como «Estándar», «Cerrar navegación» se corrompieron; `load_jsonl` / hooks con
`utf-8-sig` fallan o omiten líneas → cobertura y `validate_perfect_gate` desalineados.

**Solución:** En `evaluacion-lab.md` § «Registro por invocación» añadir subsección **Append seguro**
con: (1) prohibir `Add-Content` / `Out-File` sin `-Encoding utf8`; (2) preferir helper Python
`scripts/lab_append_jsonl.py` (propuesta complementaria en `scripts/`); (3) ejemplo one-liner
`python -c` con `open(..., 'a', encoding='utf-8')`.

**Dónde:** `references/evaluacion-lab.md`; opcional mención en `SKILL.md` § artefactos lab.

## Texto propuesto

### Append seguro a `*.jsonl` (obligatorio)

**No usar** `Add-Content` ni `Out-File` por defecto en Windows PowerShell 5.x — reescriben o
corrompen UTF-8 (acentos en evidencia Calculadora/AST).

**Preferido:**

```powershell
python scripts/lab_append_jsonl.py --file runs/{run}/mcp-usage.jsonl --json '{"ts":"...","tool":"invoke_element",...}'
```

**Alternativa inline:**

```powershell
python -c "import json,pathlib; p=pathlib.Path('runs/calculadora-2026-09-07/mcp-usage.jsonl'); p.parent.mkdir(parents=True, exist_ok=True); p.open('a',encoding='utf-8').write(json.dumps({...},ensure_ascii=False)+'\n')"
```

Si PowerShell es inevitable: `Add-Content -Encoding utf8` **y** verificar con
`python scripts/lab_coverage_report.py` que `load_jsonl` no reporta líneas inválidas.

## Contexto del turno

- F-05 met; fricción reportada: «PowerShell Add-Content rompió UTF-8 jsonl».
- `scripts/lab_coverage_lib.py` lee con `encoding=utf-8` (sin BOM tolerance en todas las rutas).
- Skills leídas: `awdui-mcp-automejora`, `action-narration` — sin guía append encoding.

## Verificación de duplicados

- **Ninguna** propuesta previa en `_MCP_IMPROVEMENT/` sobre JSONL encoding.
- Complementa hook `check_mcp_objective.py` que ya usa `utf-8-sig` al **leer** — gap es escritura.

## Test de abstracción (L3)

Aplica a cualquier corrida lab (Calculadora, Notepad, Teams) con texto localizado en evidencia.

## Esfuerzo observado

- Corrupción de acentos en jsonl; riesgo de subcontar invocaciones en `coverage.json`.

## Criterio de aceptación

- [ ] `evaluacion-lab.md` incluye § Append seguro con los tres métodos.
- [ ] Agente lab deja de usar `Add-Content` sin encoding en corridas nuevas.
- [ ] (Opcional) `scripts/lab_append_jsonl.py` + test pytest round-trip acentos.

## Beneficios futuros

- `lab_coverage_report.py` y gate G4–G8 confiables con evidencia en español.
- Menos re-trabajo manual al regenerar `coverage.json` tras corrupción.
