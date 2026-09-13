import { HelpBlock, HelpSection } from "./helpContent";
import { matchesSearch, matchesSearchAny } from "./searchUtils";

function blockText(block: HelpBlock): string {
  switch (block.type) {
    case "p":
    case "h4":
    case "code":
      return block.text;
    case "ul":
    case "ol":
      return block.items.join(" ");
    case "table":
      return [...block.headers, ...block.rows.flat()].join(" ");
    case "links":
      return block.items.map((l) => `${l.label} ${l.href}`).join(" ");
    default:
      return "";
  }
}

export function blockMatchesQuery(block: HelpBlock, query: string): boolean {
  const q = query.trim();
  if (!q) return true;
  return matchesSearch(blockText(block), q);
}

/** Filtra ítems dentro de listas; si el bloque no es lista, devuelve el bloque o null. */
export function filterHelpBlock(block: HelpBlock, query: string): HelpBlock | null {
  const q = query.trim();
  if (!q) return block;

  switch (block.type) {
    case "ul":
    case "ol": {
      const items = block.items.filter((item) => matchesSearch(item, q));
      if (items.length === 0) return null;
      return { ...block, items };
    }
    case "table": {
      const headersMatch = block.headers.some((h) => matchesSearch(h, q));
      const rows = block.rows.filter((row) =>
        row.some((cell) => matchesSearch(cell, q))
      );
      if (!headersMatch && rows.length === 0) return null;
      return {
        type: "table",
        headers: block.headers,
        rows: rows.length > 0 ? rows : block.rows,
      };
    }
    case "links": {
      const items = block.items.filter(
        (l) => matchesSearch(l.label, q) || matchesSearch(l.href, q)
      );
      if (items.length === 0) return null;
      return { type: "links", items };
    }
    default:
      return blockMatchesQuery(block, q) ? block : null;
  }
}

export type HelpSectionMatch = {
  section: HelpSection;
  blocks: HelpBlock[];
};

/** Búsqueda profunda: secciones con solo los bloques que coinciden. */
export function searchHelpContent(
  sections: HelpSection[],
  query: string
): HelpSectionMatch[] {
  const q = query.trim();
  if (!q) {
    return sections.map((section) => ({ section, blocks: section.body }));
  }

  const out: HelpSectionMatch[] = [];
  for (const section of sections) {
    const titleMatch = matchesSearchAny(q, section.title, section.id);
    const blocks = section.body
      .map((block) => filterHelpBlock(block, q))
      .filter((b): b is HelpBlock => b !== null);

    if (titleMatch || blocks.length > 0) {
      out.push({ section, blocks: blocks.length > 0 ? blocks : section.body });
    }
  }
  return out;
}

/** @deprecated usar searchHelpContent */
export function filterHelpSections(
  sections: HelpSection[],
  query: string
): HelpSection[] {
  return searchHelpContent(sections, query).map((m) => m.section);
}
