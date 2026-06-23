import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AnalysisRunner from "../components/AnalysisRunner";
import DatasetManager from "../components/DatasetManager";
import ProfileSummary from "../components/ProfileSummary";
import ProfileWorkspace from "../components/ProfileWorkspace";
import RunResult from "../components/RunResult";
import SemanticLayerWorkspace from "../components/SemanticLayerWorkspace";
import WorkspaceList from "../components/WorkspaceList";
import WorkspaceNewForm from "../components/WorkspaceNewForm";

vi.mock("../lib/api", () => ({
  createProfile: vi.fn(),
  createSemanticDraft: vi.fn(),
  createWorkspace: vi.fn(),
  importSqliteSource: vi.fn(),
  listSources: vi.fn(),
  listWorkspaces: vi.fn(),
  runAnalysis: vi.fn(),
  uploadSource: vi.fn(),
}));

import {
  createProfile,
  createSemanticDraft,
  createWorkspace,
  importSqliteSource,
  listSources,
  listWorkspaces,
  runAnalysis,
  uploadSource,
} from "../lib/api";

describe("workspace product components", () => {
  afterEach(() => {
    vi.clearAllMocks();
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

  it("uploads files, imports SQLite, and renders source metadata", async () => {
    vi.mocked(listSources)
      .mockResolvedValueOnce({ sources: [] })
      .mockResolvedValueOnce({
        sources: [{ source_id: "src_1", source_type: "csv", name: "orders.csv", imported_tables: ["orders"] }],
      })
      .mockResolvedValueOnce({
        sources: [
          { source_id: "src_1", source_type: "csv", name: "orders.csv", imported_tables: ["orders"] },
          { source_id: "src_2", source_type: "sqlite", name: "ops.db", imported_tables: ["invoices"] },
        ],
      });
    vi.mocked(uploadSource).mockResolvedValue({ success: true, imported_tables: ["orders"] });
    vi.mocked(importSqliteSource).mockResolvedValue({ success: true, imported_tables: ["invoices"] });

    render(<DatasetManager workspaceId="ws_1" />);

    const file = new File(["order_id,revenue\n1,100"], "orders.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText("CSV or Excel file"), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Upload source" }));

    expect(await screen.findByText("orders.csv")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("SQLite file path"), { target: { value: "/tmp/ops.db" } });
    fireEvent.click(screen.getByRole("button", { name: "Import SQLite" }));

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

  it("submits analysis questions and stores the run result for the detail page", async () => {
    vi.mocked(runAnalysis).mockResolvedValue({
      success: true,
      workspace_id: "ws_1",
      run_id: "run_1",
      result: { final_answer: "Email produced the most revenue.", generated_sql: "SELECT 1" },
    });

    render(<AnalysisRunner workspaceId="ws_1" />);
    fireEvent.change(screen.getByLabelText("Question"), {
      target: { value: "Which channel has the most revenue?" },
    });
    fireEvent.change(screen.getByLabelText("Initial SQL"), { target: { value: "SELECT 1" } });
    fireEvent.click(screen.getByRole("button", { name: "Run analysis" }));

    expect(await screen.findByText("Email produced the most revenue.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open run result" }).getAttribute("href")).toBe(
      "/workspaces/ws_1/runs/run_1",
    );
    expect(JSON.parse(window.sessionStorage.getItem("insightflow.run.ws_1.run_1") ?? "{}").result.final_answer).toBe(
      "Email produced the most revenue.",
    );
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

  it("renders SQL and execution rows for a run result", () => {
    render(
      <RunResult
        result={{
          final_answer: "Email leads revenue.",
          generated_sql: "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
          execution_result: { columns: ["channel", "revenue"], rows: [["email", 100]] },
          chart_path: "workspaces/ws_1/runs/run_1/charts/revenue.png",
          trace_path: "workspaces/ws_1/runs/run_1/trace.json",
        }}
      />,
    );
    expect(screen.getByText("Email leads revenue.")).toBeTruthy();
    expect(screen.getByText(/SELECT channel/)).toBeTruthy();
    expect(screen.getByText("email")).toBeTruthy();
    expect(screen.getByText(/revenue.png/)).toBeTruthy();
    expect(screen.getByText(/trace.json/)).toBeTruthy();
  });
});
