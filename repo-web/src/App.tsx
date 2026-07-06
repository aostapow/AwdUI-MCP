import { useCallback, useEffect, useState } from "react";
import {
  AppInfo,
  RepoObject,
  fetchApps,
  fetchObject,
  fetchTree,
  saveObject,
  searchObjects,
} from "./api";

type TreeData = Awaited<ReturnType<typeof fetchTree>>;

function tierKeys(obj: RepoObject | null): string[] {
  if (!obj?.full_properties) {
    return ["name", "role", "automation_id", "class_name"];
  }
  return Object.keys(obj.full_properties).filter(
    (k) => !k.startsWith("_") && typeof obj.full_properties![k] !== "object"
  );
}

export default function App() {
  const [apps, setApps] = useState<AppInfo[]>([]);
  const [trees, setTrees] = useState<Record<string, TreeData>>({});
  const [selected, setSelected] = useState<string>("");
  const [detail, setDetail] = useState<RepoObject | null>(null);
  const [hints, setHints] = useState("");
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<RepoObject[]>([]);
  const [status, setStatus] = useState("");

  const loadApps = useCallback(async () => {
    const list = await fetchApps();
    setApps(list);
  }, []);

  useEffect(() => {
    loadApps().catch((e) => setStatus(String(e)));
  }, [loadApps]);

  const openApp = async (appId: string) => {
    if (trees[appId]) return;
    const tree = await fetchTree(appId);
    setTrees((t) => ({ ...t, [appId]: tree }));
  };

  const selectObject = async (repoPath: string) => {
    setSelected(repoPath);
    const data = await fetchObject(repoPath);
    setDetail(data.object);
    setHints(data.agent_hints || "");
    setSearchResults([]);
  };

  const onSearch = async () => {
    if (!search.trim()) {
      setSearchResults([]);
      return;
    }
    const data = await searchObjects(search.trim());
    setSearchResults(data.results);
  };

  const toggleTier = (
    tier: "mandatory" | "assistive" | "smart",
    key: string,
    checked: boolean
  ) => {
    if (!detail) return;
    const ident = { ...detail.identification };
    const bucket = { ...ident[tier] };
    if (checked) {
      const val = String(detail.full_properties?.[key] ?? detail.identification.assistive[key] ?? "");
      if (val) bucket[key] = val;
    } else {
      delete bucket[key];
    }
    ident[tier] = bucket;
    setDetail({ ...detail, identification: ident });
  };

  const save = async () => {
    if (!detail || !selected) return;
    await saveObject(selected, {
      logical_name: detail.logical_name,
      identification: detail.identification,
      agent_hints: hints,
      full_properties: detail.full_properties,
    });
    setStatus("Guardado");
    await loadApps();
  };

  const keys = tierKeys(detail);

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>AwdUI Repo Studio</h1>
        <input
          className="search"
          placeholder="Buscar objeto..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearch()}
        />
        {searchResults.length > 0 && (
          <div className="section">
            {searchResults.map((r) => (
              <div key={r.repo_path} className="tree-object">
                <button
                  className={selected === r.repo_path ? "active" : ""}
                  onClick={() => selectObject(r.repo_path)}
                >
                  {r.repo_path}
                </button>
              </div>
            ))}
          </div>
        )}
        {apps.map((app) => (
          <div key={app.app_id} className="tree-app">
            <button onClick={() => openApp(app.app_id)}>{app.app_name}</button>
            {trees[app.app_id]?.windows.map((win) => (
              <div key={win.window_key} className="tree-window">
                {win.window_key}
                {win.objects.map((obj) => (
                  <div key={obj.repo_path} className="tree-object">
                    <button
                      className={selected === obj.repo_path ? "active" : ""}
                      onClick={() => selectObject(obj.repo_path)}
                    >
                      {obj.logical_name || obj.repo_path} [{obj.swf_class}]
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </div>
        ))}
      </aside>
      <main className="inspector">
        {!detail ? (
          <div className="empty">Seleccioná un objeto del repositorio</div>
        ) : (
          <>
            <h2>{selected}</h2>
            <p>
              <strong>Clase:</strong> {detail.class} &nbsp;|&nbsp;
              <strong>Parent:</strong> {detail.parent || "(root)"}
            </p>

            <div className="section">
              <h3>Propiedades detectadas</h3>
              <table className="props">
                <tbody>
                  {keys.map((k) => (
                    <tr key={k}>
                      <td>{k}</td>
                      <td>{String(detail.full_properties?.[k] ?? "")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="section">
              <h3>Identificación QTP</h3>
              {(["mandatory", "assistive", "smart"] as const).map((tier) => (
                <div key={tier} className="tier">
                  <label>{tier}</label>
                  {keys.map((k) => (
                    <div key={k} className="tier-row">
                      <input
                        type="checkbox"
                        checked={k in (detail.identification[tier] || {})}
                        onChange={(e) => toggleTier(tier, k, e.target.checked)}
                      />
                      <span>{k}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>

            <div className="section">
              <h3>Captura del elemento</h3>
              {detail.snapshots?.latest?.images?.crop ? (
                <img
                  className="element-shot"
                  src={`/api/assets/${detail.snapshots.latest.images.crop}?v=${encodeURIComponent(
                    detail.snapshots.latest.captured_at || ""
                  )}`}
                  alt={detail.logical_name || selected}
                />
              ) : (
                <p className="muted">
                  Sin captura. Interactuá con el control (find/click) para generarla.
                </p>
              )}
            </div>

            <div className="section">
              <h3>Hints para el agente IA</h3>
              <textarea
                className="hints"
                value={hints}
                onChange={(e) => setHints(e.target.value)}
                placeholder="Ej: usar automation_id num6Button; no usar OCR en esta ventana"
              />
            </div>

            {detail.last_resolution && (
              <div className="section">
                <h3>Última resolución</h3>
                <pre>{JSON.stringify(detail.last_resolution, null, 2)}</pre>
              </div>
            )}

            <div className="actions">
              <button onClick={save}>Guardar cambios</button>
              {status && <span style={{ marginLeft: 12 }}>{status}</span>}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
