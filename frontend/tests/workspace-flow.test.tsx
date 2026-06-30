import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AnalysisRunner from "../components/AnalysisRunner";
import BusinessQAPreview from "../components/BusinessQAPreview";
import BusinessAnswerCard from "../components/BusinessAnswerCard";
import ChartArtifactGallery from "../components/ChartArtifactGallery";
import DataSettings from "../components/DataSettings";
import DatasetManager from "../components/DatasetManager";
import ProfileSummary from "../components/ProfileSummary";
import ProfileWorkspace from "../components/ProfileWorkspace";
import ReportGenerator from "../components/ReportGenerator";
import ReportList from "../components/ReportList";
import ReportSection from "../components/ReportSection";
import ReportViewer from "../components/ReportViewer";
import RunResult from "../components/RunResult";
import SemanticLayerWorkspace from "../components/SemanticLayerWorkspace";
import WorkspaceList from "../components/WorkspaceList";
import WorkspaceNewForm from "../components/WorkspaceNewForm";
import BusinessQAPage from "../app/workspaces/[workspaceId]/business-qa/page";
import DatasetsPage from "../app/workspaces/[workspaceId]/datasets/page";
import NewWorkspacePage from "../app/workspaces/new/page";
import ProfilePage from "../app/workspaces/[workspaceId]/profile/page";
import ReportDetailPage from "../app/workspaces/[workspaceId]/reports/[reportId]/page";
import ReportsPage from "../app/workspaces/[workspaceId]/reports/page";
import RunDetailPage from "../app/workspaces/[workspaceId]/runs/[runId]/page";
import SemanticLayerPage from "../app/workspaces/[workspaceId]/semantic-layer/page";
import SettingsPage from "../app/workspaces/[workspaceId]/settings/page";
import WorkspacesPage from "../app/workspaces/page";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("../lib/api", () => ({
  createProfile: vi.fn(),
  createWorkspaceReport: vi.fn(),
  createSemanticDraft: vi.fn(),
  createWorkspace: vi.fn(),
  getWorkspaceReport: vi.fn(),
  getWorkspaceArtifactUrl: (workspaceId: string, relativePath: string) =>
    `http://localhost:8000/api/workspaces/${workspaceId}/artifacts/${relativePath}`,
  getWorkspaceReportDownloadUrl: vi.fn(),
  getWorkspaceRun: vi.fn(),
  getWorkspaceSettings: vi.fn(),
  importSqliteSource: vi.fn(),
  listWorkspaceReports: vi.fn(),
  listWorkspaceRuns: vi.fn(),
  listSources: vi.fn(),
  listWorkspaces: vi.fn(),
  resolveApiUrl: (url: string) => (url.startsWith("/api/") ? `http://localhost:8000${url}` : url),
  runAnalysis: vi.fn(),
  uploadSource: vi.fn(),
}));

import {
  createProfile,
  createWorkspaceReport,
  createSemanticDraft,
  createWorkspace,
  getWorkspaceReport,
  getWorkspaceReportDownloadUrl,
  getWorkspaceRun,
  getWorkspaceSettings,
  importSqliteSource,
  listWorkspaceReports,
  listWorkspaceRuns,
  listSources,
  listWorkspaces,
  runAnalysis,
  uploadSource,
} from "../lib/api";

