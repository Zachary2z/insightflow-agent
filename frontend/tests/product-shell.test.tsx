import React from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ProductShell from "../components/ProductShell";

function mockWorkspaceSettings(modelMode: Record<string, unknown>) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      workspace_id: "ws_1",
      model_mode: modelMode,
    }),
  } as Response);
}

describe("ProductShell", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders the shared InsightFlow product chrome and active Chinese navigation", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}) as Promise<Response>);

    render(
      <ProductShell workspaceId="ws_revenue" active="analysis">
        <p>页面内容</p>
      </ProductShell>,
    );

    expect(screen.getByText("InsightFlow")).toBeTruthy();
    expect(screen.getByText("通用业务数据分析工作台")).toBeTruthy();
    expect(screen.getByText("ws_revenue")).toBeTruthy();
    expect(screen.getByText("模型状态检查中")).toBeTruthy();

    const navigation = screen.getByRole("navigation", { name: "产品导航" });
    expect(within(navigation).getByRole("link", { name: /数据源管理/ }).getAttribute("href")).toBe(
      "/workspaces/ws_revenue/datasets",
    );
    expect(within(navigation).getByRole("link", { name: /分析工作台/ }).getAttribute("href")).toBe(
      "/workspaces/ws_revenue/analysis",
    );
    expect(within(navigation).getByRole("link", { name: /报告中心/ }).getAttribute("href")).toBe(
      "/workspaces/ws_revenue/reports",
    );
    expect(within(navigation).getByRole("link", { name: /数据设置/ }).getAttribute("href")).toBe(
      "/workspaces/ws_revenue/settings",
    );
    expect(within(navigation).getByRole("link", { name: /业务问答/ }).getAttribute("href")).toBe(
      "/workspaces/ws_revenue/business-qa",
    );

    expect(within(navigation).getByRole("link", { name: /分析工作台/ }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(screen.getByText("页面内容")).toBeTruthy();
  });

  it("does not show a live model status when only the api key is configured", async () => {
    mockWorkspaceSettings({
      product_live_mode: false,
      provider: { name: "DeepSeek", model: "deepseek-v4-flash", api_key_present: true },
      provider_features: {},
    });

    render(
      <ProductShell workspaceId="ws_key_only" active="analysis">
        <p>页面内容</p>
      </ProductShell>,
    );

    expect(await screen.findByText("仅已配置密钥")).toBeTruthy();
    expect(screen.queryByText("真实模型已开启")).toBeNull();
  });

  it("shows live model mode only when product live mode is enabled", async () => {
    mockWorkspaceSettings({
      product_live_mode: true,
      provider: { name: "DeepSeek", model: "deepseek-v4-flash", api_key_present: true },
      provider_features: {
        question_understanding: true,
        sql_planning: true,
      },
    });

    render(
      <ProductShell workspaceId="ws_live" active="analysis">
        <p>页面内容</p>
      </ProductShell>,
    );

    expect(await screen.findByText("真实模型已开启")).toBeTruthy();
    expect(screen.queryByText("仅已配置密钥")).toBeNull();
  });

  it("shows an unknown model status when workspace settings cannot load", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("backend unavailable"));

    render(
      <ProductShell workspaceId="ws_error" active="analysis">
        <p>页面内容</p>
      </ProductShell>,
    );

    expect(await screen.findByText("模型状态未知")).toBeTruthy();
    expect(screen.queryByText("真实模型已开启")).toBeNull();
  });

  it("marks the business Q&A preview navigation item active", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}) as Promise<Response>);

    render(
      <ProductShell workspaceId="ws_1" active="business-qa">
        <p>业务问答内容</p>
      </ProductShell>,
    );

    const navigation = screen.getByRole("navigation", { name: "产品导航" });
    expect(within(navigation).getByRole("link", { name: /业务问答/ }).getAttribute("href")).toBe(
      "/workspaces/ws_1/business-qa",
    );
    expect(within(navigation).getByRole("link", { name: /业务问答/ }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(within(navigation).getByRole("link", { name: /分析工作台/ }).getAttribute("aria-current")).toBeNull();
  });
});
