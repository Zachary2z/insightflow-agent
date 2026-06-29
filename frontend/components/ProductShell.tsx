import Link from "next/link";
import React from "react";
import { StatusPill } from "./ProductStatus";

export type ProductShellActive = "sources" | "analysis" | "reports" | "settings" | "business-qa";

export type ProductShellProps = {
  workspaceId: string;
  active: ProductShellActive;
  children: React.ReactNode;
};

const NAV_ITEMS: Array<{
  key: ProductShellActive;
  label: string;
  index: string;
  path: "datasets" | "analysis" | "reports" | "settings";
}> = [
  { key: "sources", label: "数据源管理", index: "01", path: "datasets" },
  { key: "analysis", label: "分析工作台", index: "02", path: "analysis" },
  { key: "reports", label: "报告中心", index: "03", path: "reports" },
  { key: "settings", label: "数据设置", index: "04", path: "settings" },
  { key: "business-qa", label: "业务问答", index: "05", path: "analysis" },
];

export default function ProductShell({ workspaceId, active, children }: ProductShellProps) {
  return (
    <div className="product-shell">
      <header className="product-topbar">
        <div className="product-topbar-inner">
          <div className="product-brand" aria-label="InsightFlow">
            <div className="product-brand-mark" aria-hidden="true" />
            <div>
              <div className="product-brand-title">InsightFlow</div>
              <div className="product-brand-subtitle">通用业务数据分析工作台</div>
            </div>
          </div>
          <div className="product-topbar-meta">
            <div className="workspace-switcher">{workspaceId}</div>
            <StatusPill tone="green">真实模型已开启</StatusPill>
          </div>
        </div>
      </header>

      <main className="product-page">
        <nav className="product-nav" aria-label="产品导航">
          <div className="product-nav-title">工作区导航</div>
          <div className="product-nav-list">
            {NAV_ITEMS.map((item) => {
              const isActive = item.key === active;
              return (
                <Link
                  aria-current={isActive ? "page" : undefined}
                  className={isActive ? "product-nav-link active" : "product-nav-link"}
                  href={`/workspaces/${workspaceId}/${item.path}`}
                  key={item.key}
                >
                  <span>{item.label}</span>
                  <span aria-hidden="true">{item.index}</span>
                </Link>
              );
            })}
          </div>
        </nav>
        <div className="product-page-body">{children}</div>
      </main>
    </div>
  );
}
