const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Workspace = {
  workspace_id: string;
  name: string;
  created_at?: string;
  updated_at?: string;
  sources?: WorkspaceSource[];
};

export type WorkspaceSource = {
  source_id?: string;
  source_type?: string;
  name?: string;
  original_path?: string;
  imported_tables?: string[];
};

export type ProfileColumn = {
  name: string;
  sql_type?: string;
  null_count?: number;
  null_rate?: number;
  distinct_count?: number;
  examples?: unknown[];
  role_candidates?: Record<string, boolean>;
};

export type ProfileTable = {
  table_name: string;
  row_count: number;
  columns: ProfileColumn[];
};

export type WorkspaceProfile = {
  tables?: ProfileTable[];
};

export type SemanticLayer = {
  metrics?: Array<Record<string, unknown>>;
  dimensions?: Array<Record<string, unknown>>;
  entities?: Array<Record<string, unknown>>;
  time_fields?: Array<Record<string, unknown>>;
};

export type RunAnalysisRequest = {
  userQuestion: string;
  initialSql?: string;
};

export type WorkspaceRunResponse = {
  success: boolean;
  workspace_id?: string;
  run_id?: string | null;
  result: Record<string, unknown>;
};

async function parseJsonResponse(response: Response, message: string) {
  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = body.detail ? ` ${body.detail}` : "";
    } catch {
      detail = "";
    }
    throw new Error(`${message}: ${response.status}${detail}`);
  }
  return response.json();
}

export async function createWorkspace(name: string): Promise<Workspace> {
  const response = await fetch(`${API_BASE}/api/workspaces`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return parseJsonResponse(response, "Failed to create workspace");
}

export async function listWorkspaces(): Promise<{ workspaces: Workspace[] }> {
  const response = await fetch(`${API_BASE}/api/workspaces`);
  return parseJsonResponse(response, "Failed to list workspaces");
}

export async function uploadSource(workspaceId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/sources/upload`, {
    method: "POST",
    body: formData,
  });
  return parseJsonResponse(response, "Failed to upload source");
}

export async function importSqliteSource(workspaceId: string, sqlitePath: string) {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/sources/sqlite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sqlite_path: sqlitePath }),
  });
  return parseJsonResponse(response, "Failed to import SQLite source");
}

export async function listSources(workspaceId: string): Promise<{ sources: WorkspaceSource[] }> {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/sources`);
  return parseJsonResponse(response, "Failed to list sources");
}

export async function createProfile(workspaceId: string): Promise<{ success: boolean; profile: WorkspaceProfile }> {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/profile`, {
    method: "POST",
  });
  return parseJsonResponse(response, "Failed to create profile");
}

export async function createSemanticDraft(
  workspaceId: string,
): Promise<{ success: boolean; semantic_layer: SemanticLayer }> {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/semantic-layer/draft`, {
    method: "POST",
  });
  return parseJsonResponse(response, "Failed to create semantic draft");
}

export async function runAnalysis(
  workspaceId: string,
  request: RunAnalysisRequest | string,
): Promise<WorkspaceRunResponse> {
  const payload =
    typeof request === "string"
      ? { user_question: request }
      : {
          user_question: request.userQuestion,
          ...(request.initialSql?.trim() ? { initial_sql: request.initialSql.trim() } : {}),
        };
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(response, "Failed to run analysis");
}
