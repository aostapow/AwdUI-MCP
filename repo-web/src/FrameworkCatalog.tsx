import { useEffect, useMemo, useState } from "react";

import { fetchCatalog, FrameworkCatalogData } from "./api";

import {

  CatalogHit,

  CatalogNavigate,

  filterSwfMethods,

  filterUiaBindings,

  searchCatalog,

} from "./catalogSearch";

import { SearchHighlight } from "./SearchHighlight";

import { matchesSearchAny } from "./searchUtils";



type Framework = FrameworkCatalogData["frameworks"][number];

type SwfClass = FrameworkCatalogData["swf_classes"][number];

type UiaControl = FrameworkCatalogData["uia_controls"][number];



type Props = {

  searchQuery?: string;

};



function applyNavigate(

  nav: CatalogNavigate,

  setters: {

    setFrameworkId: (id: string) => void;

    setTab: (t: "swf" | "uia") => void;

    setSelectedSwf: (c: string) => void;

    setSelectedRole: (r: string) => void;

    setMethodRef: (m: string | null) => void;

  },

  catalog: FrameworkCatalogData

) {

  if (nav.frameworkId) setters.setFrameworkId(nav.frameworkId);

  if (nav.tab === "swf" || nav.tab === "uia") setters.setTab(nav.tab);

  if (nav.swfClass) setters.setSelectedSwf(nav.swfClass);

  if (nav.uiaRole) setters.setSelectedRole(nav.uiaRole);

  if (nav.tab === "method_ref" && nav.methodRef) {

    setters.setMethodRef(nav.methodRef);

    const fw = catalog.frameworks.find((f) => f.uses_swf_repo);

    if (fw) {

      setters.setFrameworkId(fw.id);

      setters.setTab("swf");

    }

  } else {

    setters.setMethodRef(null);

  }

}



