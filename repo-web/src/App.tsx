import { useCallback, useEffect, useRef, useState } from "react";
import {
  AppInfo,
  RepoObject,
  fetchApps,
  fetchChanges,
  fetchObject,
  fetchTree,
  saveObject,
  searchObjects,
  consolidateRepos,
} from "./api";

const POLL_MS = 2500;

const JUNK_APPS = new Set([
  "foreground",
  "unknown",
  "smoke",
  "applicationframehost.exe",
]);

function isJunkApp(name: string): boolean {
  const lower = name.toLowerCase();
  return JUNK_APPS.has(lower) || lower.endsWith("applicationframehost.exe");
}

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
  const [expandedWindows, setExpandedWindows] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<string>("");
  const [detail, setDetail] = useState<RepoObject | null>(null);
  const [hints, setHints] = useState("");
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<RepoObject[]>([]);
  const [status, setStatus] = useState("");
  const [dirty, setDirty] = useState(false);
  const [live, setLive] = useState(false);
  const revisionRef = useRef<string | null>(null);
  const treesRef = useRef(trees);
  const selectedRef = useRef(selected);
  const dirtyRef = useRef(dirty);
  treesRef.current = trees;
  selectedRef.current = selected;
  dirtyRef.current = dirty;

  const loadApps = useCallback(async () => {
    const list = await fetchApps();
    setApps(list);
  }, []);

  const refreshOpenTrees = useCallback(async () => {
    const openIds = Object.keys(treesRef.current);
    if (openIds.length === 0) return;
    const updated: Record<string, TreeData> = {};
    await Promise.all(
      openIds.map(async (appId) => {
        updated[appId] = await fetchTree(appId);
      })
    );
    setTrees((prev) => ({ ...prev, ...updated }));
  }, []);

  const refreshSelected = useCallback(async () => {
    const path = selectedRef.current;
    if (!path || dirtyRef.current) return;
    const data = await fetchObject(path);
    setDetail(data.object);
    setHints(data.agent_hints || "");
  }, []);

  const pollChanges = useCallback(async () => {
    const { revision } = await fetchChanges();
    if (revisionRef.current === null) {
      revisionRef.current = revision;
      return;
    }
    if (revision === revisionRef.current) return;
    revisionRef.current = revision;
    await loadApps();
    await refreshOpenTrees();
    await refreshSelected();
    setLive(true);
    window.setTimeout(() => setLive(false), 1200);
  }, [loadApps, refreshOpenTrees, refreshSelected]);

  useEffect(() => {
    loadApps().catch((e) => setStatus(String(e)));
  }, [loadApps]);

  useEffect(() => {
    let cancelled = false;
    const tick = () => {
      if (!cancelled) {
        pollChanges().catch(() => {});
      }
    };
    const id = window.setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [pollChanges]);

  const toggleApp = async (appId: string) => {
    if (trees[appId]) {
      setTrees((t) => {
        const next = { ...t };
        delete next[appId];
        return next;
      });
      return;
    }
    const tree = await fetchTree(appId);
    setTrees((t) => ({ ...t, [appId]: tree }));
    setExpandedWindows((prev) => {
      const next = new Set(prev);
      for (const win of tree.windows) {
        next.add(`${appId}::${win.window_key}`);
      }
      return next;
    });
  };

  const toggleWindow = (appId: string, windowKey: string) => {
    const key = `${appId}::${windowKey}`;
    setExpandedWindows((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const selectObject = async (repoPath: string) => {
    setSelected(repoPath);
    setDirty(false);
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
    setDirty(true);
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
    setDirty(false);
    await loadApps();
    revisionRef.current = (await fetchChanges()).revision;
  };

  const onConsolidate = async () => {
    setStatus("Organizando...");
    try {
      const result = await consolidateRepos();
      setApps(result.apps);
      setTrees({});
      setExpandedWindows(new Set());
      setSelected("");
      setDetail(null);
      revisionRef.current = (await fetchChanges()).revision;
      setStatus(
        `Listo: ${result.moved} movidos, ${result.merged} fusionados, ` +
          `${result.removed_apps} apps eliminadas`
      );
    } catch (e) {
      setStatus(String(e));
    }
  };

  const keys = tierKeys(detail);
  const hasJunkApps = apps.some((app) => isJunkApp(app.app_name));

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>
          AwdUI Repo Studio
          <span className={`live-dot${live ? " live-dot--on" : ""}`} title="Actualización automática cada 2.5s" />
        </h1>
        {hasJunkApps && (
          <div className="sidebar-actions">
            <button
              type="button"
              className="consolidate-btn"
              onClick={onConsolidate}
              title="Une apps duplicadas (foreground, ApplicationFrameHost) y borra ventanas vacías"
            >
              Organizar repositorio
            </button>
          </div>
        )}
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
        {apps.map((app) => {
          const appOpen = Boolean(trees[app.app_id]);
          const junk = isJunkApp(app.app_name);
          const treeCount =
            trees[app.app_id]?.windows.reduce((n, w) => n + w.objects.length, 0) ?? 0;
          const count = treeCount > 0 ? treeCount : Number(app.object_count ?? 0);
          if (junk && count === 0) return null;
          return (
            <div key={app.app_id} className={`tree-app${junk ? " tree-app--junk" : ""}`}>
              <button
                type="button"
                className={`tree-toggle${appOpen ? " tree-toggle--open" : ""}`}
                onClick={() => toggleApp(app.app_id)}
                aria-expanded={appOpen}
                title={junk ? "App legacy — usá Organizar repositorio" : undefined}
              >
                <span className="tree-chevron" aria-hidden>
                  {appOpen ? "▼" : "▶"}
                </span>
                {app.app_name}
                <span className="tree-count">({count})</span>
              </button>
              {appOpen &&
                trees[app.app_id]?.windows.map((win) => {
                  const winKey = `${app.app_id}::${win.window_key}`;
                  const winOpen = expandedWindows.has(winKey);
                  return (
                    <div key={win.window_key} className="tree-window">
                      <button
                        type="button"
                        className={`tree-toggle tree-toggle--window${winOpen ? " tree-toggle--open" : ""}`}
                        onClick={() => toggleWindow(app.app_id, win.window_key)}
                        aria-expanded={winOpen}
                      >
                        <span className="tree-chevron" aria-hidden>
                          {winOpen ? "▼" : "▶"}
                        </span>
                        {win.window_key}
                        <span className="tree-count">({win.objects.length})</span>
                      </button>
                      {winOpen &&
                        win.objects.map((obj) => (
                          <div key={obj.repo_path} className="tree-object">
                            <button
                              type="button"
                              className={selected === obj.repo_path ? "active" : ""}
                              onClick={() => selectObject(obj.repo_path)}
                            >
                              {obj.logical_name || obj.repo_path} [{obj.swf_class}]
                            </button>
                          </div>
                        ))}
                    </div>
                  );
                })}
            </div>
          );
        })}
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
                onChange={(e) => {
                  setHints(e.target.value);
                  setDirty(true);
                }}
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
