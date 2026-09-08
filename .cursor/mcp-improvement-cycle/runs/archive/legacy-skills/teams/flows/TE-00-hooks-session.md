# TE-00 — Hooks + sesión MCP

**Estado:** pending | **Recovery:** L0

## Objetivo
Validar MCP vivo antes de tocar Teams.

## Pasos

### Paso 1 — check_version
| | |
|---|---|
| **Act** | `check_version` |
| **Esperado** | v0.4.0 up to date |

### Paso 2 — check_session_status
| | |
|---|---|
| **Act** | `check_session_status` |
| **Verify** | uia_find=true |

### Paso 3 — state.json
| | |
|---|---|
| **Verify** | teams_perfect=false; teams_matrix 21 flujos |

## Criterio met
MCP vivo + state harness Teams presente.
