const API = import.meta.env.DEV ? "" : "";

export type AppInfo = {
  app_id: string;
  app_name: string;
  exe_path: string;
  framework: string;
};

export type TreeObject = {
  repo_path: string;
  logical_name: string;
  swf_class: string;
  automation_id: string;
  parent_key: string;
};

export type RepoObject = {
  repo_path: string;
  logical_name?: string;
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

export async function fetchApps(): Promise<AppInfo[]> {
  const data = await get<{ apps: AppInfo[] }>("/api/apps");
  return data.apps;
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
