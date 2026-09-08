# Gaps MCP — Teams (backlog skill)

Propuestas formales van a `_MCP_IMPROVEMENT/` tras advisor. Aquí: observaciones del harness TE.

| Gap | Flujo | Prioridad |
|-----|-------|-----------|
| `launch_app(ms-teams:)` / `Teams.exe` WinError 2 | TE-01 | P1 — usar ruta WindowsApps completa |
| `detect_framework` → unknown (TeamsWebView) | TE-01/TE-02 | P2 — clasificar Electron/Chromium |
| Compose CKEditor: ValuePattern placeholder; type_text/type_into_element sin verify UIA | TE-06/TE-07 | P1 — fix read compose + verify antes TE-07 |
| TreeItem chat id rota (menur2u→menurfp) | TE-05 | P2 — buscar por name |
| SelectionItem verify falla pero chat abre | TE-05 | P2 |
| Send button sin automation_id en find_element | TE-07 | P1 — localizar por name Enviar |
| list_elements 7–8s max_depth=8 | TE-02+ | P2 — acotar role/depth |
| ascii_ui_view list index out of range | TE-02 | P2 |
| Screenshot scope=window captura foreground si target background | TE-01+ | P2 — focus_policy always en hitos |
| Contaminación árbol Cursor sin scope hwnd | TE-02 | P2 |
| Pop-out chat rompe scope | TE-18 | P2 |
