# NP-19 — Repo completo Notepad

**Estado:** met (2026-09-06)  
**Tools MCP:** `repo_capture`, `repo_list`, `repo_find`, `repo_action`, `repo_hints`  
**Recovery típico:** L2 focus Notepad antes de capture

## Precondiciones

- [ ] Baseline limpio
- [ ] `set_target_window("Bloc de notas")`
- [ ] Notepad visible (no modal encima)

## Pasos

### Paso 0 — Baseline
| | |
|---|---|
| **Act** | `list_windows` |
| **Verify** | Sin modales `#32770` |

### Paso 1 — Capturar editor
| | |
|---|---|
| **Act** | `repo_capture(automation_id="15", repo_path="Notepad/Editor", window_title="Bloc de notas")` |
| **Esperado** | Captured SwfEditor; methods Set, Type, Highlight |
| **Verify** | Output lista métodos |

### Paso 2 — Capturar menú Archivo
| | |
|---|---|
| **Act** | `repo_capture(name="Archivo", parent="Notepad", repo_path="Notepad/MenuArchivo", window_title="Bloc de notas")` |
| **Verify** | Captured SwfMenuItem |

### Paso 3 — Listar repo
| | |
|---|---|
| **Act** | `repo_list(repo_path="Notepad")` |
| **Verify** | Incluye `Notepad/Editor`, `Notepad/MenuArchivo` |

### Paso 4 — Resolver editor
| | |
|---|---|
| **Act** | `repo_find(repo_path="Notepad/Editor")` |
| **Verify** | Resolved SwfEditor Document "Editor de texto" con bbox |

### Paso 5 — Acción Highlight menú
| | |
|---|---|
| **Act** | `repo_action(method="Highlight", repo_path="Notepad/MenuArchivo")` |
| **Verify** | "Highlight on 'Notepad/MenuArchivo' OK" |
| **Nota** | Parámetro es `method`, no `action` |

### Paso 6 — Hito
| | |
|---|---|
| **Act** | `screenshot(scope="window")` |
| **Verify** | Highlight visible o bbox registrado |

## Evidencia (2026-09-06)

- repo_list: 9 objetos incl. Notepad/Editor, Notepad/MenuArchivo
- repo_find Editor: Document at (74,50)
- repo_action Highlight MenuArchivo OK

## Referencias

- [protocol/agentic-execution.md](../protocol/agentic-execution.md)
