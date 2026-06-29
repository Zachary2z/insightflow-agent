import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AnalysisRunner from "../components/AnalysisRunner";
import ChartArtifactGallery from "../components/ChartArtifactGallery";
import DataSettings from "../components/DataSettings";
import DatasetManager from "../components/DatasetManager";
import ProfileSummary from "../components/ProfileSummary";
import ProfileWorkspace from "../components/ProfileWorkspace";
import ReportGenerator from "../components/ReportGenerator";
import ReportList from "../components/ReportList";
import ReportViewer from "../components/ReportViewer";
import RunResult from "../components/RunResult";
import SemanticLayerWorkspace from "../components/SemanticLayerWorkspace";
import WorkspaceList from "../components/WorkspaceList";
import WorkspaceNewForm from "../components/WorkspaceNewForm";
import DatasetsPage from "../app/workspaces/[workspaceId]/datasets/page";
import ReportDetailPage from "../app/workspaces/[workspaceId]/reports/[reportId]/page";
import ReportsPage from "../app/workspaces/[workspaceId]/reports/page";
import SettingsPage from "../app/workspaces/[workspaceId]/settings/page";

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
  getWorkspaceReportDownloadUrl: vi.fn(),
  getWorkspaceSettings: vi.fn(),
  importSqliteSource: vi.fn(),
  listWorkspaceReports: vi.fn(),
  listSources: vi.fn(),
  listWorkspaces: vi.fn(),
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
  getWorkspaceSettings,
  importSqliteSource,
  listWorkspaceReports,
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

    expect(screen.getByText("Loading workspaces")).toBeTruthy();
    expect(await screen.findByText("Finance Workspace")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open datasets" }).getAttribute("href")).toBe(
      "/workspaces/ws_1/datasets",
    );
  });

  it("creates a workspace and reports the datasets destination", async () => {
    const onCreated = vi.fn();
    vi.mocked(createWorkspace).mockResolvedValue({ workspace_id: "ws_2", name: "Ops" });

    render(<WorkspaceNewForm onCreated={onCreated} />);
    fireEvent.change(screen.getByLabelText("Workspace name"), { target: { value: "Ops" } });
    fireEvent.click(screen.getByRole("button", { name: "Create workspace" }));

    await waitFor(() => expect(createWorkspace).toHaveBeenCalledWith("Ops"));
    expect(onCreated).toHaveBeenCalledWith({ workspace_id: "ws_2", name: "Ops" });
    expect(await screen.findByText(/Workspace created/)).toBeTruthy();
  });

  it("renders the data source management page route with active product navigation", async () => {
    vi.mocked(listSources).mockResolvedValue({ sources: [] });

    render(await DatasetsPage({ params: Promise.resolve({ workspaceId: "ws_1" }) }));

    expect(screen.getByRole("heading", { level: 1, name: "数据源管理" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /数据源管理/ }).getAttribute("aria-current")).toBe("page");
    expect(await screen.findByText("还没有导入数据源")).toBeTruthy();
  });

  it("uploads files, imports SQLite, and renders Chinese source management metadata", async () => {
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
    vi.mocked(uploadSource).mockResolvedValue({ success: true, imported_tables: ["returns"] });
    vi.mocked(importSqliteSource).mockResolvedValue({ success: true, imported_tables: ["invoices"] });

    render(<DatasetManager workspaceId="ws_1" />);

    expect(await screen.findByText("已导入数据源")).toBeTruthy();
    expect(screen.getByText("上传 CSV / Excel")).toBeTruthy();
    expect(screen.getByText("导入 SQLite")).toBeTruthy();
    expect(screen.getByText("数据准备状态")).toBeTruthy();
    expect(screen.getByText("orders.csv")).toBeTruthy();
    expect(screen.getByText("customers.csv")).toBeTruthy();
    expect(screen.getByText("marketing_spend.csv")).toBeTruthy();
    expect(screen.getAllByText("已导入").length).toBeGreaterThanOrEqual(3);

    const file = new File(["return_id,amount\n1,20"], "returns.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText("选择 CSV 或 Excel 文件"), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "上传 CSV / Excel" }));

    expect(await screen.findByText("returns.csv")).toBeTruthy();
    expect(uploadSource).toHaveBeenCalledWith("ws_1", file);
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
    fireEvent.click(screen.getByRole("button", { name: "Generate profile" }));

    expect(await screen.findByText("orders")).toBeTruthy();
    expect(createProfile).toHaveBeenCalledWith("ws_1");
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
    fireEvent.click(screen.getByRole("button", { name: "Draft semantic layer" }));

    expect(await screen.findByText("sum_revenue")).toBeTruthy();
    expect(screen.getByText(/orders.channel/)).toBeTruthy();
    expect(screen.getByText("customer")).toBeTruthy();
  });

  it("renders data settings sections with source profile semantic mode and safety details", async () => {
    vi.mocked(getWorkspaceSettings).mockResolvedValue({
      workspace_id: "ws_1",
      data_sources: {
        status: "ready",
        sources: [{ name: "orders.csv", source_type: "csv", imported_tables: ["orders"] }],
      },
      profile: {
        status: "ready",
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
        status_label: "Product/live mode is on",
        provider_features: { insight_drafting: true, sql_planning: true },
      },
      safety: {
        sql_review: "enabled",
        sensitive_field_blocking: "enabled",
        trace_available: "enabled",
        technical_details_policy: "collapsed_by_default",
      },
    });

    render(<DataSettings workspaceId="ws_1" />);

    expect(await screen.findByText("Data sources")).toBeTruthy();
    expect(screen.getByText("Field profile")).toBeTruthy();
    expect(screen.getByText("Semantic layer")).toBeTruthy();
    expect(screen.getByText("Product/live mode")).toBeTruthy();
    expect(screen.getByText("Safety and audit")).toBeTruthy();
    expect(screen.getByText("orders.csv")).toBeTruthy();
    expect(screen.getByText("orders")).toBeTruthy();
    expect(screen.getByText("10 rows")).toBeTruthy();
    expect(screen.getByText("revenue")).toBeTruthy();
    expect(screen.getByText("sum_revenue")).toBeTruthy();
    expect(screen.getAllByText("channel").length).toBeGreaterThan(0);
    expect(screen.getByText("Product/live mode is on")).toBeTruthy();
    expect(screen.getByText("SQL review enabled")).toBeTruthy();
    expect(screen.getByText("Trace available")).toBeTruthy();
  });

  it("renders the settings page route", async () => {
    vi.mocked(getWorkspaceSettings).mockResolvedValue({
      workspace_id: "ws_1",
      data_sources: { status: "empty", sources: [] },
      profile: { status: "missing", tables: [] },
      semantic_layer: { status: "missing", metrics: [], dimensions: [], entities: [], time_fields: [] },
      model_mode: {
        product_live_mode: false,
        status_label: "Product/live mode is off",
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
    expect(await screen.findByText("Data sources")).toBeTruthy();
  });

  it("submits analysis questions and stores the run result for the detail page", async () => {
    vi.mocked(runAnalysis).mockResolvedValue({
      success: true,
      workspace_id: "ws_1",
      run_id: "run_1",
      result: {
        product_result: {
          version: "p13.v1",
          status: "completed",
          question_thread: {
            original_question: "哪个渠道收入最高？",
            system_understanding: "按渠道比较收入",
            resolved_question: "比较各渠道收入并给出建议。",
          },
          business_answer: {
            headline: "Email produced the most revenue.",
            summary: "Email 贡献最高收入。",
            next_actions: ["复核 email 投放预算"],
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
    expect(screen.getByText("measure")).toBeTruthy();
  });

  it("renders the integrated analysis thread in one compact card", () => {
    render(
      <RunResult
        result={{
          product_result: {
            version: "p13.v1",
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
              summary: "paid_search 收入最高。",
              next_actions: ["提高预算"],
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
            version: "p13.v1",
            status: "completed",
            question_thread: { original_question: "看收入" },
            business_answer: { headline: "收入稳定", summary: "收入保持稳定。", confidence: "medium" },
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

  it("submits only the clarification answer for a pending run", async () => {
    vi.mocked(runAnalysis)
      .mockResolvedValueOnce({
        success: true,
        workspace_id: "ws_1",
        run_id: "run_pending",
        result: {
          product_result: {
            version: "p13.v1",
            status: "waiting_for_clarification",
            question_thread: {
              pending_run_id: "pending_1",
              original_question: "帮我分析渠道表现",
              system_understanding: "需要按渠道比较表现",
              clarification_question: "你希望分析哪个时间范围？",
              status: "waiting_for_clarification",
            },
            business_answer: {},
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
            version: "p13.v1",
            status: "completed",
            question_thread: {
              original_question: "帮我分析渠道表现",
              clarification_question: "你希望分析哪个时间范围？",
              clarification_answer: "最近 90 天",
              resolved_question: "分析最近 90 天各渠道表现。",
            },
            business_answer: {
              headline: "paid_search 表现最好",
              summary: "收入最高。",
              next_actions: [],
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
    expect(await screen.findByText("用户补充")).toBeTruthy();
    expect(screen.getByText("整理后")).toBeTruthy();
    expect(await screen.findByText("paid_search 表现最好")).toBeTruthy();
  });

  it("renders the business answer before evidence and technical details", () => {
    const { container } = render(
      <RunResult
        result={{
          product_result: {
            version: "p13.v1",
            status: "completed",
            question_thread: { original_question: "分析渠道" },
            business_answer: { headline: "先看业务结论", summary: "这是业务摘要。", confidence: "medium" },
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
    expect(image.getAttribute("src")).toBe("/api/workspaces/ws_1/artifacts/runs/run_1/charts/channel.png");
    expect(screen.getByText("付费搜索贡献最高。")).toBeTruthy();
    expect(screen.queryByText("runs/run_1/charts/channel.png")).toBeNull();
  });

  it("shows an empty chart gallery state when no artifacts exist", () => {
    render(<ChartArtifactGallery artifacts={[]} />);

    expect(screen.getByText("暂无图表")).toBeTruthy();
  });

  it("shows a business-friendly quality warning for raw parameter dump flags", () => {
    render(
      <RunResult
        result={{
          product_result: {
            version: "p13.v1",
            status: "completed",
            question_thread: { original_question: "分析渠道" },
            business_answer: {
              headline: "查询已完成",
              summary: "已完成查询。",
              confidence: "low",
              quality_flags: ["raw_parameter_dump_detected"],
            },
            evidence: { table_preview: { columns: [], rows: [] } },
            chart_artifacts: [],
            technical_details: { raw_rows: [["channel=paid_search, revenue=200"]] },
          },
        }}
      />,
    );

    expect(screen.getByText("回答已自动过滤技术参数，建议结合证据表补充业务解读。")).toBeTruthy();
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
            summary: "Paid search led revenue.",
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
    expect(screen.getByText("Paid search led revenue.")).toBeTruthy();
    expect(screen.getByText("Rows preview came from workspace data.")).toBeTruthy();
    expect(screen.getByText("图表或附件")).toBeTruthy();
    expect(screen.getByText("Revenue by Channel 图表已生成")).toBeTruthy();
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
        sections: [{ section_id: "summary", title: "收入概览", status: "completed", summary: "收入保持增长。" }],
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
                { section_id: "done", title: "Done", status: "completed", summary: "Done." },
                { section_id: "failed", title: "Failed", status: "failed", error: "Failed." },
              ]
            : [
                {
                  section_id: "section",
                  title: "Section",
                  status: status === "completed" ? "completed" : status === "running" ? "running" : "failed",
                  summary: status === "completed" ? "Done." : "",
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
