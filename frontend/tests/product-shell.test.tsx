import React from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import ProductShell from "../components/ProductShell";

describe("ProductShell", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders the shared InsightFlow product chrome and active Chinese navigation", () => {
    render(
      <ProductShell workspaceId="ws_revenue" active="analysis">
        <p>页面内容</p>
      </ProductShell>,
    );

    expect(screen.getByText("InsightFlow")).toBeTruthy();
    expect(screen.getByText("通用业务数据分析工作台")).toBeTruthy();
    expect(screen.getByText("ws_revenue")).toBeTruthy();
    expect(screen.getByText("真实模型已开启")).toBeTruthy();

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

  it("marks the business Q&A preview navigation item active", () => {
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
