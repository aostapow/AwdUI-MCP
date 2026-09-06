# Calculadora Programador — bases SelectionItem, QWORD/DWORD y flyout bitwise

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-05 12:22:00 |
| **Skill objetivo** | awdui-flow-exploration/patterns/calculator-lab.md |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Impacto** | medio |

## Resumen

**Problema:** Inventario Programador completado solo con UIA (`invoke_element` SelectionItem/Toggle;
FF→255→bin→oct; flyout AND/OR/XOR; toggle QWORD/DWORD). `calculator-lab.md` aún no documenta
este modo — el agente dependió de `calculator-mcp-harness` + exploración ad hoc. Sin mapa estable,
turnos futuros pueden re-mapear bases o no saber que `octolButton` (no `octalButton`) es el id UIA.

**Solución:** Sección «Modo Programador» en `calculator-lab.md` con tabla de automation_ids,
cadena de verificación por base, flyout bitwise (reusar protocolo Toggle de Científica) y
word-size toggle.

**Dónde:** `patterns/calculator-lab.md` — subsección «Programador».

## Contexto del turno

`calc_object_inventory_programmer`: relaunch calc OK (blocker stale conocido). Nav Programador
408 ms (`SelectionItem`). 46+ botones. Bases verificadas: `hexButton`+FF → `decimalButton`
«Se muestra 255» → `binaryButton` «11111111» (UIA espaciado) → `octolButton` «377».
`qwordButton` → `dwordButton` 231 ms. `bitwiseButton` Toggle 242 ms → 6 ops en árbol
(`andButton`, `orButton`, `notButton`, `nandButton`, `norButton`, `xorButton`). Sin OCR ni coords.
Skills: harness + flow-exploration. MCP v0.2.1.

**Turno exhaustive act+verify bitwise (2026-09-05 20:47):** misma sesión `reuse=true`;
`bitwiseButton` Toggle → `andButton`: `5 AND 3=` → `CalculatorResults` **1** ✓ (731 ms);
`xorButton`: `5 XOR 3=` → **6** ✓ (717 ms). Confirma protocolo flyout Toggle + display
sin relaunch.

**Turno cierre Programador bitwise 6/6 (2026-09-05 20:49):** `reuse=true` **sin**
`replace` — PID estable, sin relaunch. Verificados en vivo los seis operadores del flyout:
`andButton`, `orButton`, `notButton`, `nandButton`, `norButton`, `xorButton` (OBS→ACT→VERIFY
vía `CalculatorResults`). Entre operaciones, **`clearButton` (CE)** limpia display residual
de la expresión anterior antes del siguiente par de operandos — patrón ya documentado en
`calculator-lab.md` (recovery stale); aquí aplicado como **higiene entre verifies**, no por
`stale_instance`. Sin OCR ni coords. **Harness Programador bitwise: met.**

**Turno bit shift lsh+rsh (2026-09-05 20:49):** misma sesión `reuse=true` **sin** `replace`.
`bitShiftButton` Toggle 541 ms → `lshButton`: `8 LSH 1=` → `CalculatorResults` **16** ✓
(716 ms); `rshButton`: `8 RSH 1=` → **4** ✓ (701 ms). Protocolo idéntico a flyout bitwise:
CE → operandos → `bitShiftButton` On → op → segundo operando → `equalButton` → verify UIA.
Sin OCR ni coords. **Harness Programador bit_shift: met.**

**Turno hex keypad A-F (2026-09-05 20:51):** misma sesión `reuse=true` **sin** `replace`.
`hexButton` SelectionItem → `aButton` «Se muestra A»; cadena ACF → display «A C F» ✓;
CE → BDE → `decimalButton` → «Se muestra 3.038» (= **3038** decimal) ✓ (~459 ms).
`aButton`…`fButton` disabled hasta activar hex. Sin OCR ni coords.
**Harness Programmer hex A-F: met.**

## Texto propuesto

### Modo Programador — bases numéricas (RadioButton / SelectionItem)

| automation_id | Rol UIA | Pattern | Verificación (`CalculatorResults`) |
|---------------|---------|---------|-------------------------------------|
| `hexButton` | RadioButton | **SelectionItem** | Tras `FF` en teclado hex → display hex |
| `decimalButton` | RadioButton | SelectionItem | «Se muestra 255» tras cambiar desde HEX FF |
| `binaryButton` | RadioButton | SelectionItem | «11111111» (UIA puede espaciar dígitos) |
| `octolButton` | RadioButton | SelectionItem | «Se muestra 377» — **id es `octolButton`, no `octalButton`** |

**Protocolo OBS→ACT→VERIFY (cadena de bases):**

1. `invoke_element` `hexButton` → `SelectionItemPattern`.
2. Pulsar `fButton` dos veces (o `FF` vía hex keypad `aButton`…`fButton`).
3. `invoke_element` `decimalButton` → leer `CalculatorResults` = 255.
4. `binaryButton` → verificar binario de 255.
5. `octolButton` → verificar 377 octal.
6. Screenshot `scope=window` tras última base.

