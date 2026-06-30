import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createProfile,
  createWorkspaceReport,
  createSemanticDraft,
  createWorkspace,
  getWorkspaceReport,
  getWorkspaceReportDownloadUrl,
  getWorkspaceSettings,
  importSqliteSource,
  listWorkspaceReports,
  listSources,
  listWorkspaces,
  runAnalysis,
  uploadSource,
} from "../lib/api";

const businessAnswer = {
  headline: "Paid search leads revenue.",
  direct_answer: "Paid search leads revenue.",
  why: "The returned evidence rows show paid search ahead.",
  evidence_bullets: ["paid_search revenue is highest."],
  recommendations: ["Review paid search budget."],
  caveats: [],
  confidence: "medium",
};

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("creates a workspace through FastAPI", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ workspace_id: "ws_1", name: "Demo" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createWorkspace("Demo");

    expect(result.workspace_id).toBe("ws_1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/workspaces",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("lists workspaces from FastAPI", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ workspaces: [{ workspace_id: "ws_1", name: "Finance" }] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await listWorkspaces();

    expect(result.workspaces[0].name).toBe("Finance");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/workspaces");
  });

  it("uploads CSV or Excel files with multipart form data", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, imported_tables: ["orders"] }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["order_id,revenue\n1,100"], "orders.csv", { type: "text/csv" });

    const result = await uploadSource("ws_1", file);

    expect(result.imported_tables).toEqual(["orders"]);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/workspaces/ws_1/sources/upload",
      expect.objectContaining({
        method: "POST",
        body: expect.any(FormData),
      }),
    );
  });

  it("registers SQLite sources and lists imported source metadata", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, imported_tables: ["invoices"] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ sources: [{ source_type: "sqlite", imported_tables: ["invoices"] }] }),
      });
    vi.stubGlobal("fetch", fetchMock);

    await importSqliteSource("ws_1", "/tmp/source.db");
    const sources = await listSources("ws_1");

    expect(sources.sources[0].source_type).toBe("sqlite");
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/api/workspaces/ws_1/sources/sqlite",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sqlite_path: "/tmp/source.db" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2, "http://localhost:8000/api/workspaces/ws_1/sources");
  });

  it("posts profile, semantic draft, and analysis requests", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true, profile: { tables: [] } }) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, semantic_layer: { metrics: [] } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          run_id: "run_1",
          result: { final_answer: "Paid search leads revenue." },
          product_result: {
            version: "p16.v1",
            business_answer: businessAnswer,
          },
        }),
      });
    vi.stubGlobal("fetch", fetchMock);

    await createProfile("ws_1");
    await createSemanticDraft("ws_1");
    const run = await runAnalysis("ws_1", {
      userQuestion: "Which channel has the most revenue?",
      initialSql: "SELECT channel FROM orders",
    });

    expect(run.run_id).toBe("run_1");
    expect(run.product_result?.business_answer?.headline).toBe("Paid search leads revenue.");
    expect(run.result.final_answer).toBe("Paid search leads revenue.");
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://localhost:8000/api/workspaces/ws_1/runs",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_question: "Which channel has the most revenue?",
          initial_sql: "SELECT channel FROM orders",
        }),
      }),
    );
  });

  it("posts clarification continuation requests without requiring the full question", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        run_id: "run_2",
        result: { final_answer: "Products A and B lead revenue." },
        product_result: {
          version: "p16.v1",
          status: "completed",
          question_thread: {
            original_question: "帮我看看销售情况",
            clarification_answer: "按商品，最近 90 天，看 Top 5",
            resolved_question: "分析最近 90 天商品销售额 Top 5。",
            status: "completed",
          },
          business_answer: {
            headline: "商品 A 和 B 收入领先。",
            direct_answer: "商品 A 和 B 在最近 90 天收入领先。",
            why: "后端 product_result 提供了已校验的业务回答。",
            evidence_bullets: ["商品 A 和 B 位于收入 Top 5。"],
            recommendations: [],
            caveats: [],
            confidence: "medium",
          },
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const run = await runAnalysis("ws_1", {
      pendingRunId: "pending_1",
      clarificationAnswer: "按商品，最近 90 天，看 Top 5",
    });

    expect(run.product_result?.question_thread?.resolved_question).toContain("最近 90 天");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/workspaces/ws_1/runs",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pending_run_id: "pending_1",
          clarification_answer: "按商品，最近 90 天，看 Top 5",
        }),
      }),
    );
  });

  it("loads workspace settings from FastAPI", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        workspace_id: "ws_1",
        data_sources: { sources: [{ name: "orders.csv", imported_tables: ["orders"] }] },
        profile: { status: "ready", tables: [] },
        semantic_layer: { status: "ready", metrics: [], dimensions: [] },
        model_mode: { product_live_mode: true, provider_features: { insight_drafting: true } },
        safety: {
          sql_review: "enabled",
          sensitive_field_blocking: "enabled",
          trace_available: "enabled",
          technical_details_policy: "collapsed_by_default",
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const settings = await getWorkspaceSettings("ws_1");

    expect(settings.workspace_id).toBe("ws_1");
    expect(settings.safety.sql_review).toBe("enabled");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/workspaces/ws_1/settings");
  });

  it("creates, lists, loads, and links workspace reports", async () => {
    const report = {
      report_id: "report_1",
      workspace_id: "ws_1",
      report_type: "business_review",
      report_goal: "Create a revenue review.",
      title: "Business Review",
      status: "completed",
      executive_summary: ["Revenue grew."],
      sections: [],
      markdown_path: "workspaces/ws_1/reports/report_1/report.md",
      json_path: "workspaces/ws_1/reports/report_1/report.json",
      trace_path: "workspaces/ws_1/reports/report_1/trace.json",
      artifact_dir: "workspaces/ws_1/reports/report_1/artifacts",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, workspace_id: "ws_1", report_id: "report_1", report }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ workspace_id: "ws_1", reports: [report] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ workspace_id: "ws_1", report_id: "report_1", report }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const created = await createWorkspaceReport("ws_1", {
      reportType: "business_review",
      reportGoal: "Create a revenue review.",
    });
    const reports = await listWorkspaceReports("ws_1");
    const detail = await getWorkspaceReport("ws_1", "report_1");

    expect(created.report_id).toBe("report_1");
    expect(reports.reports[0].title).toBe("Business Review");
    expect(detail.report.executive_summary).toEqual(["Revenue grew."]);
    expect(getWorkspaceReportDownloadUrl("ws_1", "report_1")).toBe(
      "http://localhost:8000/api/workspaces/ws_1/reports/report_1/download",
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/api/workspaces/ws_1/reports",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report_type: "business_review",
          report_goal: "Create a revenue review.",
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2, "http://localhost:8000/api/workspaces/ws_1/reports");
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://localhost:8000/api/workspaces/ws_1/reports/report_1",
    );
  });
});