export default function FrameworkCatalog({ searchQuery = "" }: Props) {

  const [catalog, setCatalog] = useState<FrameworkCatalogData | null>(null);

  const [error, setError] = useState("");

  const [frameworkId, setFrameworkId] = useState("winforms");

  const [selectedSwf, setSelectedSwf] = useState("SwfButton");

  const [selectedRole, setSelectedRole] = useState("Button");

  const [tab, setTab] = useState<"swf" | "uia">("swf");

  const [methodRef, setMethodRef] = useState<string | null>(null);

  const [activeHitId, setActiveHitId] = useState<string | null>(null);



  useEffect(() => {

    fetchCatalog()

      .then(setCatalog)

      .catch((e) => setError(String(e)));

  }, []);



  const hasSearch = Boolean(searchQuery.trim());



  const searchHits = useMemo(

    () => (catalog && hasSearch ? searchCatalog(catalog, searchQuery) : []),

    [catalog, searchQuery, hasSearch]

  );



  const hitsByCategory = useMemo(() => {

    const map = new Map<string, CatalogHit[]>();

    for (const hit of searchHits) {

      const list = map.get(hit.category) ?? [];

      list.push(hit);

      map.set(hit.category, list);

    }

    return map;

  }, [searchHits]);



  const framework = useMemo(

    () => catalog?.frameworks.find((f) => f.id === frameworkId) ?? null,

    [catalog, frameworkId]

  );



  const swfDetail = useMemo(

    () => catalog?.swf_classes.find((c) => c.swf_class === selectedSwf) ?? null,

    [catalog, selectedSwf]

  );



  const uiaDetail = useMemo(

    () => catalog?.uia_controls.find((c) => c.role === selectedRole) ?? null,

    [catalog, selectedRole]

  );



  const storedForFw = catalog?.stored?.by_framework?.[frameworkId] ?? null;

  const methodRefDetail = methodRef && catalog?.repo_method_reference[methodRef];



  const navigateToHit = (hit: CatalogHit) => {

    if (!catalog) return;

    setActiveHitId(hit.id);

    applyNavigate(hit.navigate, {

      setFrameworkId,

      setTab,

      setSelectedSwf,

      setSelectedRole,

      setMethodRef,

    }, catalog);

  };



  useEffect(() => {
    if (!catalog) return;
    if (!hasSearch || searchHits.length === 0) {
      setActiveHitId(null);
      setMethodRef(null);
      return;
    }
    const first = searchHits[0];
    setActiveHitId(first.id);
    applyNavigate(first.navigate, {
      setFrameworkId,
      setTab,
      setSelectedSwf,
      setSelectedRole,
      setMethodRef,
    }, catalog);
  }, [catalog, searchQuery, searchHits, hasSearch]);



  if (error) {

    return <div className="catalog-empty">Error cargando catálogo: {error}</div>;

  }

  if (!catalog) {

    return <div className="catalog-empty">Cargando catálogo MCP…</div>;

  }



  const showSwf = framework?.uses_swf_repo ?? false;

  const filteredSwfMethods = swfDetail

    ? filterSwfMethods(swfDetail.methods, searchQuery)

    : [];

  const filteredUiaBindings = uiaDetail

    ? filterUiaBindings(uiaDetail.act_bindings, searchQuery)

    : [];



  const storedEntries = storedForFw

    ? Object.entries(storedForFw).filter(([cls]) =>

        hasSearch ? matchesSearchAny(searchQuery, cls) : true

      )

    : [];



  const frameworkHints = framework

    ? framework.hints.filter((h) => (hasSearch ? matchesSearchAny(searchQuery, h) : true))

    : [];



  return (

    <div className="catalog">

      <header className="catalog-header">

        <h2>Catálogo — Frameworks, objetos y métodos</h2>

        <p className="muted">

          Referencia UIA + capa Swf* (repo) y tools MCP. Fuente:{" "}

          <a href={catalog.source_uia_map} target="_blank" rel="noreferrer">

            Microsoft UIA pattern map

          </a>

          {hasSearch && (

            <> · {searchHits.length} coincidencia(s) en todo el catálogo</>

          )}

        </p>

      </header>



      {hasSearch && (

        <section className="catalog-search-results" aria-label="Resultados de búsqueda">

          {searchHits.length === 0 ? (

            <p className="search-empty">

              Sin coincidencias para «{searchQuery.trim()}» en frameworks, Swf*, UIA, tools MCP,

              métodos repo ni objetos guardados.

            </p>

          ) : (

            [...hitsByCategory.entries()].map(([category, hits]) => (

              <div key={category} className="catalog-search-group">

                <h3 className="catalog-search-group-title">

                  {category} ({hits.length})

                </h3>

                <ul className="catalog-search-list">

                  {hits.map((hit) => (

                    <li key={hit.id}>

                      <button

                        type="button"

                        className={`catalog-search-hit${activeHitId === hit.id ? " active" : ""}`}

                        onClick={() => navigateToHit(hit)}

                      >

                        <span className="catalog-search-hit-path">

                          <SearchHighlight text={hit.path} query={searchQuery} />

                        </span>

                        <span className="catalog-search-hit-title">

                          <SearchHighlight text={hit.title} query={searchQuery} />

                        </span>

                        <span className="catalog-search-hit-detail muted">

                          <SearchHighlight text={hit.detail} query={searchQuery} />

                        </span>

                      </button>

                    </li>

                  ))}

                </ul>

              </div>

            ))

          )}

        </section>

      )}



      {methodRefDetail && (

        <section className="catalog-method-ref section">

          <h3>Método repo_action — {methodRef}</h3>

          <p>

            <strong>Tools MCP:</strong> {methodRefDetail.mcp_tools.join(", ")}

          </p>

          <p>{methodRefDetail.summary}</p>

        </section>

      )}



      <div className={`catalog-layout${hasSearch ? " catalog-layout--with-search" : ""}`}>

        <aside className="catalog-fw-list">

          <h3>Frameworks</h3>

          {catalog.frameworks.map((fw: Framework) => (

            <button

              key={fw.id}

              type="button"

              className={`catalog-fw-btn${frameworkId === fw.id ? " active" : ""}`}

              onClick={() => {

                setFrameworkId(fw.id);

                setTab(fw.uses_swf_repo ? "swf" : "uia");

                setMethodRef(null);

              }}

            >

              <span className="catalog-fw-label">{fw.label}</span>

              <span className={`catalog-badge badge-${fw.uia_support}`}>

                UIA {fw.uia_support}

              </span>

            </button>

          ))}

        </aside>



        <section className="catalog-main">

          {framework && (

            <div className="catalog-fw-panel">

              <h3>{framework.label}</h3>

              {(frameworkHints.length > 0 || !hasSearch) && (

                <ul className="catalog-hints">

                  {(hasSearch ? frameworkHints : framework.hints).map((h) => (

                    <li key={h}>

                      <SearchHighlight text={h} query={searchQuery} />

                    </li>

                  ))}

                </ul>

              )}

              {storedEntries.length > 0 && (

                <div className="catalog-stored">

                  <h4>Objetos en tu repositorio</h4>

                  <table className="props">

                    <thead>

                      <tr>

                        <th>Clase Swf / rol</th>

                        <th>Cantidad</th>

                      </tr>

                    </thead>

                    <tbody>

                      {storedEntries

                        .sort(([a], [b]) => a.localeCompare(b))

                        .map(([cls, n]) => (

                          <tr key={cls}>

                            <td>

                              <SearchHighlight text={cls} query={searchQuery} />

                            </td>

                            <td>{n}</td>

                          </tr>

                        ))}

                    </tbody>

                  </table>

                </div>

              )}

            </div>

          )}



          <div className="catalog-tabs">

            {showSwf && (

              <button

                type="button"

                className={tab === "swf" ? "active" : ""}

                onClick={() => setTab("swf")}

              >

                Objetos Swf* (repo)

              </button>

            )}

            <button

              type="button"

              className={tab === "uia" ? "active" : ""}

              onClick={() => setTab("uia")}

            >

              Controles UIA

            </button>

          </div>



          {tab === "swf" && showSwf && (

            <div className="catalog-split">

              <div className="catalog-list">

                {catalog.swf_classes
                  .filter((c) => {
                    if (!hasSearch) return true;
                    if (c.swf_class === selectedSwf) return true;
                    return searchHits.some(
                      (h) =>
                        h.navigate.swfClass === c.swf_class ||
                        h.path.includes(c.swf_class)
                    );
                  })

                  .map((c: SwfClass) => (

                    <button

                      key={c.swf_class}

                      type="button"

                      className={selectedSwf === c.swf_class ? "active" : ""}

                      onClick={() => {

                        setSelectedSwf(c.swf_class);

                        setMethodRef(null);

                      }}

                    >

                      {c.swf_class}

                      {c.uia_role ? ` → ${c.uia_role}` : ""}

                    </button>

                  ))}

              </div>

              <div className="catalog-detail">

                {swfDetail && (

                  <>

                    <h4>{swfDetail.swf_class}</h4>

                    <p>

                      <strong>Rol UIA:</strong> {swfDetail.uia_role || "—"}

                    </p>

                    <p>

                      <strong>Identificación:</strong> mandatory=[

                      {swfDetail.mandatory.join(", ")}] assistive=[

                      {swfDetail.assistive.join(", ")}]

                      {swfDetail.smart.length > 0 && (

                        <> smart=[{swfDetail.smart.join(", ")}]</>

                      )}

                    </p>

                    <h4>Métodos repo_action</h4>

                    {(filteredSwfMethods.length > 0 || !hasSearch) ? (

                      <table className="props catalog-methods">

                        <thead>

                          <tr>

                            <th>Método</th>

                            <th>Tools MCP</th>

                            <th>Descripción</th>

                          </tr>

                        </thead>

                        <tbody>

                          {(hasSearch ? filteredSwfMethods : swfDetail.methods).map((m) => (

                            <tr key={m.name}>

                              <td><code>{m.name}</code></td>

                              <td>

                                <SearchHighlight

                                  text={m.mcp_tools.join(", ")}

                                  query={searchQuery}

                                />

                              </td>

                              <td>

                                <SearchHighlight text={m.summary} query={searchQuery} />

                              </td>

                            </tr>

                          ))}

                        </tbody>

                      </table>

                    ) : (

                      <p className="muted">Ningún método coincide con la búsqueda.</p>

                    )}

                  </>

                )}

              </div>

            </div>

          )}



          {(tab === "uia" || !showSwf) && (

            <div className="catalog-split">

              <div className="catalog-list catalog-list--tall">

                {catalog.uia_controls
                  .filter((c) => {
                    if (!hasSearch) return true;
                    if (c.role === selectedRole) return true;
                    return searchHits.some(
                      (h) =>
                        h.navigate.uiaRole === c.role ||
                        h.path.includes(c.role)
                    );
                  })

                  .map((c: UiaControl) => (

                    <button

                      key={c.role}

                      type="button"

                      className={selectedRole === c.role ? "active" : ""}

                      onClick={() => {

                        setSelectedRole(c.role);

                        setMethodRef(null);

                      }}

                    >

                      {c.role}

                    </button>

                  ))}

              </div>

              <div className="catalog-detail">

                {uiaDetail && (

                  <>

                    <h4>{uiaDetail.role}</h4>

                    <p>

                      <strong>Patterns MS:</strong> must=

                      {(uiaDetail.patterns_ms.must || []).join(", ") || "—"} ·

                      conditional=

                      {(uiaDetail.patterns_ms.conditional || []).join(", ") || "—"}

                      {(uiaDetail.patterns_ms.not || []).length > 0 && (

                        <> · not={(uiaDetail.patterns_ms.not || []).join(", ")}</>

                      )}

                    </p>

                    <p>

                      <strong>Leer:</strong> {uiaDetail.read_tools.join(", ")}

                    </p>

                    <h4>Actuar (bindings)</h4>

                    {(filteredUiaBindings.length > 0 || !hasSearch) ? (

                      (hasSearch ? filteredUiaBindings : uiaDetail.act_bindings).map((b) => (

                        <div key={b.id} className="catalog-binding">

                          <div>

                            <code>{b.tools.join(" → ")}</code>

                            {b.patterns.length > 0 && (

                              <span className="muted"> [{b.patterns.join(", ")}]</span>

                            )}

                          </div>

                          <ul>

                            {b.steps

                              .filter((s) =>

                                !hasSearch || matchesSearchAny(searchQuery, s)

                              )

                              .map((s) => (

                                <li key={s}>

                                  <SearchHighlight text={s} query={searchQuery} />

                                </li>

                              ))}

                          </ul>

                        </div>

                      ))

                    ) : (

                      <p className="muted">Ningún binding coincide con la búsqueda.</p>

                    )}

                    {uiaDetail.fallback_tools.length > 0 && (

                      <p>

                        <strong>Fallback:</strong>{" "}

                        {uiaDetail.fallback_tools.join(", ")}

                      </p>

                    )}

                  </>

                )}

              </div>

            </div>

          )}

        </section>

      </div>

    </div>

  );

}


