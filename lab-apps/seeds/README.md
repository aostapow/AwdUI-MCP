# Seeds de flujos (opcional)

Al definir una app lab, el usuario puede dar **flujos funcionales iniciales** (pocos está bien).

| Origen | Dónde |
|--------|--------|
| En el mensaje del turno | El agente los vuelca a `runs/{active_run}/flows.json` |
| Archivo opcional aquí | `{slug}.json` — copiado al iniciar corrida si existe |

Durante la corrida el catálogo **crece** en `runs/{active_run}/flows.json` con flujos `source: discovered`.

Plantilla: [flows.template.json](../flows.template.json)
