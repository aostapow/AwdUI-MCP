import { useEffect, useState } from "react";
import {
  AppDetail,
  deleteApp,
  detectAppFramework,
  fetchApp,
  updateApp,
} from "./api";

type Props = {
  appId: string;
  onDeleted: (appId: string) => void;
  onSaved: () => void;
};

const FRAMEWORKS = [
  "unknown",
  "winforms",
  "win32",
  "wpf",
  "uwp",
  "electron",
  "chromium_browser",
  "qt",
  "java_swing",
  "java_fx",
  "gtk",
];

export default function AppPanel({ appId, onDeleted, onSaved }: Props) {
  const [app, setApp] = useState<AppDetail | null>(null);
  const [hints, setHints] = useState("");
  const [framework, setFramework] = useState("unknown");
  const [status, setStatus] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setStatus("");
    setDirty(false);
    fetchApp(appId)
      .then((data) => {
        if (cancelled) return;
        setApp(data);
        setHints(data.agent_hints || "");
        setFramework(data.framework || "unknown");
      })
      .catch((e) => {
        if (!cancelled) setStatus(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [appId]);

  const onDetectFramework = async () => {
    if (!app) return;
    setBusy(true);
    try {
      const result = await detectAppFramework(appId);
      setApp(result.app);
      setFramework(result.app.framework || "unknown");
      setDirty(false);
      const det = result.detection as { framework?: string; unchanged?: boolean; error?: string };
      if (det.unchanged) {
        setStatus(`Framework ya conocido: ${det.framework || framework}`);
      } else {
        setStatus(`Framework detectado: ${det.framework || result.app.framework}`);
      }
      onSaved();
    } catch (e) {
      setStatus(String(e));
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (!app) return;
    setBusy(true);
    try {
      const updated = await updateApp(appId, {
        framework,
        agent_hints: hints,
      });
      setApp(updated);
      setDirty(false);
      setStatus("Guardado");
      onSaved();
    } catch (e) {
      setStatus(String(e));
    } finally {
      setBusy(false);
    }
  };

  const onDeleteApp = async () => {
    if (!app) return;
    const msg =
      `¿Eliminar solo "${app.app_name}" del repositorio?\n\n` +
      `Se borrarán ${app.object_count} objetos y ${app.window_count} ventanas de esta app.\n` +
      `Las demás aplicaciones no se tocan.`;
    if (!window.confirm(msg)) return;
    setBusy(true);
    try {
      await deleteApp(appId);
      setStatus(`"${app.app_name}" eliminada`);
      onDeleted(appId);
    } catch (e) {
      setStatus(String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!app) {
    return <div className="empty">Cargando aplicación…</div>;
  }

  return (
    <>
      <h2>{app.app_name}</h2>
      <p className="muted app-subtitle">Repositorio de aplicación</p>

      <div className="section app-panel">
        <h3>Propiedades</h3>
        <table className="props app-props">
          <tbody>
            <tr>
              <td>app_id</td>
              <td>
                <code>{app.app_id}</code>
              </td>
            </tr>
            <tr>
              <td>app_name</td>
              <td>{app.app_name}</td>
            </tr>
            <tr>
              <td>exe_path</td>
              <td>{app.exe_path || "(vacío)"}</td>
            </tr>
            <tr>
              <td>framework</td>
              <td>
                <select
                  value={framework}
                  onChange={(e) => {
                    setFramework(e.target.value);
                    setDirty(true);
                  }}
                >
                  {FRAMEWORKS.map((fw) => (
                    <option key={fw} value={fw}>
                      {fw}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
            <tr>
              <td>objetos</td>
              <td>{app.object_count}</td>
            </tr>
            <tr>
              <td>ventanas</td>
              <td>{app.window_count}</td>
            </tr>
            <tr>
              <td>creado</td>
              <td>{app.created_at || "—"}</td>
            </tr>
            <tr>
              <td>actualizado</td>
              <td>{app.updated_at || "—"}</td>
            </tr>
          </tbody>
        </table>
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
          placeholder="Ej: app WinForms; priorizar automation_id; la grilla no expone celdas por nombre"
        />
      </div>

      <div className="section app-actions">
        <h3>Acciones</h3>
        <div className="action-row">
          <button type="button" onClick={onDetectFramework} disabled={busy}>
            Detectar framework
          </button>
          <button type="button" onClick={save} disabled={busy || !dirty}>
            Guardar cambios
          </button>
          <button
            type="button"
            className="danger-btn"
            onClick={onDeleteApp}
            disabled={busy}
          >
            Eliminar solo esta aplicación
          </button>
        </div>
        <p className="muted app-delete-hint">
          Solo borra <strong>{app.app_name}</strong>. El resto del repositorio queda intacto.
        </p>
        {status && <p className="status-msg">{status}</p>}
      </div>
    </>
  );
}
