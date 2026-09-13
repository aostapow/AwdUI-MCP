import { FrameworkCatalogData } from "./api";
import { matchesSearch, matchesSearchAny, normalizeSearchQuery } from "./searchUtils";

export type CatalogNavigate = {
  frameworkId?: string;
  tab: "swf" | "uia" | "framework" | "method_ref";
  swfClass?: string;
  uiaRole?: string;
  methodRef?: string;
};

export type CatalogHit = {
  id: string;
  category: string;
  path: string;
  title: string;
  detail: string;
  navigate: CatalogNavigate;
};

function pushHit(
  hits: CatalogHit[],
  seen: Set<string>,
  hit: CatalogHit
): void {
  if (seen.has(hit.id)) return;
  seen.add(hit.id);
  hits.push(hit);
}

/** Índice plano: frameworks, Swf*, UIA, métodos repo, objetos guardados. */
export function searchCatalog(
  catalog: FrameworkCatalogData,
  query: string
): CatalogHit[] {
  const q = query.trim();
  if (!q) return [];

  const hits: CatalogHit[] = [];
  const seen = new Set<string>();

  for (const fw of catalog.frameworks) {
    const fwText = [fw.id, fw.label, fw.uia_support, ...fw.hints].join(" ");
    if (matchesSearch(fwText, q)) {
      pushHit(hits, seen, {
        id: `fw:${fw.id}`,
        category: "Framework",
        path: fw.label,
        title: fw.label,
        detail: fw.hints[0] || `UIA ${fw.uia_support}`,
        navigate: { frameworkId: fw.id, tab: fw.uses_swf_repo ? "swf" : "uia" },
      });
    }

    const stored = catalog.stored?.by_framework?.[fw.id];
    if (stored) {
      for (const [cls, count] of Object.entries(stored)) {
        const text = `${fw.label} ${cls} ${count} objetos guardados`;
        if (matchesSearch(text, q)) {
          pushHit(hits, seen, {
            id: `stored-fw:${fw.id}:${cls}`,
            category: "Tu repositorio",
            path: `${fw.label} › ${cls}`,
            title: cls,
            detail: `${count} objeto(s) guardado(s)`,
            navigate: {
              frameworkId: fw.id,
              tab: fw.uses_swf_repo ? "swf" : "uia",
              swfClass: cls.startsWith("Swf") ? cls : undefined,
              uiaRole: !cls.startsWith("Swf") ? cls : undefined,
            },
          });
        }
      }
    }
  }

  if (catalog.stored?.apps) {
    for (const app of catalog.stored.apps) {
      const appText = [
        app.app_name,
        app.app_id,
        app.framework,
        String(app.object_count),
        ...Object.keys(app.by_class),
      ].join(" ");
      if (matchesSearch(appText, q)) {
        pushHit(hits, seen, {
          id: `stored-app:${app.app_id}`,
          category: "Tu repositorio",
          path: `${app.app_name} (${app.framework})`,
          title: app.app_name,
          detail: `${app.object_count} objeto(s): ${Object.keys(app.by_class).join(", ")}`,
          navigate: {
            frameworkId: app.framework,
            tab: "framework",
          },
        });
      }
      for (const [cls, count] of Object.entries(app.by_class)) {
        const text = `${app.app_name} ${cls} ${count}`;
        if (matchesSearch(text, q)) {
          pushHit(hits, seen, {
            id: `stored-app-cls:${app.app_id}:${cls}`,
            category: "Tu repositorio",
            path: `${app.app_name} › ${cls}`,
            title: `${app.app_name} — ${cls}`,
            detail: `${count} instancia(s)`,
            navigate: {
              frameworkId: app.framework,
              tab: cls.startsWith("Swf") ? "swf" : "uia",
              swfClass: cls.startsWith("Swf") ? cls : undefined,
              uiaRole: !cls.startsWith("Swf") ? cls : undefined,
            },
          });
        }
      }
    }
  }

  for (const c of catalog.swf_classes) {
    const classText = [
      c.swf_class,
      c.uia_role,
      ...c.mandatory,
      ...c.assistive,
      ...c.smart,
    ].join(" ");

    if (matchesSearch(classText, q)) {
      pushHit(hits, seen, {
        id: `swf:${c.swf_class}`,
        category: "Objeto Swf*",
        path: `Swf* › ${c.swf_class}`,
        title: c.swf_class,
        detail: c.uia_role ? `Rol UIA: ${c.uia_role}` : "Clase del repositorio",
        navigate: { frameworkId: "winforms", tab: "swf", swfClass: c.swf_class },
      });
    }

    for (const m of c.methods) {
      const methodText = [c.swf_class, m.name, m.summary, ...m.mcp_tools].join(" ");
      if (matchesSearch(methodText, q)) {
        pushHit(hits, seen, {
          id: `swf-method:${c.swf_class}:${m.name}`,
          category: "Método repo_action",
          path: `${c.swf_class} › ${m.name}`,
          title: `${c.swf_class}.${m.name}`,
          detail: `${m.mcp_tools.join(", ")} — ${m.summary}`,
          navigate: { frameworkId: "winforms", tab: "swf", swfClass: c.swf_class },
        });
      }
      for (const tool of m.mcp_tools) {
        if (matchesSearch(tool, q)) {
          pushHit(hits, seen, {
            id: `swf-tool:${c.swf_class}:${m.name}:${tool}`,
            category: "Tool MCP",
            path: `${c.swf_class} › ${m.name} › ${tool}`,
            title: tool,
            detail: `Método ${m.name} en ${c.swf_class}`,
            navigate: { frameworkId: "winforms", tab: "swf", swfClass: c.swf_class },
          });
        }
      }
    }
  }

  for (const c of catalog.uia_controls) {
    const roleText = [
      c.role,
      ...(c.patterns_ms.must || []),
      ...(c.patterns_ms.conditional || []),
      ...(c.patterns_ms.not || []),
      ...c.read_tools,
      ...c.fallback_tools,
    ].join(" ");

    if (matchesSearch(roleText, q)) {
      pushHit(hits, seen, {
        id: `uia:${c.role}`,
        category: "Control UIA",
        path: `UIA › ${c.role}`,
        title: c.role,
        detail: `Leer: ${c.read_tools.join(", ") || "—"}`,
        navigate: { tab: "uia", uiaRole: c.role },
      });
    }

    for (const tool of c.read_tools) {
      if (matchesSearch(tool, q)) {
        pushHit(hits, seen, {
          id: `uia-read:${c.role}:${tool}`,
          category: "Tool MCP (leer)",
          path: `${c.role} › leer › ${tool}`,
          title: tool,
          detail: `Control UIA ${c.role}`,
          navigate: { tab: "uia", uiaRole: c.role },
        });
      }
    }

    for (const b of c.act_bindings) {
      const bindingText = [c.role, b.id, ...b.tools, ...b.patterns, ...b.steps].join(" ");
      if (matchesSearch(bindingText, q)) {
        pushHit(hits, seen, {
          id: `uia-act:${c.role}:${b.id}`,
          category: "Binding UIA",
          path: `${c.role} › ${b.id || b.tools.join(" → ")}`,
          title: b.id || b.tools.join(" → "),
          detail: b.steps[0] || b.patterns.join(", "),
          navigate: { tab: "uia", uiaRole: c.role },
        });
      }
      for (const step of b.steps) {
        if (matchesSearch(step, q)) {
          pushHit(hits, seen, {
            id: `uia-step:${c.role}:${b.id}:${step}`,
            category: "Paso UIA",
            path: `${c.role} › ${b.id} › paso`,
            title: step,
            detail: `Tools: ${b.tools.join(" → ")}`,
            navigate: { tab: "uia", uiaRole: c.role },
          });
        }
      }
    }

    for (const tool of c.fallback_tools) {
      if (matchesSearch(tool, q)) {
        pushHit(hits, seen, {
          id: `uia-fallback:${c.role}:${tool}`,
          category: "Fallback UIA",
          path: `${c.role} › fallback › ${tool}`,
          title: tool,
          detail: `Control UIA ${c.role}`,
          navigate: { tab: "uia", uiaRole: c.role },
        });
      }
    }
  }

  for (const [name, meta] of Object.entries(catalog.repo_method_reference)) {
    const text = [name, meta.summary, ...meta.mcp_tools].join(" ");
    if (matchesSearch(text, q)) {
      pushHit(hits, seen, {
        id: `method-ref:${name}`,
        category: "Método repo (referencia)",
        path: `repo_action › ${name}`,
        title: name,
        detail: `${meta.mcp_tools.join(", ")} — ${meta.summary}`,
        navigate: { tab: "method_ref", methodRef: name },
      });
    }
  }

  return hits;
}

/** Filtra filas de métodos Swf* visibles en el detalle. */
export function filterSwfMethods<T extends { name: string; summary: string; mcp_tools: string[] }>(
  methods: T[],
  query: string
): T[] {
  const q = query.trim();
  if (!q) return methods;
  return methods.filter((m) =>
    matchesSearchAny(q, m.name, m.summary, ...m.mcp_tools)
  );
}

/** Filtra bindings UIA visibles en el detalle. */
export function filterUiaBindings<
  T extends { id: string; tools: string[]; patterns: string[]; steps: string[] },
>(bindings: T[], query: string): T[] {
  const q = query.trim();
  if (!q) return bindings;
  return bindings.filter((b) =>
    matchesSearchAny(q, b.id, ...b.tools, ...b.patterns, ...b.steps)
  );
}

export function catalogQueryTokens(query: string): string[] {
  return normalizeSearchQuery(query).split(/\s+/).filter(Boolean);
}
