# Seguridad de mensajes — harness Teams

## Contacto autorizado para envío

| Campo | Valor |
|-------|-------|
| Nombre | Nicolás Awamori |
| Login TF | `nicolas.awamori` |
| Rol | Gerente Testing Factory |
| Búsqueda UIA | `Nicolas Awamori` · `Awamori` · `Nicolas Awamori Accusys` |

## Flujos con impacto en chat

| Flujo | Permiso |
|-------|---------|
| TE-04..TE-06 | Buscar, abrir chat, **escribir sin Enviar** |
| **TE-07** | **Único flujo con `send_keys Enter` o botón Enviar** |
| TE-08+ | Solo lectura, scroll, navegación |
| TE-09 | Canales — **prohibido** escribir en hilo |
| TE-14 | Nuevo chat — **Cancelar** antes de destinatario alternativo |

## Plantilla mensaje TE-07

```
[AwdUI-MCP-TE] harness TE-07 verificación agentica — OK si recibís esto en prueba MCP.
```

Opcional suffix: fecha ISO corta (`2026-09-06`).

## Verify post-envío TE-07

1. `read_element` / `list_elements` en panel mensajes — texto contiene `[AwdUI-MCP-TE]`
2. Screenshot ventana chat
3. **No** reenviar si ya existe mensaje harness reciente (<24h) — marcar TE-07 `met` con nota "mensaje previo visible"

## Si el agente necesita probar otra cosa

Usar TE-06 (compose sin enviar) o canal de prueba **sin publicar**. Nunca improvisar otro destinatario.
