# discover_flows subárbol — escaneo acotado en flyout (MenuItem, no ribbon)

| Campo | Valor |
|-------|-------|
| **Tipo** | mejora_skill |
| **Estado** | propuesta |
| **Fecha** | 2026-09-10 19:51:26 |
| **Usuario sesión** | ariel.ostapow |
| **Skill objetivo** | `awdui-mcp-automejora/references/evaluacion-lab.md` |
| **Tipo de gap** | routing_tool |
| **Nivel** | L3 |
| **Versión MCP** | 0.4.0 |

## Resumen

**Problema:** En `discover_flows` **subárbol** con flyout/popup abierto (Explorador «Ubicaciones recientes»),
el agente ejecutó `list_elements(role=Button)` (**10.5 s**) y `find_element` de acciones footer
(«Borrar historial», **36 s** NOT FOUND) aunque **un solo MenuItem** bastaba para encolar **F-37**.

**Solución:** En paso B3/B4 de evaluacion-lab, cuando `discover_scope` es subárbol de un `entry` flyout:
limitar roles a los del popup (`MenuItem`, `ListItem`, `Hyperlink`); **prohibir** barrido `Button` del
ribbon/padre; no usar `find_element` para chrome opcional ya visible en screenshot — encolar desde
`list_elements(role=MenuItem)`; tras timing ≥3 s o NOT FOUND → `repo_hints_set` con `latencia:` / `nota:`.

**Dónde:** `evaluacion-lab.md` § Modo B pasos B3–B4 + tabla «Subárbol flyout»; enlace desde
`patterns/object-repository.md` § protocolo post-fricción.

## Contexto del turno

- F-08 `subtree_discovered=true`; encolado único **F-37** (`MenuItem: awdui-lab-escritorio-2026-09-10`).
- Sin `repo_hints_set` pese a WARN SLOW (pedido explícito en turno).
- `list_elements role=Menu` falló (error parámetros — ver propuesta código `backend-kwargs-fallback`).

## Análisis del gap

| Fricción | tipo_gap | L | ¿Propuesta? |
|----------|----------|---|-------------|
| list_elements Button 10s con flyout | performance | L3 | Sí (este archivo — routing) |
| find Borrar historial innecesario | routing_tool | L3 | Sí |
| Falta repo_hints_set | routing_tool | L3 | Incluido en texto propuesto |

Complementa `20260907_232300_discover-root-flyout-dismiss-hygiene` (raíz UWP) — este bloque es **subárbol Win32 flyout**.

## Texto propuesto

### Subárbol con flyout/popup abierto (discover B3–B4)

Tras B2 (re-invoke padre si cerró):

1. `list_elements(role="MenuItem", max_depth=4)` — acciones encolables del popup.
2. **No** `list_elements(role="Button")` sin `ancestor_automation_id` del contenedor flyout.
3. **No** `find_element` por textos footer («Borrar historial», «Anclar») si no salieron en el listado MenuItem.
4. Si `list_elements(role="Menu")` falla → usar MenuItem o `spy_inspect` del popup, no reintentar con parámetros no documentados.
5. Tras WARN slow o NOT FOUND >3 s: `repo_hints_set(repo_path=…, append=true)` con `nota: discover F-XX flyout — solo MenuItem`.

## Test de abstracción (L3)

Aplica a Notepad menú contextual, Explorador flyouts, WinForms popup — no solo carpeta lab.

## Verificación de duplicados

| Propuesta | Acción |
|-----------|--------|
| `20260907_232300_discover-root-flyout-dismiss-hygiene` | Referencia cruzada; no merge |

## Esfuerzo observado

~47 s en tools evitables en un discover que agregó 1 flujo útil.

## Criterios de aceptación (mantenedor)

- [ ] Texto sin rutas lab concretas salvo ejemplo genérico flyout.
- [ ] Obligatoriedad `repo_hints_set` tras WARN en discover documentada.
- [ ] Próximo subárbol F-08/F-37: solo MenuItem list + hints si slow.

## Beneficios futuros

Discover subárbol escala sin escanear ribbon completo; menos false-negative en chrome footer.