### Tamaño de palabra (QWORD / DWORD)

| automation_id | Comportamiento | Pattern |
|---------------|----------------|---------|
| `qwordButton` | Activo por defecto en inventario | SelectionItem o Toggle — al activar alterna visibilidad |
| `dwordButton` | Aparece tras seleccionar QWORD toggle | Invoke / SelectionItem |

**VERIFY:** tras toggle, `list_elements` debe mostrar `dwordButton` seleccionable; screenshot opcional.

### Flyout operaciones bitwise

| automation_id | Rol | Pattern | Hijos tras Toggle On |
|---------------|-----|---------|----------------------|
| `bitwiseButton` | Button | **TogglePattern** | `andButton`, `orButton`, `notButton`, `nandButton`, `norButton`, `xorButton` |

**Protocolo:** igual que flyouts Científica (`trigButton`/`funcButton` en propuesta `121301`):
`invoke_element` → `method: TogglePattern` → `list_elements` hijos → operar → toggle off o
`LightDismiss`.

**Entre operaciones bitwise (verify 6/6):** tras cada `equalButton`, invocar `clearButton`
(CE) antes del siguiente par de operandos si el display conserva expresión/resultado previo
— evita lecturas ambiguas en `CalculatorResults` sin relaunch.

### Flyout desplazamiento de bits (bit shift)

| automation_id | Rol | Pattern | Verificación (`CalculatorResults`) |
|---------------|-----|---------|-------------------------------------|
| `bitShiftButton` | Button | **TogglePattern** | On → expone `lshButton`, `rshButton` |
| `lshButton` | Button | Invoke | `8 LSH 1=` → «Se muestra 16» (8<<1) |
| `rshButton` | Button | Invoke | `8 RSH 1=` → «Se muestra 4» (8>>1) |

**Protocolo:** igual que flyout bitwise — `bitShiftButton` Toggle On → operar → verify → CE
entre operaciones si display residual. **Harness bit_shift: met** (turno 2026-09-05).

### Teclado hexadecimal (checklist inventario — **met** 2026-09-05)

| automation_id | Comportamiento | Verificación (`CalculatorResults`) |
|---------------|----------------|-------------------------------------|
| `aButton`…`fButton` | Habilitados solo tras `hexButton` SelectionItem | `aButton` → «Se muestra A» |
| Cadena ACF | `aButton` → `cButton` → `fButton` | Display «A C F» (hex concatenado) |
| Cadena BDE → decimal | `bButton` → `dButton` → `eButton` → `decimalButton` | «Se muestra 3.038» (= **3038** decimal; separador miles locale) |

**Protocolo OBS→ACT→VERIFY (hex keypad):**

1. `invoke_element` `hexButton` → `SelectionItemPattern` (sin esto `aButton`…`fButton` disabled).
2. Pulsar dígitos hex deseados; leer `CalculatorResults` tras cada tecla o cadena.
3. Para conversión decimal: `invoke_element` `decimalButton` → verificar valor numérico (ej. BDE = 3038).
4. `clearButton` (CE) entre cadenas si display residual.
5. Screenshot `scope=window` tras verify decimal.

**Turno live (2026-09-05 20:51):** `reuse=true` **sin** `replace` — PID estable.
ACF display OK; BDE→decimal 3038 ✓ (~459 ms). Sin OCR ni coords.
**Harness Programmer hex A-F: met.**

### Patrón cross-app (WinUI)

Grupos de **RadioButton** en toolbar: cada opción expone **SelectionItem** — usar
`invoke_element` (no `click_element` a ciegas). Flyouts de operadores: **TogglePattern**
(compartido con Científica). Verificación numérica: leer `CalculatorResults` / `Value` del
display, no OCR.

## Verificación de duplicados

- **Complementa** `121301_calculator-flyout-expandcollapse` (protocolo Toggle genérico) — no reemplazar;
  enlazar desde Programador para `bitwiseButton` / `bitShiftButton`.
- Distinto de `121900_calculator-graphing-dual-view` (GraphingControl / ecuaciones).
- Blocker relaunch calc → `120902_stale-element-cache` (ya en backlog; no duplicar).

## Test de abstracción

L3: RadioButton groups + Toggle flyouts aplican a otras apps WinUI/XAML (toolbar modo, palettes).
Ids `octolButton` son **síntoma Calculadora** — el protocolo SelectionItem no.

## Criterio de aceptación

- [ ] Texto en `calculator-lab.md` sin timings del turno
- [ ] Cadena FF→255→bin→oct documentada como verify estándar
- [ ] Enlace a sección flyout Toggle (121301) para bitwise/bitShift
- [ ] Nota `octolButton` vs nombre visible «Octal»

## Beneficios futuros

- Cierra inventario Programador sin re-exploración en conversores siguientes.
- Reduce falsos gaps en bases (agente busca `octalButton` inexistente).
- Modelo reutilizable para toolbar RadioButton + operator flyouts WinUI.
