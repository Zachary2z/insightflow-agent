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

export type WorkspaceSettings = {
  workspace_id: string;
  workspace_name?: string;
  data_sources: {
    status?: string;
    sources?: WorkspaceSource[];
    source_count?: number;
    imported_table_count?: number;
  };
  profile: WorkspaceProfile & {
    status?: string;
    table_count?: number;
    column_count?: number;
    row_count?: number;
  };
  semantic_layer: SemanticLayer & {
    status?: string;
  };
  model_mode: {
    product_live_mode?: boolean;
    status_label?: string;
    provider?: {
      name?: string;
      model?: string;
      api_key_present?: boolean;
    };
    provider_features?: Record<string, boolean>;
    coverage?: {
      enabled?: number;
      total?: number;
    };
  };
  safety: {
    sql_review: "enabled" | "disabled" | string;
    sensitive_field_blocking: "enabled" | "disabled" | string;
    trace_available: "enabled" | "disabled" | string;
    technical_details_policy: "collapsed_by_default" | string;
  };
};

export type RunAnalysisRequest = {
  userQuestion?: string;
  initialSql?: string;
  pendingRunId?: string;
  clarificationAnswer?: string;
};

export type QuestionThread = {
  original_question?: string;
  system_understanding?: string;
  clarification_question?: string;
  clarification_answer?: string;
  resolved_question?: string;
  pending_run_id?: string;
  status?: string;
};

export type BusinessAnswer = {
  headline?: string;
  summary?: string;
  recommendations?: string[];
  next_actions?: string[];
  caveats?: string[];
  confidence?: string;
  source?: string;
  quality_flags?: string[];
};

export type EvidenceSummary = {
  table_preview?: {
    columns?: string[];
    rows?: Array<unknown[] | Record<string, unknown>>;
  };
  evidence_notes?: string[];
  validation_status?: string;
};

export type ChartArtifact = {
  title?: string;
  path?: string;
  url?: string;
  rendering_status?: string;
  unit?: string;
  business_annotation?: string;
};

export type TechnicalDetails = {
  sql?: string;
  raw_rows?: Array<unknown[] | Record<string, unknown>>;
  trace_path?: string;
  provider_metadata?: Record<string, unknown>;
  validation_logs?: Array<Record<string, unknown>>;
  debug?: Record<string, unknown>;
};

export type ProductAnalysisResult = {
  version: "p13.v1" | string;
  workspace_id?: string;
  run_id?: string | null;
  status?: string;
  question_thread?: QuestionThread;
  business_answer?: BusinessAnswer;
  evidence?: EvidenceSummary;
  chart_artifacts?: ChartArtifact[];
  report?: Record<string, unknown> | null;
  technical_details?: TechnicalDetails;
};

export type WorkspaceRunResponse = {
  success: boolean;
  workspace_id?: string;
  run_id?: string | null;
  result: Record<string, unknown>;
  product_result?: ProductAnalysisResult | null;
};

export type ReportType = "business_review" | "channel_performance" | "revenue_trend";

export type WorkspaceReportSection = {
  section_id: string;
  title: string;
  purpose?: string;
  status: string;
  question?: string;
  summary?: string;
  sql?: string;
  columns?: string[];
  rows_preview?: Array<Record<string, unknown>>;
  artifact_paths?: string[];
  evidence_notes?: string[];
  business_artifacts?: Array<Record<string, unknown>>;
  technical_details?: {
    internal_question?: string;
    purpose?: string;
    sql?: string;
    columns?: string[];
    rows_preview?: Array<Record<string, unknown>>;
    provider_metadata?: Record<string, unknown>;
    trace_nodes?: string[];
    trace_path?: string;
    workspace_run_dir?: string;
    error?: string | null;
  };
  provider_metadata?: Record<string, unknown>;
  trace_nodes?: string[];
  error?: string | null;
};

export type WorkspaceReport = {
  report_id: string;
  workspace_id: string;
  report_type: ReportType | string;
  report_goal: string;
  title: string;
  status: string;
  executive_summary?: string[];
  sections?: WorkspaceReportSection[];
  markdown_path?: string;
  json_path?: string;
  trace_path?: string;
  artifact_dir?: string;
  created_at?: string;
  updated_at?: string;
  provider_metadata?: Record<string, unknown>;
};

export type CreateWorkspaceReportRequest = {
  reportType: ReportType;
  reportGoal: string;
};

export type WorkspaceReportCreateResponse = {
  success: boolean;
  workspace_id: string;
  report_id: string;
  report: WorkspaceReport;
};

export type WorkspaceReportsResponse = {
  workspace_id: string;
  reports: WorkspaceReport[];
};

export type WorkspaceReportResponse = {
  workspace_id: string;
  report_id: string;
  report: WorkspaceReport;
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

export async function getWorkspaceSettings(workspaceId: string): Promise<WorkspaceSettings> {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/settings`);
  return parseJsonResponse(response, "Failed to load workspace settings");
}

export async function runAnalysis(
  workspaceId: string,
  request: RunAnalysisRequest | string,
): Promise<WorkspaceRunResponse> {
  const payload =
    typeof request === "string"
      ? { user_question: request }
      : request.pendingRunId
        ? {
            pending_run_id: request.pendingRunId,
            clarification_answer: request.clarificationAnswer ?? "",
          }
      : {
          user_question: request.userQuestion ?? "",
          ...(request.initialSql?.trim() ? { initial_sql: request.initialSql.trim() } : {}),
        };
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(response, "Failed to run analysis");
}

export async function createWorkspaceReport(
  workspaceId: string,
  request: CreateWorkspaceReportRequest,
): Promise<WorkspaceReportCreateResponse> {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/reports`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      report_type: request.reportType,
      report_goal: request.reportGoal,
    }),
  });
  return parseJsonResponse(response, "Failed to create report");
}

export async function listWorkspaceReports(workspaceId: string): Promise<WorkspaceReportsResponse> {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/reports`);
  return parseJsonResponse(response, "Failed to list reports");
}

export async function getWorkspaceReport(
  workspaceId: string,
  reportId: string,
): Promise<WorkspaceReportResponse> {
  const response = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/reports/${reportId}`);
  return parseJsonResponse(response, "Failed to load report");
}

export function getWorkspaceReportDownloadUrl(workspaceId: string, reportId: string): string {
  return `${API_BASE}/api/workspaces/${workspaceId}/reports/${reportId}/download`;
}