describe("workspace product components", () => {
  afterEach(() => {
    vi.clearAllMocks();
    pushMock.mockReset();
    window.sessionStorage.clear();
    cleanup();
  });

  it("loads and renders real workspaces", async () => {
    vi.mocked(listWorkspaces).mockResolvedValue({
      workspaces: [{ workspace_id: "ws_1", name: "Finance Workspace", updated_at: "2026-06-23T00:00:00Z" }],
    });

    render(<WorkspaceList />);

    expect(screen.getByText("正在加载工作区")).toBeTruthy();
    expect(await screen.findByText("Finance Workspace")).toBeTruthy();
    expect(screen.getByRole("link", { name: "打开数据源管理" }).getAttribute("href")).toBe(
      "/workspaces/ws_1/datasets",
    );
  });

  it("renders the workspace list route as a Chinese product entry page", async () => {
    vi.mocked(listWorkspaces).mockResolvedValue({
      workspaces: [{ workspace_id: "ws_1", name: "Finance Workspace", updated_at: "2026-06-23T00:00:00Z" }],
    });

    render(<WorkspacesPage />);

    expect(screen.getByRole("heading", { level: 1, name: "选择工作区" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "新建工作区" }).getAttribute("href")).toBe("/workspaces/new");
    expect(await screen.findByText("Finance Workspace")).toBeTruthy();
  });

  it("creates a workspace and reports the datasets destination", async () => {
    const onCreated = vi.fn();
    vi.mocked(createWorkspace).mockResolvedValue({ workspace_id: "ws_2", name: "Ops" });

    render(<WorkspaceNewForm onCreated={onCreated} />);
    fireEvent.change(screen.getByLabelText("工作区名称"), { target: { value: "Ops" } });
    fireEvent.click(screen.getByRole("button", { name: "创建工作区" }));

    await waitFor(() => expect(createWorkspace).toHaveBeenCalledWith("Ops"));
    expect(onCreated).toHaveBeenCalledWith({ workspace_id: "ws_2", name: "Ops" });
    expect(await screen.findByText(/已创建工作区/)).toBeTruthy();
  });

  it("renders the new workspace route as a Chinese product entry page", () => {
    render(<NewWorkspacePage />);

    expect(screen.getByRole("heading", { level: 1, name: "新建工作区" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "返回工作区" }).getAttribute("href")).toBe("/workspaces");
    expect(screen.getByText("工作区信息")).toBeTruthy();
  });

  it("renders the data source management page route with active product navigation", async () => {
    vi.mocked(listSources).mockResolvedValue({ sources: [] });

    render(await DatasetsPage({ params: Promise.resolve({ workspaceId: "ws_1" }) }));

    expect(screen.getByRole("heading", { level: 1, name: "数据源管理" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /数据源管理/ }).getAttribute("aria-current")).toBe("page");
    expect(await screen.findByText("还没有导入数据源")).toBeTruthy();
  });

  it("uploads multiple files, imports SQLite, and renders source management actions in one responsive grid", async () => {
    vi.mocked(listSources)
      .mockResolvedValueOnce({
        sources: [
          { source_id: "src_1", source_type: "csv", name: "orders.csv", imported_tables: ["orders"] },
          { source_id: "src_2", source_type: "csv", name: "customers.csv", imported_tables: ["customers"] },
          {
            source_id: "src_3",
            source_type: "csv",
            name: "marketing_spend.csv",
            imported_tables: ["marketing_spend"],
          },
        ],
      })
      .mockResolvedValueOnce({
        sources: [
          { source_id: "src_1", source_type: "csv", name: "orders.csv", imported_tables: ["orders"] },
          { source_id: "src_2", source_type: "csv", name: "customers.csv", imported_tables: ["customers"] },
          {
            source_id: "src_3",
            source_type: "csv",
            name: "marketing_spend.csv",
            imported_tables: ["marketing_spend"],
          },
          { source_id: "src_4", source_type: "csv", name: "returns.csv", imported_tables: ["returns"] },
        ],
      })
      .mockResolvedValueOnce({
        sources: [
          { source_id: "src_1", source_type: "csv", name: "orders.csv", imported_tables: ["orders"] },
          { source_id: "src_2", source_type: "csv", name: "customers.csv", imported_tables: ["customers"] },
          {
            source_id: "src_3",
            source_type: "csv",
            name: "marketing_spend.csv",
            imported_tables: ["marketing_spend"],
          },
          { source_id: "src_4", source_type: "csv", name: "returns.csv", imported_tables: ["returns"] },
          { source_id: "src_5", source_type: "sqlite", name: "ops.db", imported_tables: ["invoices"] },
        ],
      });
    vi.mocked(uploadSource)
      .mockResolvedValueOnce({ success: true, imported_tables: ["returns"] })
      .mockResolvedValueOnce({ success: true, imported_tables: ["refunds"] });
    vi.mocked(importSqliteSource).mockResolvedValue({ success: true, imported_tables: ["invoices"] });

    render(<DatasetManager workspaceId="ws_1" />);

    expect(await screen.findByText("已导入数据源")).toBeTruthy();
    expect(screen.getByText("上传 CSV / Excel")).toBeTruthy();
    expect(screen.getByText("导入 SQLite")).toBeTruthy();
    expect(screen.getByText("数据准备状态")).toBeTruthy();
    const actionRegion = screen.getByRole("region", { name: "数据源操作区" });
    expect(actionRegion.querySelector(".dataset-side-column")).toBeNull();
    expect(actionRegion.contains(screen.getByText("数据准备状态"))).toBe(true);
    expect(actionRegion.contains(screen.getByRole("heading", { name: "下一步" }))).toBe(true);
    expect(screen.getByText("orders.csv")).toBeTruthy();
    expect(screen.getByText("customers.csv")).toBeTruthy();
    expect(screen.getByText("marketing_spend.csv")).toBeTruthy();
    expect(screen.getAllByText("已导入").length).toBeGreaterThanOrEqual(3);

    const file = new File(["return_id,amount\n1,20"], "returns.csv", { type: "text/csv" });
    const secondFile = new File(["refund_id,amount\n1,8"], "refunds.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText("选择 CSV 或 Excel 文件"), { target: { files: [file, secondFile] } });
    fireEvent.click(screen.getByRole("button", { name: "上传 CSV / Excel" }));

    expect(await screen.findByText("returns.csv")).toBeTruthy();
    expect(uploadSource).toHaveBeenCalledWith("ws_1", file);
    expect(uploadSource).toHaveBeenCalledWith("ws_1", secondFile);
    expect(uploadSource).toHaveBeenCalledTimes(2);
    fireEvent.change(screen.getByLabelText("SQLite 文件路径"), { target: { value: "/tmp/ops.db" } });
    fireEvent.click(screen.getByRole("button", { name: "导入 SQLite" }));

    expect(importSqliteSource).toHaveBeenCalledWith("ws_1", "/tmp/ops.db");
    expect(await screen.findByText("ops.db")).toBeTruthy();
    expect(screen.getByText("invoices")).toBeTruthy();
  });

  it("generates and renders profile results from the API", async () => {
    vi.mocked(createProfile).mockResolvedValue({
      success: true,
      profile: {
        tables: [{ table_name: "orders", row_count: 2, columns: [{ name: "revenue", role_candidates: { measure: true } }] }],
      },
    });

    render(<ProfileWorkspace workspaceId="ws_1" />);
    fireEvent.click(screen.getByRole("button", { name: "生成字段画像" }));

    expect(await screen.findByText("orders")).toBeTruthy();
    expect(screen.getByText("字段画像结果")).toBeTruthy();
    expect(screen.getByText("2 行")).toBeTruthy();
    expect(screen.getByText(/指标/)).toBeTruthy();
    expect(createProfile).toHaveBeenCalledWith("ws_1");
  });

  it("renders the profile route inside the product shell with Chinese copy", async () => {
    render(await ProfilePage({ params: Promise.resolve({ workspaceId: "ws_1" }) }));

    expect(screen.getByRole("heading", { level: 1, name: "字段画像" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /数据源管理/ }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("button", { name: "生成字段画像" })).toBeTruthy();
  });

  it("generates and renders semantic layer drafts", async () => {
    vi.mocked(createSemanticDraft).mockResolvedValue({
      success: true,
      semantic_layer: {
        metrics: [{ name: "sum_revenue", formula: "SUM(orders.revenue)" }],
        dimensions: [{ name: "channel", field: "orders.channel" }],
        entities: [{ name: "customer", key: "orders.customer_id" }],
      },
    });

    render(<SemanticLayerWorkspace workspaceId="ws_1" />);
    fireEvent.click(screen.getByRole("button", { name: "生成语义层草稿" }));

    expect(await screen.findByText("sum_revenue")).toBeTruthy();
    expect(screen.getByText("语义层草稿结果")).toBeTruthy();
    expect(screen.getByText("指标")).toBeTruthy();
    expect(screen.getByText("维度")).toBeTruthy();
    expect(screen.getByText(/orders.channel/)).toBeTruthy();
    expect(screen.getByText("customer")).toBeTruthy();
  });

  it("renders the semantic-layer route inside the product shell with Chinese copy", async () => {
    render(await SemanticLayerPage({ params: Promise.resolve({ workspaceId: "ws_1" }) }));

    expect(screen.getByRole("heading", { level: 1, name: "语义层草稿" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /数据源管理/ }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("button", { name: "生成语义层草稿" })).toBeTruthy();
  });

  it("renders data settings as a Chinese readiness product page with collapsed technical details", async () => {
    vi.mocked(getWorkspaceSettings).mockResolvedValue({
      workspace_id: "ws_1",
      data_sources: {
        status: "ready",
        source_count: 1,
        imported_table_count: 1,
        sources: [{ name: "orders.csv", source_type: "csv", imported_tables: ["orders"] }],
      },
      profile: {
        status: "ready",
        table_count: 1,
        column_count: 2,
        row_count: 10,
        tables: [
          {
            table_name: "orders",
            row_count: 10,
            columns: [
              { name: "revenue", role_candidates: { measure: true } },
              { name: "channel", role_candidates: { dimension: true } },
            ],
          },
        ],
      },
      semantic_layer: {
        status: "ready",
        metrics: [{ name: "sum_revenue" }],
        dimensions: [{ name: "channel" }],
        entities: [],
        time_fields: [],
      },
      model_mode: {
        product_live_mode: true,
        status_label: "真实模型模式已开启",
        provider: { name: "DeepSeek", model: "deepseek-chat", api_key_present: true },
        provider_features: {
          question_understanding: true,
          clarification: true,
          sql_planning: true,
          report_writer: true,
        },
      },
      safety: {
        sql_review: "enabled",
        sensitive_field_blocking: "enabled",
        trace_available: "enabled",
        technical_details_policy: "collapsed_by_default",
      },
    });

    render(<DataSettings workspaceId="ws_1" />);

    expect(await screen.findByText("数据准备总览")).toBeTruthy();
    expect(screen.getByText("数据源")).toBeTruthy();
    expect(screen.getByText("字段画像")).toBeTruthy();
    expect(screen.getByText("语义层")).toBeTruthy();
    expect(screen.getByText("真实模型模式")).toBeTruthy();
    expect(screen.getByText("安全与审计")).toBeTruthy();
    expect(screen.getAllByText("已准备").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText("orders.csv")).toBeTruthy();
    expect(screen.getByText("orders")).toBeTruthy();
    expect(screen.getAllByText("10 行").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("1 张表")).toBeTruthy();
    expect(screen.getByText("2 个字段")).toBeTruthy();
    expect(screen.getAllByText(/revenue/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("指标")).toBeTruthy();
    expect(screen.getByText("维度")).toBeTruthy();
    expect(screen.getByText("sum_revenue")).toBeTruthy();
    expect(screen.getAllByText("channel").length).toBeGreaterThan(0);
    expect(screen.getAllByText("真实模型已参与").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("DeepSeek / deepseek-chat")).toBeTruthy();
    expect(screen.getByText("问题理解")).toBeTruthy();
    expect(screen.getByText("追问判断")).toBeTruthy();
    expect(screen.getByText("SQL 规划")).toBeTruthy();
    expect(screen.getByText("报告写作")).toBeTruthy();
    expect(screen.getByText("SQL 审核不可绕过")).toBeTruthy();
    expect(screen.getByText("敏感字段拦截已开启")).toBeTruthy();
    expect(screen.getByText("Trace 可审计")).toBeTruthy();
    expect(screen.getByText("技术详情默认折叠")).toBeTruthy();

    const disclosure = screen.getByText("技术详情").closest("details");
    expect(disclosure?.hasAttribute("open")).toBe(false);
    expect(screen.queryByText(/provider metadata/)).toBeNull();
    expect(screen.queryByText(/raw config/)).toBeNull();

    fireEvent.click(screen.getByText("技术详情"));

    expect(screen.getByText(/provider metadata/)).toBeTruthy();
    expect(screen.getByText(/raw config/)).toBeTruthy();
  });

  it("shows Chinese empty states for settings that are not ready yet", async () => {
    vi.mocked(getWorkspaceSettings).mockResolvedValue({
      workspace_id: "ws_1",
      data_sources: { status: "empty", sources: [], source_count: 0, imported_table_count: 0 },
      profile: { status: "missing", tables: [], table_count: 0, column_count: 0, row_count: 0 },
      semantic_layer: { status: "missing", metrics: [], dimensions: [], entities: [], time_fields: [] },
      model_mode: {
        product_live_mode: false,
        status_label: "真实模型模式未开启",
        provider_features: {},
      },
      safety: {
        sql_review: "enabled",
        sensitive_field_blocking: "enabled",
        trace_available: "enabled",
        technical_details_policy: "collapsed_by_default",
      },
    });

    render(<DataSettings workspaceId="ws_1" />);

    expect(await screen.findByText("暂无数据源")).toBeTruthy();
    expect(screen.getByText("先回到数据源管理导入 CSV、Excel 或 SQLite。")).toBeTruthy();
    expect(screen.getAllByText("未生成").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("暂无数据").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("真实模型未开启").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/暂无真实模型能力参与/)).toBeTruthy();
  });

  it("renders the settings page route", async () => {
    vi.mocked(getWorkspaceSettings).mockResolvedValue({
      workspace_id: "ws_1",
      data_sources: { status: "empty", sources: [] },
      profile: { status: "missing", tables: [] },
      semantic_layer: { status: "missing", metrics: [], dimensions: [], entities: [], time_fields: [] },
      model_mode: {
        product_live_mode: false,
        status_label: "真实模型模式未开启",
        provider_features: {},
      },
      safety: {
        sql_review: "enabled",
        sensitive_field_blocking: "enabled",
        trace_available: "enabled",
        technical_details_policy: "collapsed_by_default",
      },
    });

    render(await SettingsPage({ params: Promise.resolve({ workspaceId: "ws_1" }) }));

    expect(screen.getByRole("heading", { level: 1, name: "数据设置" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /数据设置/ }).getAttribute("aria-current")).toBe("page");
    expect(await screen.findByText("数据准备总览")).toBeTruthy();
    expect(screen.getByText("暂无数据源")).toBeTruthy();
  });

  it("loads analysis history on mount and renders completed failed and clarification runs", async () => {
    vi.mocked(listWorkspaceRuns).mockResolvedValue({
      workspace_id: "ws_1",
      runs: [
        {
          run_id: "run_done",
          status: "completed",
          question: "哪个渠道收入最高？",
          headline: "email 渠道收入最高。",
          saved_at: "2026-06-29T12:00:00Z",
          has_chart: true,
          requires_clarification: false,
          failure_reason: "",
        },
        {
          run_id: "run_failed",
          status: "failed",
          question: "分析不存在字段",
          headline: "",
          saved_at: "2026-06-29T11:00:00Z",
          has_chart: false,
          requires_clarification: false,
          failure_reason: "系统尝试使用当前工作区中不存在的表或字段，因此没有执行查询。",
        },
        {
          run_id: "run_waiting",
          status: "waiting_for_clarification",
          question: "帮我看看销售情况",
          headline: "需要补充时间范围",
          saved_at: "2026-06-29T10:00:00Z",
          has_chart: false,
          requires_clarification: true,
          failure_reason: "",
        },
      ],
    });

    render(<AnalysisRunner workspaceId="ws_1" />);

    await waitFor(() => expect(listWorkspaceRuns).toHaveBeenCalledWith("ws_1"));
    expect(await screen.findByText("历史分析")).toBeTruthy();
    expect(screen.getByText("哪个渠道收入最高？")).toBeTruthy();
    expect(screen.getByText(/email 渠道收入最高/)).toBeTruthy();
    expect(screen.queryByText(/Email produced the most revenue/)).toBeNull();
    expect(screen.getByText("分析不存在字段")).toBeTruthy();
    expect(screen.getByText(/系统尝试使用当前工作区中不存在的表或字段/)).toBeTruthy();
    expect(screen.getByText("帮我看看销售情况")).toBeTruthy();
    expect(screen.getByText(/需要补充时间范围/)).toBeTruthy();
    expect(screen.getByText("有图表")).toBeTruthy();
    expect(screen.getAllByText("已完成").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("失败").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("等待补充").length).toBeGreaterThanOrEqual(1);
  });

  it("restores a selected history run into the analysis result", async () => {
    vi.mocked(listWorkspaceRuns).mockResolvedValue({
      workspace_id: "ws_1",
      runs: [
        {
          run_id: "run_history",
          status: "completed",
          question: "恢复历史问题",
          headline: "历史业务结论",
          saved_at: "2026-06-29T12:00:00Z",
          has_chart: false,
          requires_clarification: false,
          failure_reason: "",
        },
      ],
    });
    vi.mocked(getWorkspaceRun).mockResolvedValue({
      success: true,
      workspace_id: "ws_1",
      run_id: "run_history",
      result: {
        product_result: {
          version: "p16.v1",
          status: "completed",
          question_thread: { original_question: "恢复历史问题", status: "completed" },
          business_answer: {
            headline: "历史业务结论",
            direct_answer: "这是从后端历史详情恢复的完整结果。",
            why: "来自后端保存的 run detail。",
            evidence_bullets: [],
            recommendations: [],
            caveats: [],
            confidence: "medium",
          },
          evidence: { table_preview: { columns: ["channel"], rows: [["email"]] } },
          chart_artifacts: [],
          technical_details: {},
        },
      },
    });

    render(<AnalysisRunner workspaceId="ws_1" />);
    fireEvent.click(await screen.findByRole("button", { name: /恢复历史问题/ }));

    await waitFor(() => expect(getWorkspaceRun).toHaveBeenCalledWith("ws_1", "run_history"));
    expect(await screen.findByText("历史业务结论", { selector: ".answer-headline" })).toBeTruthy();
    expect(screen.getByText("这是从后端历史详情恢复的完整结果。")).toBeTruthy();
    expect(screen.getByRole("button", { name: /恢复历史问题/ }).getAttribute("aria-current")).toBe("true");
  });

  it("shows Chinese history empty and error states", async () => {
    vi.mocked(listWorkspaceRuns).mockResolvedValueOnce({ workspace_id: "ws_1", runs: [] });

    const { unmount } = render(<AnalysisRunner workspaceId="ws_1" />);

    expect(await screen.findByText("还没有历史分析。开始提问后会保存在这里。")).toBeTruthy();
    unmount();

    vi.mocked(listWorkspaceRuns).mockRejectedValueOnce(new Error("backend unavailable"));
    render(<AnalysisRunner workspaceId="ws_1" />);

    expect(await screen.findByText("历史分析加载失败：backend unavailable")).toBeTruthy();
  });

  it("submits analysis questions and stores the run result for the detail page", async () => {
    vi.mocked(listWorkspaceRuns)
      .mockResolvedValueOnce({ workspace_id: "ws_1", runs: [] })
      .mockResolvedValueOnce({
        workspace_id: "ws_1",
        runs: [
          {
            run_id: "run_1",
            status: "completed",
            question: "哪个渠道收入最高？",
            headline: "Email produced the most revenue.",
            saved_at: "2026-06-29T12:00:00Z",
            has_chart: false,
            requires_clarification: false,
            failure_reason: "",
          },
        ],
      });
    vi.mocked(runAnalysis).mockResolvedValue({
      success: true,
      workspace_id: "ws_1",
      run_id: "run_1",
      result: {
        product_result: {
          version: "p16.v1",
          status: "completed",
          question_thread: {
            original_question: "哪个渠道收入最高？",
            system_understanding: "按渠道比较收入",
            resolved_question: "比较各渠道收入并给出建议。",
          },
          business_answer: {
            headline: "Email produced the most revenue.",
            direct_answer: "Email 贡献最高收入。",
            why: "证据表第一行显示：channel 为 email，revenue 为 100。",
            evidence_bullets: ["email revenue is 100"],
            recommendations: ["复核 email 投放预算"],
            caveats: [],
            confidence: "medium",
          },
          evidence: { table_preview: { columns: ["channel", "revenue"], rows: [["email", 100]] } },
          chart_artifacts: [],
          technical_details: { sql: "SELECT 1", raw_rows: [[1]] },
        },
      },
    });

    render(<AnalysisRunner workspaceId="ws_1" />);
    expect(screen.getByText("分析工作台")).toBeTruthy();
    expect(screen.getByText("问一个业务问题")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("业务问题"), {
      target: { value: "哪个渠道收入最高？" },
    });
    fireEvent.click(screen.getByRole("button", { name: "开始分析" }));

    await waitFor(() => expect(listWorkspaceRuns).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("分析线程")).toBeTruthy();
    expect(screen.getByText("用户问题")).toBeTruthy();
    expect(screen.getByText("系统理解")).toBeTruthy();
    expect(screen.getByText("整理后")).toBeTruthy();
    expect(screen.getByText("业务结论")).toBeTruthy();
    expect(await screen.findByText("Email produced the most revenue.")).toBeTruthy();
    expect(screen.getByText("比较各渠道收入并给出建议。")).toBeTruthy();
    expect(screen.getByRole("link", { name: "查看本次分析详情" }).getAttribute("href")).toBe(
      "/workspaces/ws_1/runs/run_1",
    );
    expect(
      JSON.parse(window.sessionStorage.getItem("insightflow.run.ws_1.run_1") ?? "{}").result.product_result
        .business_answer.headline,
    ).toBe("Email produced the most revenue.");
  });

  it("loads the run detail route from the backend without sessionStorage", async () => {
    vi.mocked(getWorkspaceRun).mockResolvedValue({
      success: true,
      workspace_id: "ws_1",
      run_id: "run_1",
      result: {
        generated_sql: "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
      },
      product_result: {
        version: "p16.v1",
        workspace_id: "ws_1",
        run_id: "run_1",
        status: "completed",
        question_thread: {
          original_question: "哪个渠道收入最高？",
          system_understanding: "按渠道比较收入",
          resolved_question: "比较各渠道收入并给出建议。",
          status: "completed",
        },
        business_answer: {
          headline: "Email produced the most revenue.",
          direct_answer: "Email 贡献最高收入。",
          why: "证据表第一行显示：channel 为 email，revenue 为 100。",
          evidence_bullets: ["email revenue is 100"],
          recommendations: ["复核 email 投放预算"],
          caveats: [],
          confidence: "medium",
        },
        evidence: { table_preview: { columns: ["channel", "revenue"], rows: [["email", 100]] } },
        chart_artifacts: [],
        technical_details: {
          sql: "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
          raw_rows: [["email", 100]],
          provider_metadata: { model: "deepseek" },
        },
      },
    });

    render(
      await RunDetailPage({
        params: Promise.resolve({ workspaceId: "ws_1", runId: "run_1" }),
      }),
    );

    expect(screen.getByRole("heading", { level: 1, name: "分析详情" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /分析工作台/ }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByText("正在加载分析详情")).toBeTruthy();

    await waitFor(() => expect(getWorkspaceRun).toHaveBeenCalledWith("ws_1", "run_1"));
    expect(await screen.findByText("Email produced the most revenue.", { selector: ".answer-headline" })).toBeTruthy();
    expect(screen.getByText("Email 贡献最高收入。")).toBeTruthy();
    expect(screen.getByText("email")).toBeTruthy();
    expect(screen.getByText("100")).toBeTruthy();
    expect(screen.getByText("技术详情")).toBeTruthy();
    expect(screen.queryByText(/SELECT channel/)).toBeNull();
    expect(screen.queryByText(/deepseek/)).toBeNull();
    expect(screen.queryByText(/当前浏览器会话没有缓存这次分析结果/)).toBeNull();
    expect(window.sessionStorage.getItem("insightflow.run.ws_1.run_1")).toBeNull();
  });

  it("shows a Chinese error state when backend run detail cannot be loaded", async () => {
    vi.mocked(getWorkspaceRun).mockRejectedValue(new Error("not found"));

    render(
      await RunDetailPage({
        params: Promise.resolve({ workspaceId: "ws_1", runId: "run_missing" }),
      }),
    );

    await waitFor(() => expect(getWorkspaceRun).toHaveBeenCalledWith("ws_1", "run_missing"));
    expect(await screen.findByText("无法加载分析详情")).toBeTruthy();
    expect(screen.getByText("请回到分析工作台，从历史分析中重新打开这条记录。")).toBeTruthy();
    expect(screen.queryByText(/当前浏览器会话没有缓存这次分析结果/)).toBeNull();
  });

  it("renders the business Q&A preview route with active navigation and honest preview copy", async () => {
    render(await BusinessQAPage({ params: Promise.resolve({ workspaceId: "ws_1" }) }));

    expect(screen.getByRole("heading", { level: 1, name: "业务问答" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /业务问答/ }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: /业务问答/ }).getAttribute("href")).toBe(
      "/workspaces/ws_1/business-qa",
    );
    expect(screen.getByText("业务问答模式")).toBeTruthy();
    expect(screen.getByText("未来模式预览")).toBeTruthy();
    expect(screen.getByLabelText("业务问答预览消息")).toBeTruthy();
    expect(screen.getByText(/最近 90 天哪个渠道应该加预算/)).toBeTruthy();
    expect(screen.getByText("正在理解问题")).toBeTruthy();
    expect(screen.getByText("当前上下文")).toBeTruthy();
    expect(screen.getByText("本轮产物")).toBeTruthy();
    expect(screen.getByText("业务结论")).toBeTruthy();
    expect(screen.getByText("证据表")).toBeTruthy();
    expect(screen.getByText("图表")).toBeTruthy();
    expect(screen.getByText("报告草稿")).toBeTruthy();
    expect(screen.getByRole("link", { name: "打开工作台查看完整证据" }).getAttribute("href")).toBe(
      "/workspaces/ws_1/analysis",
    );
    expect(screen.queryByText("完整聊天产品已上线")).toBeNull();
  });

  it("submits a business Q&A preview question through the existing analysis API", async () => {
    vi.mocked(runAnalysis).mockResolvedValue({
      success: true,
      workspace_id: "ws_1",
      run_id: "run_qa_1",
      result: {
        product_result: {
          version: "p16.v1",
          status: "completed",
          question_thread: {
            original_question: "下个月预算应该优先投哪个渠道？",
            system_understanding: "比较渠道表现并给出预算建议",
            resolved_question: "比较各渠道表现，给出下个月预算优先级建议。",
          },
          business_answer: {
            headline: "优先加码 paid_search，同时观察转化成本。",
            direct_answer: "paid_search 贡献更高收入，但需要结合成本观察。",
            why: "证据表第一行显示：channel 为 paid_search，revenue 为 200。",
            evidence_bullets: ["paid_search revenue is 200"],
            recommendations: ["先提高 paid_search 预算"],
            caveats: [],
            confidence: "medium",
          },
          evidence: { table_preview: { columns: ["channel", "revenue"], rows: [["paid_search", 200]] } },
          chart_artifacts: [],
          technical_details: {
            sql: "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
            raw_rows: [["paid_search", 200]],
            provider_metadata: { model: "deepseek" },
          },
        },
      },
    });

    render(<BusinessQAPreview workspaceId="ws_1" />);

    fireEvent.change(screen.getByLabelText("业务问题"), {
      target: { value: "下个月预算应该优先投哪个渠道？" },
    });
    fireEvent.click(screen.getByRole("button", { name: "生成预览回答" }));

    await waitFor(() =>
      expect(runAnalysis).toHaveBeenCalledWith("ws_1", {
        userQuestion: "下个月预算应该优先投哪个渠道？",
      }),
    );
    expect(await screen.findByText("优先加码 paid_search，同时观察转化成本。")).toBeTruthy();
    expect(screen.getByText("分析线程")).toBeTruthy();
    expect(screen.getAllByText("证据表").length).toBeGreaterThanOrEqual(1);

    const disclosure = screen.getByText("技术详情").closest("details");
    expect(disclosure?.hasAttribute("open")).toBe(false);
    expect(screen.queryByText(/SELECT channel/)).toBeNull();
    expect(screen.queryByText(/deepseek/)).toBeNull();
  });

  it("renders profile tables and candidate roles", () => {
    render(
      <ProfileSummary
        profile={{
          tables: [
            {
              table_name: "orders",
              row_count: 10,
              columns: [
                { name: "revenue", role_candidates: { measure: true } },
                { name: "channel", role_candidates: { dimension: true } },
              ],
            },
          ],
        }}
      />,
    );
    expect(screen.getByText("orders")).toBeTruthy();
    expect(screen.getByText("revenue")).toBeTruthy();
    expect(screen.getByText("指标")).toBeTruthy();
  });

  it("renders the integrated analysis thread in one compact card", () => {
    render(
      <RunResult
        result={{
          product_result: {
            version: "p16.v1",
            status: "completed",
            question_thread: {
              original_question: "帮我分析渠道表现",
              system_understanding: "按渠道比较收入表现",
              clarification_question: "你希望分析哪个时间范围？",
              clarification_answer: "最近 90 天",
              resolved_question: "分析最近 90 天各渠道收入和 ROI，并给出预算建议。",
            },
            business_answer: {
              headline: "建议优先加码 paid_search",
              direct_answer: "paid_search 收入最高。",
              why: "证据表第一行显示：channel 为 paid_search，revenue 为 200。",
              evidence_bullets: ["paid_search revenue is 200"],
              recommendations: ["提高预算"],
              caveats: [],
              confidence: "medium",
            },
            evidence: { table_preview: { columns: ["channel", "revenue"], rows: [["paid_search", 200]] } },
            chart_artifacts: [],
            technical_details: { sql: "SELECT 1", raw_rows: [[1]], provider_metadata: { model: "deepseek" } },
          },
        }}
      />,
    );

    const thread = screen.getByLabelText("分析线程");
    expect(screen.getByText("用户问题")).toBeTruthy();
    expect(screen.getByText("系统理解")).toBeTruthy();
    expect(screen.getByText("追问")).toBeTruthy();
    expect(screen.getByText("用户补充")).toBeTruthy();
    expect(screen.getByText("整理后")).toBeTruthy();
    expect(screen.getByText("业务结论")).toBeTruthy();
    expect(thread.textContent).toContain("帮我分析渠道表现");
    expect(thread.textContent).toContain("按渠道比较收入表现");
    expect(thread.textContent).toContain("你希望分析哪个时间范围？");
    expect(thread.textContent).toContain("最近 90 天");
    expect(thread.textContent).toContain("分析最近 90 天各渠道收入和 ROI");
    expect(screen.getByText("建议优先加码 paid_search")).toBeTruthy();
  });

  it("keeps SQL raw rows and provider metadata collapsed by default", () => {
    render(
      <RunResult
        result={{
          product_result: {
            version: "p16.v1",
            status: "completed",
            question_thread: { original_question: "看收入" },
            business_answer: {
              headline: "收入稳定",
              direct_answer: "收入保持稳定。",
              why: "证据表第一行显示：channel 为 email。",
              evidence_bullets: ["email 渠道有收入记录。"],
              recommendations: [],
              caveats: [],
              confidence: "medium",
            },
            evidence: { table_preview: { columns: ["channel"], rows: [["email"]] } },
            chart_artifacts: [],
            technical_details: {
              sql: "SELECT channel FROM orders",
              raw_rows: [["email"]],
              trace_path: "workspaces/ws_1/runs/run_1/trace.json",
              provider_metadata: { model: "deepseek" },
              validation_logs: [{ name: "review_result", value: { approved: true } }],
            },
          },
        }}
      />,
    );

    const disclosure = screen.getByText("技术详情").closest("details");
    expect(disclosure?.hasAttribute("open")).toBe(false);
    expect(screen.queryByText(/SELECT channel/)).toBeNull();
    expect(screen.queryByText(/deepseek/)).toBeNull();

    fireEvent.click(screen.getByText("技术详情"));

    expect(screen.getByText(/SELECT channel/)).toBeTruthy();
    expect(screen.getByText(/deepseek/)).toBeTruthy();
  });

  it("shows business-friendly failed SQL review copy and keeps reviewer details collapsed", () => {
    render(
      <RunResult
        result={{
          product_result: {
            version: "p16.v1",
            status: "failed",
            question_thread: { original_question: "按商品看看最近 30 天收入", status: "failed" },
            business_answer: {
              headline: "当前数据无法支持这次查询",
              direct_answer: "系统尝试使用当前工作区中不存在的表或字段，因此没有执行查询。",
              why: "SQL 审核发现查询引用了当前数据中不存在的表或字段。",
              evidence_bullets: [],
              recommendations: [
                "可以改问当前数据已包含的渠道、收入、订单、投放花费和 ROI。",
                "如果要分析商品、订单明细或产品维度，请先上传对应数据表。",
              ],
              caveats: ["本轮没有执行未通过审核的 SQL。"],
              confidence: "low",
            },
            evidence: { table_preview: { columns: [], rows: [] } },
            chart_artifacts: [],
            technical_details: {
              validation_logs: [
                {
                  name: "review_result",
                  value: {
                    approved: false,
                    issues: ["Unknown table: products", "Unknown column: order_items.quantity"],
                  },
                },
              ],
            },
          },
        }}
      />,
    );

    expect(screen.getByText("当前数据无法支持这次查询")).toBeTruthy();
    expect(screen.getByText("系统尝试使用当前工作区中不存在的表或字段，因此没有执行查询。")).toBeTruthy();
    expect(screen.getByText("可以改问当前数据已包含的渠道、收入、订单、投放花费和 ROI。")).toBeTruthy();
    expect(screen.queryByText(/Unknown table/)).toBeNull();
    expect(screen.queryByText(/Unknown column/)).toBeNull();

    fireEvent.click(screen.getByText("技术详情"));

    expect(screen.getByText(/Unknown table: products/)).toBeTruthy();
    expect(screen.getByText(/Unknown column: order_items.quantity/)).toBeTruthy();
  });

  it("replaces raw SQL reviewer wall in failed history summaries", async () => {
    vi.mocked(listWorkspaceRuns).mockResolvedValue({
      workspace_id: "ws_1",
      runs: [
        {
          run_id: "run_failed_raw",
          status: "failed",
          question: "分析商品表现",
          headline: "",
          saved_at: "2026-06-29T12:00:00Z",
          has_chart: false,
          requires_clarification: false,
          failure_reason: "Review rejected before execution: Unknown table: products; Unknown column: product_name",
        },
      ],
    });

    render(<AnalysisRunner workspaceId="ws_1" />);

    expect(await screen.findByText("分析商品表现")).toBeTruthy();
    expect(screen.getByText("原因：本轮分析未能执行，请打开详情查看技术信息。")).toBeTruthy();
    expect(screen.queryByText(/Unknown table/)).toBeNull();
    expect(screen.queryByText(/Unknown column/)).toBeNull();
  });

  it("submits only the clarification answer for a pending run", async () => {
    vi.mocked(listWorkspaceRuns)
      .mockResolvedValueOnce({ workspace_id: "ws_1", runs: [] })
      .mockResolvedValueOnce({ workspace_id: "ws_1", runs: [{ run_id: "run_pending", status: "waiting_for_clarification", question: "帮我分析渠道表现", headline: "需要补充时间范围", saved_at: "2026-06-29T12:00:00Z", has_chart: false, requires_clarification: true, failure_reason: "" }] })
      .mockResolvedValueOnce({ workspace_id: "ws_1", runs: [{ run_id: "run_done", status: "completed", question: "帮我分析渠道表现", headline: "paid_search 表现最好", saved_at: "2026-06-29T12:05:00Z", has_chart: false, requires_clarification: false, failure_reason: "" }] });
    vi.mocked(runAnalysis)
      .mockResolvedValueOnce({
        success: true,
        workspace_id: "ws_1",
        run_id: "run_pending",
        result: {
          product_result: {
            version: "p16.v1",
            status: "waiting_for_clarification",
            question_thread: {
              pending_run_id: "pending_1",
              original_question: "帮我分析渠道表现",
              system_understanding: "需要按渠道比较表现",
              clarification_question: "你希望分析哪个时间范围？",
              status: "waiting_for_clarification",
            },
            business_answer: {
              headline: "需要补充时间范围",
              direct_answer: "请先补充时间范围后再继续分析。",
              why: "当前问题还缺少必要分析条件。",
              evidence_bullets: [],
              recommendations: [],
              caveats: ["补充时间范围后才能执行查询。"],
              confidence: "low",
            },
            evidence: { table_preview: { columns: [], rows: [] } },
            chart_artifacts: [],
            technical_details: {},
          },
        },
      })
      .mockResolvedValueOnce({
        success: true,
        workspace_id: "ws_1",
        run_id: "run_done",
        result: {
          product_result: {
            version: "p16.v1",
            status: "completed",
            question_thread: {
              original_question: "帮我分析渠道表现",
              clarification_question: "你希望分析哪个时间范围？",
              clarification_answer: "最近 90 天",
              resolved_question: "分析最近 90 天各渠道表现。",
            },
            business_answer: {
              headline: "paid_search 表现最好",
              direct_answer: "收入最高。",
              why: "证据表支持 paid_search 表现最好。",
              evidence_bullets: [],
              recommendations: [],
              caveats: [],
              confidence: "medium",
            },
            evidence: { table_preview: { columns: [], rows: [] } },
            chart_artifacts: [],
            technical_details: {},
          },
        },
      });

    render(<AnalysisRunner workspaceId="ws_1" />);
    fireEvent.change(screen.getByLabelText("业务问题"), { target: { value: "帮我分析渠道表现" } });
    fireEvent.click(screen.getByRole("button", { name: "开始分析" }));
    expect(await screen.findByText("追问")).toBeTruthy();
    fireEvent.change(await screen.findByLabelText("用户补充"), { target: { value: "最近 90 天" } });
    fireEvent.click(screen.getByRole("button", { name: "继续分析" }));

    await waitFor(() =>
      expect(runAnalysis).toHaveBeenLastCalledWith("ws_1", {
        pendingRunId: "pending_1",
        clarificationAnswer: "最近 90 天",
      }),
    );
    await waitFor(() => expect(listWorkspaceRuns).toHaveBeenCalledTimes(3));
    expect(await screen.findByText("用户补充")).toBeTruthy();
    expect(screen.getByText("整理后")).toBeTruthy();
    expect(await screen.findByText("paid_search 表现最好")).toBeTruthy();
  });

  it("starts a contextual follow-up analysis after a completed run", async () => {
    vi.mocked(listWorkspaceRuns)
      .mockResolvedValueOnce({ workspace_id: "ws_1", runs: [] })
      .mockResolvedValueOnce({ workspace_id: "ws_1", runs: [{ run_id: "run_done", status: "completed", question: "帮我分析最近90天哪些渠道收益比较好", headline: "email 渠道收益最好", saved_at: "2026-06-29T12:00:00Z", has_chart: false, requires_clarification: false, failure_reason: "" }] })
      .mockResolvedValueOnce({ workspace_id: "ws_1", runs: [{ run_id: "run_followup", status: "completed", question: "为什么 email 渠道收益最好？", headline: "email 的客单价更高", saved_at: "2026-06-29T12:05:00Z", has_chart: false, requires_clarification: false, failure_reason: "" }] });
    vi.mocked(runAnalysis)
      .mockResolvedValueOnce({
        success: true,
        workspace_id: "ws_1",
        run_id: "run_done",
        result: {
          product_result: {
            version: "p16.v1",
            status: "completed",
            question_thread: {
              original_question: "帮我分析最近90天哪些渠道收益比较好",
              system_understanding: "按最近 90 天比较渠道收益。",
              resolved_question: "分析最近 90 天各渠道收益表现。",
              status: "completed",
            },
            business_answer: {
              headline: "email 渠道收益最好",
              direct_answer: "email 收益最高。",
              why: "证据表显示 email 渠道收益最好。",
              evidence_bullets: ["email 渠道收益最高。"],
              recommendations: [],
              caveats: [],
              confidence: "medium",
            },
            evidence: { table_preview: { columns: ["channel"], rows: [["email"]] } },
            chart_artifacts: [],
            technical_details: {},
          },
        },
      })
      .mockResolvedValueOnce({
        success: true,
        workspace_id: "ws_1",
        run_id: "run_followup",
        result: {
          product_result: {
            version: "p16.v1",
            status: "completed",
            question_thread: {
              original_question: "基于上一轮分析继续追问",
              resolved_question: "继续分析 email 渠道为什么收益最好。",
              status: "completed",
            },
            business_answer: {
              headline: "email 的客单价更高",
              direct_answer: "email 渠道收益高主要来自客单价。",
              why: "证据表显示 email 客单价更高。",
              evidence_bullets: ["email 客单价更高。"],
              recommendations: [],
              caveats: [],
              confidence: "medium",
            },
            evidence: { table_preview: { columns: ["channel"], rows: [["email"]] } },
            chart_artifacts: [],
            technical_details: {},
          },
        },
      });

    render(<AnalysisRunner workspaceId="ws_1" />);
    fireEvent.change(screen.getByLabelText("业务问题"), {
      target: { value: "帮我分析最近90天哪些渠道收益比较好" },
    });
    fireEvent.click(screen.getByRole("button", { name: "开始分析" }));

    expect(await screen.findByText("email 渠道收益最好")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("继续追问"), {
      target: { value: "为什么 email 渠道收益最好？" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送追问" }));

    await waitFor(() => expect(runAnalysis).toHaveBeenCalledTimes(2));
    const followUpRequest = vi.mocked(runAnalysis).mock.calls[1][1];
    expect(followUpRequest).toMatchObject({
      userQuestion: expect.stringContaining("为什么 email 渠道收益最好？"),
    });
    expect(String((followUpRequest as { userQuestion?: string }).userQuestion)).toContain(
      "帮我分析最近90天哪些渠道收益比较好",
    );
    await waitFor(() => expect(listWorkspaceRuns).toHaveBeenCalledTimes(3));
    expect(await screen.findByText("email 的客单价更高")).toBeTruthy();
  });

  it("renders the business answer before evidence and technical details", () => {
    const { container } = render(
      <RunResult
        result={{
          product_result: {
            version: "p16.v1",
            status: "completed",
            question_thread: { original_question: "分析渠道" },
            business_answer: {
              headline: "先看业务结论",
              direct_answer: "这是业务摘要。",
              why: "证据表第一行显示：channel 为 email。",
              evidence_bullets: ["email 渠道有收入记录。"],
              recommendations: [],
              caveats: [],
              confidence: "medium",
            },
            evidence: { table_preview: { columns: ["channel"], rows: [["email"]] } },
            chart_artifacts: [],
            technical_details: { sql: "SELECT 1", raw_rows: [[1]] },
          },
        }}
      />,
    );

    const text = container.textContent ?? "";
    expect(text).toContain("业务结论");
    expect(text.indexOf("先看业务结论")).toBeLessThan(text.indexOf("证据表"));
    expect(text.indexOf("证据表")).toBeLessThan(text.indexOf("技术详情"));
  });

  it("renders only the P16 business answer contract fields in business order", () => {
    const { container } = render(
      <BusinessAnswerCard
        answer={
          {
            headline: "建议优先关注 email 渠道",
            direct_answer: "email 渠道贡献最高收入。",
            why: "证据显示 email 收入排在第一。",
            evidence_bullets: ["email 收入为 100。"],
            recommendations: ["复核 email 的投放预算。"],
            caveats: ["样本只覆盖最近 30 天。"],
            confidence: "high",
            summary: "旧摘要不应展示。",
            next_actions: ["旧动作不应展示。"],
            source: "legacy",
            quality_flags: ["legacy"],
          } as never
        }
      />,
    );

    expect(screen.getByText("结论")).toBeTruthy();
    expect(screen.getByText("建议优先关注 email 渠道")).toBeTruthy();
    expect(screen.getByText("直接回答")).toBeTruthy();
    expect(screen.getByText("email 渠道贡献最高收入。")).toBeTruthy();
    expect(screen.getByText("为什么")).toBeTruthy();
    expect(screen.getByText("关键证据")).toBeTruthy();
    expect(screen.getByText("建议动作")).toBeTruthy();
    expect(screen.getByText("限制说明")).toBeTruthy();
    expect(screen.getByText("置信度 high")).toBeTruthy();

    const text = container.textContent ?? "";
    expect(text.indexOf("结论")).toBeLessThan(text.indexOf("直接回答"));
    expect(text.indexOf("直接回答")).toBeLessThan(text.indexOf("为什么"));
    expect(text.indexOf("为什么")).toBeLessThan(text.indexOf("关键证据"));
    expect(text.indexOf("关键证据")).toBeLessThan(text.indexOf("建议动作"));
    expect(text.indexOf("建议动作")).toBeLessThan(text.indexOf("限制说明"));
    expect(text).not.toContain("Business Answer");
    expect(text).not.toContain("旧摘要不应展示");
    expect(text).not.toContain("旧动作不应展示");
    expect(text).not.toContain("legacy");
  });

  it("renders chart artifact images with title alt text and hides local paths from the main UI", () => {
    render(
      <ChartArtifactGallery
        artifacts={[
          {
            title: "渠道收入",
            path: "runs/run_1/charts/channel.png",
            url: "/api/workspaces/ws_1/artifacts/runs/run_1/charts/channel.png",
            unit: "元",
            business_annotation: "付费搜索贡献最高。",
          },
        ]}
      />,
    );

    const image = screen.getByRole("img", { name: "渠道收入" }) as HTMLImageElement;
    expect(image.getAttribute("src")).toBe(
      "http://localhost:8000/api/workspaces/ws_1/artifacts/runs/run_1/charts/channel.png",
    );
    expect(screen.getByText("付费搜索贡献最高。")).toBeTruthy();
    expect(screen.queryByText("runs/run_1/charts/channel.png")).toBeNull();
  });

  it("shows an empty chart gallery state when no artifacts exist", () => {
    render(<ChartArtifactGallery artifacts={[]} />);

    expect(screen.getByText("暂无图表")).toBeTruthy();
  });

  it("shows business-friendly caveats for sanitized raw parameter dumps", () => {
    render(
      <RunResult
        result={{
          product_result: {
            version: "p16.v1",
            status: "completed",
            question_thread: { original_question: "分析渠道" },
            business_answer: {
              headline: "查询已完成",
              direct_answer: "已完成查询。",
              why: "当前回答已移除技术参数格式内容。",
              evidence_bullets: [],
              recommendations: [],
              caveats: ["模型原始回答包含参数格式内容，已从业务结论中移除。"],
              confidence: "low",
            },
            evidence: { table_preview: { columns: [], rows: [] } },
            chart_artifacts: [],
            technical_details: { raw_rows: [["channel=paid_search, revenue=200"]] },
          },
        }}
      />,
    );

    expect(screen.getByText("模型原始回答包含参数格式内容，已从业务结论中移除。")).toBeTruthy();
  });

  it("does not synthesize product output from raw final_answer fields", () => {
    render(
      <RunResult
        result={{
          status: "completed",
          final_answer: "Raw legacy final answer should stay hidden.",
          execution_result: { columns: ["channel"], rows: [["email"]] },
        }}
      />,
    );

    expect(screen.getByText("分析结果结构异常")).toBeTruthy();
    expect(screen.getByText("后端没有返回当前 P16 业务答案结构，请重新运行分析。")).toBeTruthy();
    expect(screen.queryByText("Raw legacy final answer should stay hidden.")).toBeNull();
    expect(screen.queryByText("email")).toBeNull();
  });

  it("rejects legacy business_answer fields instead of rendering fallback product content", () => {
    render(
      <RunResult
        result={{
          product_result: {
            version: "p16.v1",
            status: "completed",
            question_thread: { original_question: "哪个渠道收入最高？" },
            business_answer: {
              summary: "旧 summary 不应展示。",
              next_actions: ["旧 next_actions 不应展示。"],
              source: "legacy",
              quality_flags: ["old_shape"],
            },
            evidence: { table_preview: { columns: ["channel"], rows: [["email"]] } },
            chart_artifacts: [],
            technical_details: { sql: "SELECT channel FROM orders" },
          },
        }}
      />,
    );

    expect(screen.getByText("分析结果结构异常")).toBeTruthy();
    expect(screen.getByText("后端没有返回当前 P16 业务答案结构，请重新运行分析。")).toBeTruthy();
    expect(screen.queryByText("旧 summary 不应展示。")).toBeNull();
    expect(screen.queryByText("旧 next_actions 不应展示。")).toBeNull();
    expect(screen.queryByText("legacy")).toBeNull();
    expect(screen.queryByText("email")).toBeNull();
    expect(screen.queryByText("技术详情")).toBeNull();
  });

  it("renders an empty report list state", async () => {
    vi.mocked(listWorkspaceReports).mockResolvedValue({ workspace_id: "ws_1", reports: [] });

    render(<ReportList workspaceId="ws_1" />);

    expect(screen.getByText("正在加载报告")).toBeTruthy();
    expect(await screen.findByText("还没有生成报告")).toBeTruthy();
    expect(screen.getByText("生成第一份管理层复盘，之后会在这里按创建时间展示。")).toBeTruthy();
  });

  it("submits a report generation form and opens the created report", async () => {
    vi.mocked(createWorkspaceReport).mockResolvedValue({
      success: true,
      workspace_id: "ws_1",
      report_id: "report_1",
      report: {
        report_id: "report_1",
        workspace_id: "ws_1",
        report_type: "channel_performance",
        report_goal: "Compare acquisition channel revenue.",
        title: "Channel Performance",
        status: "completed",
        executive_summary: ["Paid search led revenue."],
        sections: [],
        markdown_path: "workspaces/ws_1/reports/report_1/report.md",
        json_path: "workspaces/ws_1/reports/report_1/report.json",
        trace_path: "workspaces/ws_1/reports/report_1/trace.json",
        artifact_dir: "workspaces/ws_1/reports/report_1/artifacts",
      },
    });

    render(<ReportGenerator workspaceId="ws_1" />);
    expect(screen.getByText("新建报告")).toBeTruthy();
    expect(screen.getByText("生成最近 90 天渠道表现复盘")).toBeTruthy();
    expect(screen.getByText("生成管理层收入复盘报告")).toBeTruthy();
    expect(screen.getByText("生成客户增长与留存报告")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("报告类型"), { target: { value: "channel_performance" } });
    fireEvent.change(screen.getByLabelText("报告目标"), {
      target: { value: "生成最近 90 天渠道表现复盘" },
    });
    fireEvent.click(screen.getByRole("button", { name: "生成报告" }));

    await waitFor(() =>
      expect(createWorkspaceReport).toHaveBeenCalledWith("ws_1", {
        reportType: "channel_performance",
        reportGoal: "生成最近 90 天渠道表现复盘",
      }),
    );
    expect(pushMock).toHaveBeenCalledWith("/workspaces/ws_1/reports/report_1");
  });

  it("renders generated report list items", async () => {
    vi.mocked(listWorkspaceReports).mockResolvedValue({
      workspace_id: "ws_1",
      reports: [
        {
          report_id: "report_1",
          workspace_id: "ws_1",
          report_type: "business_review",
          report_goal: "Review revenue.",
          title: "Business Review",
          status: "completed",
          executive_summary: ["Revenue grew."],
          sections: [],
          markdown_path: "workspaces/ws_1/reports/report_1/report.md",
          json_path: "workspaces/ws_1/reports/report_1/report.json",
          trace_path: "workspaces/ws_1/reports/report_1/trace.json",
          artifact_dir: "workspaces/ws_1/reports/report_1/artifacts",
          created_at: "2026-06-23T00:00:00Z",
        },
      ],
    });

    render(<ReportList workspaceId="ws_1" />);

    expect(await screen.findByText("Business Review")).toBeTruthy();
    expect(screen.getByText("报告列表")).toBeTruthy();
    expect(screen.getByText("生成状态：已完成")).toBeTruthy();
    expect(screen.getByText("报告类型：经营复盘")).toBeTruthy();
    expect(screen.getByText(/创建时间：2026-06-23/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "打开报告" }).getAttribute("href")).toBe(
      "/workspaces/ws_1/reports/report_1",
    );
  });

  it("renders the report center route with active product navigation", async () => {
    vi.mocked(listWorkspaceReports).mockResolvedValue({ workspace_id: "ws_1", reports: [] });

    render(await ReportsPage({ params: Promise.resolve({ workspaceId: "ws_1" }) }));

    expect(screen.getByRole("heading", { level: 1, name: "报告中心" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /报告中心/ }).getAttribute("aria-current")).toBe("page");
    expect(await screen.findByText("还没有生成报告")).toBeTruthy();
    expect(screen.getByText("新建报告")).toBeTruthy();
  });

  it("renders business report detail with a collapsed technical appendix and Markdown download link", async () => {
    vi.mocked(getWorkspaceReportDownloadUrl).mockReturnValue(
      "http://localhost:8000/api/workspaces/ws_1/reports/report_1/download",
    );
    vi.mocked(getWorkspaceReport).mockResolvedValue({
      workspace_id: "ws_1",
      report_id: "report_1",
      report: {
        report_id: "report_1",
        workspace_id: "ws_1",
        report_type: "business_review",
        report_goal: "Review revenue.",
        title: "Business Review",
        status: "completed",
        executive_summary: ["Revenue grew."],
        sections: [
          {
            section_id: "revenue_by_channel",
            title: "Revenue by Channel",
            purpose: "Compare channels.",
            status: "completed",
            question: "Which channels led revenue?",
            summary: "旧 summary 不应展示。",
            business_answer: {
              headline: "付费搜索收入领先",
              direct_answer: "付费搜索是本节收入最高的渠道。",
              why: "证据表显示 paid_search 收入为 200。",
              evidence_bullets: ["paid_search 收入为 200。"],
              recommendations: ["优先复盘付费搜索渠道。"],
              caveats: ["当前只基于报告章节查询结果。"],
              confidence: "high",
            },
            sql: "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
            columns: ["channel", "revenue"],
            rows_preview: [{ channel: "paid_search", revenue: 200 }],
            artifact_paths: ["artifacts/revenue_by_channel_1.png"],
            business_artifacts: [
              {
                type: "chart",
                path: "artifacts/revenue_by_channel_1.png",
                title: "Revenue by Channel",
              },
            ],
            evidence_notes: ["Rows preview came from workspace data."],
            provider_metadata: { sql_planning: { provider_called: true } },
            trace_nodes: ["sql_reviewer"],
            technical_details: {
              internal_question: "这是自动报告内部 section。Which channels led revenue?",
              purpose: "Compare channels.",
              sql: "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
              rows_preview: [{ channel: "paid_search", revenue: 200 }],
              provider_metadata: { sql_planning: { provider_called: true } },
              trace_nodes: ["sql_reviewer"],
            },
          },
        ],
        markdown_path: "workspaces/ws_1/reports/report_1/report.md",
        json_path: "workspaces/ws_1/reports/report_1/report.json",
        trace_path: "workspaces/ws_1/reports/report_1/trace.json",
        artifact_dir: "workspaces/ws_1/reports/report_1/artifacts",
        provider_metadata: { completed_section_count: 1 },
      },
    });

    render(<ReportViewer workspaceId="ws_1" reportId="report_1" />);

    expect(await screen.findByText("Business Review")).toBeTruthy();
    expect(screen.getByText("生成状态：已完成")).toBeTruthy();
    expect(screen.getByText("进度：1/1 个章节已完成")).toBeTruthy();
    expect(screen.getByText("管理层摘要 / Executive Summary")).toBeTruthy();
    expect(screen.getByText("报告章节")).toBeTruthy();
    expect(screen.getByText("Revenue grew.")).toBeTruthy();
    expect(screen.getByText("结论")).toBeTruthy();
    expect(screen.getByText("付费搜索收入领先")).toBeTruthy();
    expect(screen.getByText("直接回答")).toBeTruthy();
    expect(screen.getByText("付费搜索是本节收入最高的渠道。")).toBeTruthy();
    expect(screen.getByText("为什么")).toBeTruthy();
    expect(screen.getByText("证据表显示 paid_search 收入为 200。")).toBeTruthy();
    expect(screen.getByText("关键证据")).toBeTruthy();
    expect(screen.getByText("paid_search 收入为 200。")).toBeTruthy();
    expect(screen.getByText("建议动作")).toBeTruthy();
    expect(screen.getByText("优先复盘付费搜索渠道。")).toBeTruthy();
    expect(screen.getByText("限制说明")).toBeTruthy();
    expect(screen.getByText("当前只基于报告章节查询结果。")).toBeTruthy();
    expect(screen.getByText("置信度 high")).toBeTruthy();
    expect(screen.queryByText("旧 summary 不应展示。")).toBeNull();
    expect(screen.queryByText("Rows preview came from workspace data.")).toBeNull();
    expect(screen.getByText("图表或附件")).toBeTruthy();
    expect(screen.getByRole("img", { name: "Revenue by Channel" }).getAttribute("src")).toBe(
      "http://localhost:8000/api/workspaces/ws_1/artifacts/reports/report_1/artifacts/revenue_by_channel_1.png",
    );
    expect(screen.getByRole("link", { name: "下载图表" }).getAttribute("href")).toBe(
      "http://localhost:8000/api/workspaces/ws_1/artifacts/reports/report_1/artifacts/revenue_by_channel_1.png",
    );
    expect(screen.queryByText("Revenue by Channel 图表已生成")).toBeNull();
    expect(screen.queryByText("artifacts/revenue_by_channel_1.png")).toBeNull();
    expect(screen.queryByText("workspaces/ws_1/reports/report_1/report.md")).toBeNull();
    expect(screen.queryByText("workspaces/ws_1/reports/report_1/report.json")).toBeNull();
    expect(screen.queryByText("workspaces/ws_1/reports/report_1/artifacts")).toBeNull();
    expect(screen.queryByText(/SELECT channel/)).toBeNull();
    expect(screen.queryByText("paid_search")).toBeNull();
    expect(screen.queryByText(/provider_called/)).toBeNull();
    expect(screen.queryByText(/sql_reviewer/)).toBeNull();
    expect(screen.queryByText(/trace.json/)).toBeNull();

    const appendix = screen.getByText("技术附录").closest("details");
    expect(appendix?.hasAttribute("open")).toBe(false);
    fireEvent.click(screen.getByText("技术附录"));
    expect(screen.getByText(/SELECT channel/)).toBeTruthy();
    expect(screen.getByText(/provider_called/)).toBeTruthy();
    expect(screen.getByText(/sql_reviewer/)).toBeTruthy();
    expect(screen.getByText(/这是自动报告内部 section/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "下载 Markdown" }).getAttribute("href")).toBe(
      "http://localhost:8000/api/workspaces/ws_1/reports/report_1/download",
    );
  });

  it("rejects malformed report business_answer instead of rendering legacy report body", () => {
    render(
      <ReportSection
        workspaceId="ws_1"
        reportId="report_1"
        section={
          {
            section_id: "legacy_section",
            title: "Legacy Section",
            status: "completed",
            summary: "旧 summary 不应展示。",
            business_answer: {
              summary: "旧业务摘要不应展示。",
              next_actions: ["旧行动不应展示。"],
              direct_answer: "",
            },
            artifact_paths: ["artifacts/legacy.png"],
            business_artifacts: [
              {
                type: "chart",
                path: "artifacts/legacy.png",
                title: "Legacy Chart",
              },
            ],
          } as never
        }
      />,
    );

    expect(screen.getByText("报告章节结构异常")).toBeTruthy();
    expect(screen.getByText("后端没有返回完整的 P16 business_answer，请重新生成报告。")).toBeTruthy();
    expect(screen.queryByText("旧 summary 不应展示。")).toBeNull();
    expect(screen.queryByText("旧业务摘要不应展示。")).toBeNull();
    expect(screen.queryByText("旧行动不应展示。")).toBeNull();
    expect(screen.queryByText("直接回答")).toBeNull();
    expect(screen.queryByText("Legacy Chart")).toBeNull();
  });

  it("renders the report detail route inside the product shell", async () => {
    vi.mocked(getWorkspaceReportDownloadUrl).mockReturnValue(
      "http://localhost:8000/api/workspaces/ws_1/reports/report_1/download",
    );
    vi.mocked(getWorkspaceReport).mockResolvedValue({
      workspace_id: "ws_1",
      report_id: "report_1",
      report: {
        report_id: "report_1",
        workspace_id: "ws_1",
        report_type: "business_review",
        report_goal: "生成管理层收入复盘报告",
        title: "管理层收入复盘报告",
        status: "completed",
        executive_summary: ["收入增长稳定。"],
        sections: [
          {
            section_id: "summary",
            title: "收入概览",
            status: "completed",
            summary: "旧 summary 不应展示。",
            business_answer: {
              headline: "收入保持增长",
              direct_answer: "本节显示收入保持增长。",
              why: "证据表显示最近周期收入高于上一周期。",
              evidence_bullets: ["最近周期收入增长。"],
              recommendations: [],
              caveats: ["当前只基于报告章节查询结果。"],
              confidence: "medium",
            },
          },
        ],
      },
    });

    render(
      await ReportDetailPage({
        params: Promise.resolve({ workspaceId: "ws_1", reportId: "report_1" }),
      }),
    );

    expect(screen.getByRole("heading", { level: 1, name: "报告中心" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /报告中心/ }).getAttribute("aria-current")).toBe("page");
    expect(await screen.findByText("管理层收入复盘报告")).toBeTruthy();
    expect(screen.getByText("收入增长稳定。")).toBeTruthy();
    expect(screen.getByText("本节显示收入保持增长。")).toBeTruthy();
    expect(screen.queryByText("旧 summary 不应展示。")).toBeNull();
  });

  it.each([
    ["completed", "已完成", "进度：1/1 个章节已完成"],
    ["partial", "部分完成", "进度：1/2 个章节已完成，1 个章节失败"],
    ["failed", "失败", "进度：0/1 个章节已完成，1 个章节失败"],
    ["running", "生成中", "进度：0/1 个章节已完成，仍在生成"],
  ])("shows clear report status and progress for %s reports", async (status, label, progress) => {
    vi.mocked(getWorkspaceReportDownloadUrl).mockReturnValue(
      "http://localhost:8000/api/workspaces/ws_1/reports/report_1/download",
    );
    vi.mocked(getWorkspaceReport).mockResolvedValue({
      workspace_id: "ws_1",
      report_id: "report_1",
      report: {
        report_id: "report_1",
        workspace_id: "ws_1",
        report_type: "business_review",
        report_goal: "Review revenue.",
        title: "Business Review",
        status,
        executive_summary: [],
        sections:
          status === "partial"
            ? [
                {
                  section_id: "done",
                  title: "Done",
                  status: "completed",
                  business_answer: {
                    headline: "已完成",
                    direct_answer: "本章节已完成。",
                    why: "章节分析成功返回业务答案。",
                    evidence_bullets: [],
                    recommendations: [],
                    caveats: [],
                    confidence: "medium",
                  },
                },
                {
                  section_id: "failed",
                  title: "Failed",
                  status: "failed",
                  business_answer: {
                    headline: "章节生成失败",
                    direct_answer: "本章节未能生成业务答案。",
                    why: "章节分析没有完成。",
                    evidence_bullets: [],
                    recommendations: [],
                    caveats: ["可重新生成报告。"],
                    confidence: "low",
                  },
                  error: "Failed.",
                },
              ]
            : [
                {
                  section_id: "section",
                  title: "Section",
                  status: status === "completed" ? "completed" : status === "running" ? "running" : "failed",
                  business_answer:
                    status === "completed"
                      ? {
                          headline: "已完成",
                          direct_answer: "本章节已完成。",
                          why: "章节分析成功返回业务答案。",
                          evidence_bullets: [],
                          recommendations: [],
                          caveats: [],
                          confidence: "medium",
                        }
                      : {
                          headline: status === "running" ? "章节仍在生成" : "章节生成失败",
                          direct_answer: status === "running" ? "本章节仍在生成。" : "本章节未能生成业务答案。",
                          why: status === "running" ? "报告任务尚未完成。" : "章节分析没有完成。",
                          evidence_bullets: [],
                          recommendations: [],
                          caveats: status === "running" ? [] : ["可重新生成报告。"],
                          confidence: "low",
                        },
                  error: status === "failed" ? "Failed." : null,
                },
              ],
      },
    });

    render(<ReportViewer workspaceId="ws_1" reportId="report_1" />);

    expect(await screen.findByText(`生成状态：${label}`)).toBeTruthy();
    expect(screen.getByText(progress)).toBeTruthy();
  });

  it("renders report API errors", async () => {
    vi.mocked(listWorkspaceReports).mockRejectedValue(new Error("Failed to list reports: 500"));

    render(<ReportList workspaceId="ws_1" />);

    expect((await screen.findByRole("alert")).textContent).toBe("Failed to list reports: 500");
  });
});
