import { normalizeSearchQuery } from "./searchUtils";

type Props = {
  text: string;
  query: string;
};

/** Resalta la primera coincidencia de query en text. */
export function SearchHighlight({ text, query }: Props) {
  const nq = normalizeSearchQuery(query);
  if (!nq) return <>{text}</>;

  const lower = text.toLowerCase();
  const idx = lower.indexOf(nq);
  if (idx < 0) return <>{text}</>;

  return (
    <>
      {text.slice(0, idx)}
      <mark className="search-mark">{text.slice(idx, idx + nq.length)}</mark>
      {text.slice(idx + nq.length)}
    </>
  );
}
