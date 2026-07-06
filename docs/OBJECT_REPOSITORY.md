# Object Repository (UFT-style / Swf* WinForms)

Logical object names are stored per application under `~/.awdui-mcp/repositories/`.

## Naming

Use hierarchical paths mirroring QTP/UFT:

| QTP / UFT | AwdUI repo_path |
|-----------|-------------------|
| `SwfWindow("frmMain").SwfButton("btnSave")` | `frmMain/btnSave` |
| `SwfWindow("frmMain").SwfPage("tabDatos").SwfEdit("txtNombre")` | `frmMain/tabDatos/txtNombre` |

## Swf* classes

WinForms controls are stored with QTP-style classes (`SwfButton`, `SwfEdit`, `SwfComboBox`, …) and per-class identification profiles (mandatory → assistive → smart → ordinal → template → OCR).

## Tools

| Tool | Purpose |
|------|---------|
| `repo_capture` | Object Spy → add control to repository with Swf* class |
| `repo_find` | Resolve logical name (Smart Identification) |
| `repo_action` | Execute Swf* method: `Click`, `Set`, `Select`, `FireEvent`, … |
| `repo_list` | List stored objects with class and parent |
| `smart_find` | Cascade including repo layer |
| `highlight_element` | Mark object on screen |

### repo_action examples

```
repo_action(repo_path="frmMain/btnGuardar", method="Click")
repo_action(repo_path="frmMain/txtUsuario", method="Set", value="admin")
repo_action(repo_path="frmMain/cboTipo", method="Select", value="Premium")
repo_action(repo_path="frmMain/txtPass", method="SetSecure", value="secret")
```

## Auto-capture

After successful `smart_find`, `click_element`, `repo_action`, or `repo_find` with `remember=true` (default):

- Swf* class and parent chain
- Identification props (mandatory + assistive + smart)
- Full snapshot via `capture_object_snapshot` (images + phash)
- Strategy memory update

## Image assets

| File | Use |
|------|-----|
| `*_crop.png` | Exact element bbox |
| `*_context.png` | Bbox + 20% padding |
| `*_template.png` | OpenCV template matching fallback (Smart ID) |
| `*_annotated.png` | Window with red highlight |

## Smart Identification order

1. Mandatory properties only
2. Mandatory + assistive
3. Smart properties one-by-one (`name`, `text`, `class_name`, …)
4. Ordinal index
5. Template image from last snapshot
6. OCR on stored visible text

Parent-scoped search: nested paths resolve each parent in the chain before locating the leaf control inside the parent bounding box.
