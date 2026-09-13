const API = import.meta.env.DEV ? "" : "";

export type AppInfo = {
  app_id: string;
  app_name: string;
  exe_path: string;
  framework: string;
  object_count?: number;
};

export type AppDetail = AppInfo & {
  window_count: number;
  agent_hints: string;
  created_at?: string;
  updated_at?: string;
};

export type TreeObject = {
  repo_path: string;
  logical_name: string;
  swf_class: string;
  automation_id: string;
  parent_key: string;
};

export type RepoSearchMeta = {
  matched_in: string;
  snippet: string;
};

export type RepoObject = {
  repo_path: string;
  logical_name?: string;
  automation_id?: string;
  class: string;
  parent: string;
  identification: {
    mandatory: Record<string, string>;
    assistive: Record<string, string>;
    smart: Record<string, string>;
    ordinal: Record<string, string>;
  };
  full_properties?: Record<string, unknown>;
  last_resolution?: Record<string, unknown>;
  snapshots?: { latest?: { images?: Record<string, string>; captured_at?: string } };
  agent_hints?: string;
  _app_name?: string;
  _search?: RepoSearchMeta;
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export type RepoRevision = {
  revision: string;
  app_count: number;
  object_count: number;
};

export async function fetchChanges(): Promise<RepoRevision> {
  return get<RepoRevision>("/api/changes");
}

export async function fetchApps(): Promise<AppInfo[]> {
  const data = await get<{ apps: AppInfo[] }>("/api/apps");
  const normalized = data.apps.map((app) => ({
    ...app,
    object_count: Number(app.object_count ?? 0),
  }));
  const needsBackfill = data.apps.some((app) => app.object_count == null);
  if (!needsBackfill) {
    return normalized;
  }
  return Promise.all(
    normalized.map(async (app) => {
      if (app.object_count > 0) return app;
      try {
        const tree = await fetchTree(app.app_id);
        const n = tree.windows.reduce((sum, w) => sum + w.objects.length, 0);
        return { ...app, object_count: n };
      } catch {
        return app;
      }
    })
  );
}

export async function fetchTree(appId: string) {
  return get<{
    app_id: string;
    app_name: string;
    windows: {
      window_key: string;
      objects: TreeObject[];
    }[];
  }>(`/api/apps/${appId}/tree`);
}

export async function fetchApp(appId: string): Promise<AppDetail> {
  const data = await get<{ app: AppDetail }>(`/api/apps/${encodeURIComponent(appId)}`);
  return data.app;
}

export async function updateApp(
  appId: string,
  payload: {
    app_name?: string;
    exe_path?: string;
    framework?: string;
    agent_hints?: string;
  }
): Promise<AppDetail> {
  const data = await put<{ app: AppDetail }>(
    `/api/apps/${encodeURIComponent(appId)}`,
    payload
  );
  return data.app;
}

export async function detectAppFramework(
  appId: string,
  options?: { force?: boolean; windowTitle?: string }
): Promise<{ app: AppDetail; detection: Record<string, unknown> }> {
  const params = new URLSearchParams();
  if (options?.force) params.set("force", "true");
  if (options?.windowTitle) params.set("window_title", options.windowTitle);
  const qs = params.toString();
  const res = await fetch(
    `${API}/api/apps/${encodeURIComponent(appId)}/detect-framework${qs ? `?${qs}` : ""}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteApp(appId: string, clearAssets = true) {
  const res = await fetch(
    `${API}/api/apps/${encodeURIComponent(appId)}?clear_assets=${clearAssets ? "true" : "false"}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{
    app_id: string;
    app_name: string;
    objects_removed: number;
    windows_removed: number;
    assets_cleared: number;
  }>;
}

export async function resetRepository(clearAssets = true) {
  const res = await fetch(
    `${API}/api/reset?clear_assets=${clearAssets ? "true" : "false"}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{
    objects_removed: number;
    apps_removed: number;
    assets_cleared: number;
  }>;
}

export async function fetchObject(repoPath: string) {
  return get<{ object: RepoObject; agent_hints: string }>(
    `/api/objects?repo_path=${encodeURIComponent(repoPath)}`
  );
}

export async function saveObject(
  repoPath: string,
  payload: {
    logical_name?: string;
    identification?: RepoObject["identification"];
    agent_hints?: string;
    full_properties?: Record<string, unknown>;
  }
) {
  return put<{ object: RepoObject }>(
    `/api/objects/${encodeURIComponent(repoPath)}`,
    payload
  );
}

export async function searchObjects(q: string) {
  return get<{ results: RepoObject[] }>(`/api/search?q=${encodeURIComponent(q)}`);
}

export type ConsolidateResult = {
  moved: number;
  merged: number;
  removed_objects: number;
  removed_windows: number;
  removed_apps: number;
  apps: AppInfo[];
};

export async function consolidateRepos(): Promise<ConsolidateResult> {
  const res = await fetch(`${API}/api/consolidate`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export type FrameworkCatalogData = {
  schema_version: number;
  source_uia_map: string;
  frameworks: {
    id: string;
    label: string;
    uia_support: string;
    hints: string[];
    uses_swf_repo: boolean;
  }[];
  swf_classes: {
    swf_class: string;
    uia_role: string;
    mandatory: string[];
    assistive: string[];
    smart: string[];
    methods: {
      name: string;
      mcp_tools: string[];
      summary: string;
    }[];
  }[];
  uia_controls: {
    role: string;
    patterns_ms: {
      must?: string[];
      conditional?: string[];
      not?: string[];
    };
    read_tools: string[];
    act_bindings: {
      id: string;
      tools: string[];
      patterns: string[];
      steps: string[];
    }[];
    fallback_tools: string[];
  }[];
  repo_method_reference: Record<string, { mcp_tools: string[]; summary: string }>;
  stored?: {
    by_framework: Record<string, Record<string, number>>;
    apps: {
      app_id: string;
      app_name: string;
      framework: string;
      object_count: number;
      by_class: Record<string, number>;
    }[];
  };
};

export async function fetchCatalog(): Promise<FrameworkCatalogData> {
  return get<FrameworkCatalogData>("/api/catalog");
}
