# Calculadora UWP — patrones descubiertos (laboratorio)



Patrones reutilizables para **cualquier** app WinUI/NavView; la Calculadora es solo el medio actual.



## Modo Estándar desde otro modo



- **Atajo:** `send_keys` `alt+1` → modo Estándar sin abrir NavView (locale puede variar).

- **NavView:** `TogglePaneButton` — tras fix ApplicationFrameHost en spy, probar `invoke_element` primero.

- **`list_elements`:** UIA puede incluir nodos de otros modos NavView aunque el panel esté colapsado. Default: solo visibles (`include_offscreen=false`). Para inventario completo: `list_elements(include_offscreen=true, tree_mode="raw", max_depth=10)`. Al **actuar**, priorizar controles visibles (skill + `role=Button` para teclado).
- **Settings diag bleed (skill):** en modo ≠ Settings, ignorar botones «Copiar la ruta… diagnósticos» / «Buscar actualizaciones» al planificar clics — conocimiento de producto, no del servidor.
- **Instancia huérfana:** si `spy_inspect` `process_id` ≠ PID de la ventana activa, usar `launch_app(path='calc.exe', replace=true)` (cierra duplicados y abre una sola) — **no** llamar `launch_app` sin `replace` si ya hay Calculadora abierta.

## Historial (title chrome / ApplicationFrameHost)

| Señal | Valor |
|-------|--------|
| `automation_id` | `HistoryButton` |
| name (abierto) | `Cerrar control flotante de historial` |
| name (cerrado) | `Abrir control flotante de historial` |
| Pattern | Invoke |

**Protocolo (rápido):** `invoke_element automation_id=HistoryButton` → citar `elapsed_ms`. Fallback coords solo si falla.

**LightDismiss:** solo presente/verificable con flyout abierto (`HistoryButton` name contiene «Cerrar…»). Verificar estado del flyout antes de actuar sobre `LightDismiss`. `invoke LightDismiss` cierra flyout → `HistoryButton` vuelve a «Abrir…».

**Fix MCP (2026-09-05):** spy sidecar `ResolveWindow` prioriza ApplicationFrameHost sobre CoreWindow para Calculadora — title chrome entra en `FindInScope`.



## Científica — flyout trigonometría

| Señal | Valor |
|-------|--------|
| `trigButton` | TogglePattern — abrir **una vez** (state On); no re-toggle antes de pulsar sin/cos/tan |
| Flyout ids | `sinButton`, `cosButton`, `tanButton`, `secButton`, `cscButton`, `cotButton`, `trigShiftButton`, `hypShiftButton` |
| Inverse ids (tras `trigShiftButton` On) | `invsinButton`, `invcosButton`, `invtanButton`, `invsecButton`, `invcscButton`, `invcotButton` |
| Hyp ids (tras `hypShiftButton` On) | `sinhButton`, … (buscar por name «hiperbólico») |

**Func flyout (`funcButton` On):** pane `FuncFlyout`; ids `absButton`, `floorButton`, `ceilButton`, `randButton`, `dmsButton`, `degreesButton`. Patrón unary: `func→=` (arg 0 default); `randButton` resultado inmediato sin `equal`.
 `trigButton` On → `invoke_element` `cosButton` (o sin/tan) → **no** `num0Button` (la función ya usa argumento 0 por defecto) → `spy_inspect` `CalculatorExpression` debe contener «coseno (0)» / «tangente (0)» → `equalButton` → `CalculatorResults` (cos(0)=1, tan(0)=0, sin(0)=0).

**Anti-patrón:** `cos` → `0` → `=` deja expresión `0=` sin función (falso negativo de gap MCP).

**Stale:** tras `equalButton`, botones del flyout pueden devolver `stale_instance`. Recovery: `focus_window` + `clearButton`; si persiste → `launch_app(path='calc.exe', replace=true)` (una sola instancia). **Prohibido** acumular `launch_app` sin `replace`.




| automation_id | name (ES) | Pattern típico |

|---------------|-----------|----------------|

| `ClearMemoryButton` | Borrar toda la memoria | Invoke |

| `MemRecall` | Recuperar la memoria | Invoke |

| `MemPlus` | Sumar memoria | Invoke |

| `MemMinus` | Restar la memoria | Invoke |

| `memButton` | Almacén de la memoria | Invoke |

| `MemoryButton` | Abrir control flotante de la memoria | Invoke — flyout flotante |

| `CalculatorExpression` | La expresión es … | Text — verificación de historial en línea |



**Descubrimiento:** por cada control, `spy_inspect` / `get_element_properties` → patterns → invoke/click → verificar display o subárbol.



## Conversores (Date / Currency / Volume / Length)

### Fecha (`Date`)

| automation_id | Rol | Pattern | Notas |
|---------------|-----|---------|-------|
| `DateCalculationOption` | ComboBox | **ExpandCollapse** | `expand_element` 405ms → modos fecha |
| `DateDiff_FromDate` / `DateDiff_ToDate` | CalendarDatePicker | Invoke + **Value** | Invoke abre `CalendarView` |
| `CalendarView` | Calendar | DataItem **SelectionItem** | `PreviousButton`/`NextButton` Invoke |
| `DateDiffAllUnitsResultLabel` | Text | LegacyIAccessible | ej. `Diferencia: 4 días` |

### Divisa / Volumen / Longitud (grid común `UnitConverterRootGrid`)

| automation_id | Rol | Pattern | Notas |
|---------------|-----|---------|-------|
| `Units1` / `Units2` | ComboBox | **ExpandCollapse** | `expand_element` o `invoke_element` (2026-09-05) |
| `Value1` / `Value2` | Text | Invoke (focus) | nombre incluye cantidad + unidad |
| `CurrencyRatioEqualityBlock` | Text | — | solo Divisa |
| `CurrencyRefreshBlock` | Hyperlink | **Invoke** | actualizar tarifas |
| `ClearEntryButtonPos0` / `BackSpaceButtonSmall` | Button | Invoke | teclado reducido |
| `NumberPad` | Group | num0–9 + `decimalSeparatorButton` | Invoke |

**Verificación:** `expand_element(automation_id="Units1")` → lista monedas; `DateCalculationOption` → modos fecha.

### Configuración (`SettingsItem`)

| automation_id | Rol | Pattern | Notas |
|---------------|-----|---------|-------|
| `BackButton` | Button | **Invoke** | vuelve al modo previo (ej. Longitud) |
| `AppThemeExpander` | SettingsExpander Group | **expand_element** `fallback_click=true` | HeaderClick en bbox (sin coords manuales) |
| `ThemeRadioButtons` | Group | hijos RadioButton **SelectionItem** | `LightThemeRadioButton`, `DarkThemeRadioButton`, `SystemThemeRadioButton` |
| `AboutExpander` | SettingsExpander Group | **expand_element** `fallback_click=true` | revela `AboutEULA`, `AboutControlServicesAgreement`, `AboutControlPrivacyStatement` |
| `AboutBuildVersion` | Text | — | ej. `11.2607.0.0` |
| `FeedbackButton` | Hyperlink | **Invoke** | abre hub de comentarios Windows |
| `GitHub` | Hyperlink | sin automation_id | en `AboutContribute` |

**Verificación:** `DarkThemeRadioButton` SelectionItem 337ms → UI oscura; `SystemThemeRadioButton` restore; `BackButton` 243ms.

## Pausa del ciclo automático



Usuario detiene agente y el hook `stop` reinyecta → `scripts/pause-mcp-cycle.ps1`.

