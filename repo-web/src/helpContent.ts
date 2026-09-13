export type HelpSection = {
  id: string;
  title: string;
  body: HelpBlock[];
};

export type HelpBlock =
  | { type: "p"; text: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "code"; text: string }
  | { type: "h4"; text: string }
  | { type: "links"; items: { label: string; href: string }[] };

export const HELP_SECTIONS: HelpSection[] = [
  {
    id: "intro",
    title: "¿Qué es Repo Studio?",
    body: [
      {
        type: "p",
        text:
          "Repo Studio es la interfaz web del repositorio de objetos de AwdUI MCP. Guarda controles Windows que ya mapeaste (propiedades UIA, identificación QTP/Swf*, capturas y notas para el agente) para no redescubrirlos en cada sesión.",
      },
      {
        type: "p",
        text:
          "El MCP y Cursor usan la misma base SQLite. Lo que capturás acá o con repo_capture queda disponible para find_element, repo_find y repo_action.",
      },
    ],
  },
  {
    id: "inicio",
    title: "Inicio rápido",
    body: [
      {
        type: "code",
        text: `# Producción (API + SPA en :8765)\n& C:\\mcps\\AwdUI-MCP\\scripts\\start-repo-studio.ps1\n\n# Si el catálogo da 404 (API viejo)\n& C:\\mcps\\AwdUI-MCP\\scripts\\restart-repo-studio.ps1\n\n# Desarrollo (Vite :5173 + API :8765)\n& C:\\mcps\\AwdUI-MCP\\scripts\\start-repo-studio.ps1 -Dev`,
      },
      {
        type: "ul",
        items: [
          "UI: http://127.0.0.1:8765",
          "Base de datos: %USERPROFILE%\\.awdui-mcp\\repository.db",
          "Imágenes: %USERPROFILE%\\.awdui-mcp\\repository-assets\\{app_id}\\",
          "Se inicia automáticamente con el MCP awdui (AWDUI_REPO_STUDIO=1 por defecto)",
        ],
      },
    ],
  },
  {
    id: "repositorio",
    title: "Pestaña Repositorio",
    body: [
      {
        type: "h4",
        text: "Tres capas de mapa",
      },
      {
        type: "table",
        headers: ["Capa", "Dónde", "Para qué"],
        rows: [
          ["Funcional", "flows.json (corrida lab)", "Qué flujo ejecutar"],
          ["Descubrimiento", "element-map.md", "Lectura humana de una corrida"],
          ["Persistente", "repository.db + Repo Studio", "Localizadores + agent_hints entre sesiones"],
        ],
      },
      {
        type: "h4",
        text: "Árbol App → Ventana → Objeto",
      },
      {
        type: "ul",
        items: [
          "Expandí una app para ver ventanas (frmMain, Calculadora, …).",
          "Cada objeto tiene repo_path lógico (ej. frmMain/btnGuardar).",
          "Buscá por ruta, automation_id, propiedades, identificación QTP, hints de agente o nombre de app.",
          "Organizar repositorio: fusiona apps duplicadas y limpia buckets vacíos.",
        ],
      },
      {
        type: "h4",
        text: "Auto-captura",
      },
      {
        type: "p",
        text:
          "Tras find_element / click_element / smart_find exitosos (remember=true), el MCP puede guardar el control si set_target_window apunta a esa app y no está en la blocklist (Cursor, Chrome, etc.). Sin ventana objetivo no se auto-captura salvo AWDUI_AUTO_REPO=1.",
      },
    ],
  },
  {
    id: "inspector",
    title: "Inspector de objeto",
    body: [
      {
        type: "ul",
        items: [
          "Propiedades detectadas: snapshot UIA al momento del capture.",
          "Identificación QTP: mandatory / assistive / smart — qué propiedades usa repo_find para resolver.",
          "Captura del elemento: crop de pantalla si hubo interacción con screenshot.",
          "Hints para el agente IA: texto libre o clave: valor (verify_automation_id, precondicion, nota, …).",
          "Última resolución: backend y bbox del último match.",
        ],
      },
      {
        type: "h4",
        text: "Claves útiles en agent_hints",
      },
      {
        type: "table",
        headers: ["Clave", "Uso"],
        rows: [
          ["verify_automation_id", "Tras click/invoke, verificar otro control (ej. display de calculadora)"],
          ["metodo_preferido / preferred_tool", "Priorizar invoke_element vs click_element"],
          ["precondicion:", "Estado UI requerido antes de actuar"],
          ["nota:", "Lección operativa para el agente"],
        ],
      },
    ],
  },
  {
    id: "catalogo",
    title: "Pestaña Catálogo MCP",
    body: [
      {
        type: "p",
        text:
          "Referencia de frameworks, controles UIA (~40 tipos) y métodos Swf* (capa repo estilo QTP). No reemplaza la skill de automejora: es consulta rápida mientras automatizás.",
      },
      {
        type: "ul",
        items: [
          "Frameworks: hints de detect_framework y nivel UIA.",
          "Objetos Swf*: clases del repo (SwfButton, SwfComboBox…) y métodos repo_action.",
          "Controles UIA: patterns Microsoft → tools MCP (invoke_element, select_control_item, …).",
          "Tu repositorio: conteo de objetos guardados por framework y clase.",
        ],
      },
    ],
  },
  {
    id: "uia-niveles",
    title: "Niveles UIA (badges)",
    body: [
      {
        type: "p",
        text:
          "Los badges UIA full / partial / conditional / none indican qué tan bien esa tecnología expone su UI al árbol de accesibilidad de Windows — no la calidad del MCP.",
      },
      {
        type: "table",
        headers: ["Nivel", "Significado"],
        rows: [
          ["full", "Controles estándar con árbol UIA completo; automation_id suele ser fiable."],
          ["partial", "UIA en widgets estándar; custom, owner-drawn o flyouts pueden faltar."],
          ["conditional", "Depende de config o contenido (Electron, canvas, WebView, JAB)."],
          ["none", "Sin puente UIA usable en Windows (ej. GTK)."],
          ["unknown", "Framework no clasificado."],
        ],
      },
      {
        type: "h4",
        text: "Por framework",
      },
      {
        type: "table",
        headers: ["Framework", "UIA", "Por qué"],
        rows: [
          ["WPF", "full", "AutomationPeers en controles estándar"],
          ["JavaFX", "full", "UIA nativo en controles estándar"],
          ["WinForms", "partial", "Owner-drawn y DataGridView viejos pueden no exponerse"],
          ["Win32", "partial", "Common Controls OK; menús solo con menú abierto"],
          ["UWP / WinUI", "partial", "Shell ApplicationFrameHost; flyouts en otra ventana"],
          ["Qt", "partial", "QML/QtQuick sin Accessible{} = invisible"],
          ["Electron", "conditional", "Accesibilidad Chromium puede estar off; canvas sin nodos"],
          ["Java Swing", "conditional", "Requiere Java Access Bridge, no UIA puro"],
          ["GTK", "none", "Puente ATK→UIA no funcional en Windows"],
        ],
      },
      {
        type: "p",
        text:
          "full no garantiza cero fricción (listas virtualizadas, modales, timing). partial no significa «no usar UIA» — sigue siendo el primer camino programático.",
      },
    ],
  },
  {
    id: "tools",
    title: "Tools MCP del repositorio",
    body: [
      {
        type: "table",
        headers: ["Tool", "Rol"],
        rows: [
          ["set_target_window", "Fijar app antes de capturar / actuar (obligatorio para auto-repo)"],
          ["detect_framework", "Toolkit + UIA level + automation_profile (tools preferidas/bloqueadas)"],
          ["get_automation_profile", "Solo el perfil de tools/notas (útil en frameworks partial)"],
          ["repo_capture", "Guardar control desde spy/find (con agent_hints opcional)"],
          ["repo_find", "Resolver repo_path → elemento en pantalla"],
          ["repo_action", "Método Swf* (Click, Set, Select…) sobre repo_path"],
          ["repo_hints / repo_hints_set", "Leer / escribir notas del agente"],
          ["repo_list", "Inventario de la app activa"],
          ["discover_control_interaction", "Rol + patterns → estrategia de interacción"],
          ["find_element / invoke_element", "UIA directo; pueden auto-capturar al repo"],
        ],
      },
      {
        type: "h4",
        text: "Flujo típico",
      },
      {
        type: "ol",
        items: [
          "set_target_window('NombreApp')",
          "detect_framework(window_title=…) — leer Automation profile",
          "spy_inspect o find_element → entender rol y automation_id",
          "repo_capture si el control es estable",
          "repo_hints_set si hubo workaround (invoke falla → click)",
          "Próximas sesiones: repo_hints → repo_find / repo_action",
          "set_target_window('') al terminar",
        ],
      },
    ],
  },
  {
    id: "mantenimiento",
    title: "Mantenimiento",
    body: [
      {
        type: "ul",
        items: [
          "Organizar repositorio: fusiona Calculadora/Calculator duplicados y elimina apps junk.",
          "restart-repo-studio.ps1: reinicia API si falta /api/catalog (API viejo en :8765).",
          "Panel de app: detectar framework, editar hints de app, borrar app del repo.",
          "El punto verde del título parpadea cuando hay cambios externos (MCP capturó algo).",
        ],
      },
    ],
  },
  {
    id: "docs",
    title: "Documentación",
    body: [
      {
        type: "links",
        items: [
          {
            label: "OBJECT_REPOSITORY.md (repo Git)",
            href: "https://github.com/aostapow/AwdUI-MCP/blob/main/docs/OBJECT_REPOSITORY.md",
          },
          {
            label: "MCP_TOOLS_REFERENCE.md",
            href: "https://github.com/aostapow/AwdUI-MCP/blob/main/docs/MCP_TOOLS_REFERENCE.md",
          },
          {
            label: "Catálogo UIA (skill)",
            href: "https://github.com/aostapow/AwdUI-MCP/blob/main/.cursor/skills/awdui-mcp-automejora/references/patterns/control-catalog.md",
          },
          {
            label: "Repositorio Git AwdUI-MCP",
            href: "https://github.com/aostapow/AwdUI-MCP",
          },
        ],
      },
    ],
  },
];
