# TE-01 — Launch Teams limpio

**Estado:** pending | **Recovery:** L3

## Pasos
1. `launch_app(path="ms-teams:", replace=true)` — fallback Teams.exe
2. `wait_for_input_idle` ≤15s
3. `set_target_window("Teams", focus_policy="minimal")`
4. `detect_framework` → electron
5. `screenshot(scope=window)`

## Criterio met
Una instancia; target fijado; framework electron.
