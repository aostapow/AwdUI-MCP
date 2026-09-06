# Backlog de mejoras — AwdUI MCP

Propuestas generadas por el subagente `awdui-mcp-improvement-advisor` al cierre de turnos con automatización Windows.

**Objetivo:** un MCP eficiente para detectar e interactuar con aplicaciones Windows (UIA primero, OCR como fallback, tools atómicas, código mantenible).

No reemplaza el código ni las skills; es material para que **mantenedores** evalúen y apliquen.

## Estructura

```
_MCP_IMPROVEMENT/
├── README.md
├── advisor.log              ← una línea por ejecución del advisor
├── mejoras-skill/           ← solo Estado: propuesta (pendientes)
├── mejoras-tool/
├── mejoras-codigo/
├── aceptadas/               ← aplicada / aceptada (por tipo)
│   ├── mejoras-skill/
│   ├── mejoras-tool/
│   └── mejoras-codigo/
└── rechazadas/
    ├── mejoras-skill/
    ├── mejoras-tool/
    └── mejoras-codigo/
```

## Convención de nombres

```
{YYYYMMDD}_{HHmmss}_{slug-corto}.md
```

## Estados

| Estado | Significado |
|--------|-------------|
| `propuesta` | Generada por advisor; pendiente revisión |
| `aceptada` | Aprobada; pendiente implementar |
| `aplicada` | Incorporada al repo |
| `rechazada` | Descartada (motivo en archivo) |

## Flujo mantenedor

1. Revisar **solo** `mejoras-*/*.md` (pendientes).
2. Verificar impacto cross (¿otras apps WinForms se benefician?).
3. Implementar en código/skills según tipo.
4. Correr `pytest tests/` y prueba MCP viva si aplica.
5. Actualizar `Estado` en el archivo (`aplicada`, `aceptada` o `rechazada`).
6. Archivar con:

```powershell
& scripts/archive-mcp-improvements.ps1
```

Vista previa: `& scripts/archive-mcp-improvements.ps1 -DryRun`

El script mueve el `.md` a `aceptadas/{tipo}/` o `rechazadas/{tipo}/`. Las carpetas `mejoras-*` quedan solo con `propuesta`.

## Advisor

- Skill: `.cursor/skills/awdui-mcp-improvement-advisor/SKILL.md`
- Manifiesto: `.cursor/skills/awdui-mcp-improvement-advisor/manifest.md`
- Exclusión usuario: `sin mcp advisor`
- Plantillas: `.cursor/skills/awdui-mcp-improvement-advisor/examples.md`

## Log (`advisor.log`)

```
2026-07-07 01:10:00 | ariel.ostapow | ninguno | artefactos=0 | subagente=completado
```

Timestamp: `America/Argentina/Buenos_Aires`.
