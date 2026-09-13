import { useEffect, useMemo, useRef, useState } from "react";

import { HELP_SECTIONS, HelpBlock } from "./helpContent";

import { searchHelpContent } from "./helpSearch";

import { SearchHighlight } from "./SearchHighlight";



function Block({

  block,

  searchQuery,

}: {

  block: HelpBlock;

  searchQuery: string;

}) {

  switch (block.type) {

    case "p":

      return (

        <p>

          <SearchHighlight text={block.text} query={searchQuery} />

        </p>

      );

    case "h4":

      return (

        <h4>

          <SearchHighlight text={block.text} query={searchQuery} />

        </h4>

      );

    case "ul":

      return (

        <ul>

          {block.items.map((item) => (

            <li key={item}>

              <SearchHighlight text={item} query={searchQuery} />

            </li>

          ))}

        </ul>

      );

    case "ol":

      return (

        <ol>

          {block.items.map((item) => (

            <li key={item}>

              <SearchHighlight text={item} query={searchQuery} />

            </li>

          ))}

        </ol>

      );

    case "code":

      return (

        <pre className="help-code">

          <SearchHighlight text={block.text} query={searchQuery} />

        </pre>

      );

    case "table":

      return (

        <table className="props help-table">

          <thead>

            <tr>

              {block.headers.map((h) => (

                <th key={h}>

                  <SearchHighlight text={h} query={searchQuery} />

                </th>

              ))}

            </tr>

          </thead>

          <tbody>

            {block.rows.map((row, i) => (

              <tr key={i}>

                {row.map((cell, j) => (

                  <td key={j}>

                    <SearchHighlight text={cell} query={searchQuery} />

                  </td>

                ))}

              </tr>

            ))}

          </tbody>

        </table>

      );

    case "links":

      return (

        <ul className="help-links">

          {block.items.map((l) => (

            <li key={l.href}>

              <a href={l.href} target="_blank" rel="noreferrer">

                <SearchHighlight text={l.label} query={searchQuery} />

              </a>

            </li>

          ))}

        </ul>

      );

    default:

      return null;

  }

}



export default function HelpPanel({ searchQuery = "" }: { searchQuery?: string }) {

  const [activeId, setActiveId] = useState(HELP_SECTIONS[0].id);

  const articleRef = useRef<HTMLElement>(null);

  const hasSearch = Boolean(searchQuery.trim());



  const matches = useMemo(

    () => searchHelpContent(HELP_SECTIONS, searchQuery),

    [searchQuery]

  );



  const blockCount = useMemo(

    () => matches.reduce((n, m) => n + m.blocks.length, 0),

    [matches]

  );



  useEffect(() => {

    if (!hasSearch || matches.length === 0) return;

    if (!matches.some((m) => m.section.id === activeId)) {

      setActiveId(matches[0].section.id);

    }

  }, [matches, activeId, hasSearch]);



  useEffect(() => {

    if (!hasSearch || !articleRef.current) return;

    const el = articleRef.current.querySelector(`[data-section-id="${activeId}"]`);

    el?.scrollIntoView({ behavior: "smooth", block: "start" });

  }, [activeId, hasSearch]);



  const singleSection = !hasSearch

    ? HELP_SECTIONS.find((s) => s.id === activeId) ?? HELP_SECTIONS[0]

    : null;



  return (

    <div className="help">

      <header className="help-header">

        <h2>Ayuda — Repo Studio y AwdUI MCP</h2>

        <p className="muted">

          Guía de uso del repositorio, catálogo UIA y herramientas MCP relacionadas.

          {hasSearch && matches.length > 0 && (

            <> · {matches.length} sección(es), {blockCount} bloque(s)</>

          )}

        </p>

      </header>

      <div className="help-layout">

        <nav className="help-nav" aria-label="Secciones de ayuda">

          {hasSearch && matches.length === 0 && (

            <p className="search-empty">Sin coincidencias para «{searchQuery.trim()}»</p>

          )}

          {(hasSearch ? matches : HELP_SECTIONS.map((s) => ({ section: s, blocks: s.body }))).map(

            ({ section, blocks }) => (

              <button

                key={section.id}

                type="button"

                className={activeId === section.id ? "active" : ""}

                onClick={() => setActiveId(section.id)}

              >

                {section.title}

                {hasSearch && blocks.length > 0 && (

                  <span className="help-nav-count">{blocks.length}</span>

                )}

              </button>

            )

          )}

        </nav>

        <article className="help-article" ref={articleRef}>

          {hasSearch ? (

            matches.length === 0 ? (

              <p className="muted">

                Probá con otro término: tools MCP, niveles UIA, repo_capture, hints, etc.

              </p>

            ) : (

              matches.map(({ section, blocks }) => (

                <section

                  key={section.id}

                  data-section-id={section.id}

                  className={`help-section-chunk${activeId === section.id ? " help-section-chunk--active" : ""}`}

                >

                  <h3>

                    <SearchHighlight text={section.title} query={searchQuery} />

                  </h3>

                  {blocks.map((block, i) => (

                    <Block

                      key={`${section.id}-${i}`}

                      block={block}

                      searchQuery={searchQuery}

                    />

                  ))}

                </section>

              ))

            )

          ) : singleSection ? (

            <>

              <h3>{singleSection.title}</h3>

              {singleSection.body.map((block, i) => (

                <Block

                  key={`${singleSection.id}-${i}`}

                  block={block}

                  searchQuery=""

                />

              ))}

            </>

          ) : null}

        </article>

      </div>

    </div>

  );

}


