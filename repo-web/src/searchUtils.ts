/** Normaliza texto de búsqueda (trim + minúsculas). */
export function normalizeSearchQuery(q: string): string {
  return q.trim().toLowerCase();
}

/** ¿El texto contiene la query? Query vacía → coincide todo. */
export function matchesSearch(haystack: string, query: string): boolean {
  const nq = normalizeSearchQuery(query);
  if (!nq) return true;
  return haystack.toLowerCase().includes(nq);
}

/** ¿Alguna de las partes contiene la query? */
export function matchesSearchAny(
  query: string,
  ...parts: (string | undefined | null | false)[]
): boolean {
  const nq = normalizeSearchQuery(query);
  if (!nq) return true;
  return parts.some((p) => p && String(p).toLowerCase().includes(nq));
}
