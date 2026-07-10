import Link from "next/link";
import React from "react";
import ModelModePill from "./ModelModePill";

export type ProductShellActive = "prepare" | "analysis" | "reports" | "settings";

export type ProductShellProps = {
  workspaceId: string;
  active: ProductShellActive;
  children: React.ReactNode;
};

const PRIMARY_NAV: Array<{
  key: Exclude<ProductShellActive, "settings">;
  label: string;
  glyph: string;
  path: "datasets" | "analysis" | "reports";
}> = [
  { key: "prepare", label: "数据准备", glyph: "数", path: "datasets" },
  { key: "analysis", label: "分析", glyph: "析", path: "analysis" },
  { key: "reports", label: "报告", glyph: "报", path: "reports" },
];

const ACTIVE_LABELS: Record<ProductShellActive, string> = {
  prepare: "数据准备",
  analysis: "分析",
  reports: "报告",
  settings: "工作区设置",
};

function Brand() {
  return (
    <div className="decision-brand" aria-label="InsightFlow">
      <span className="decision-brand-mark" aria-hidden="true" />
      <div>
        <strong>InsightFlow</strong>
        <span>把数据变成下一步行动</span>
      </div>
    </div>
  );
}

type PrimaryNavigationProps = Pick<ProductShellProps, "workspaceId" | "active"> & { mobile?: boolean };

function PrimaryNavigation({ workspaceId, active, mobile = false }: PrimaryNavigationProps) {
  return (
    <nav className={mobile ? "decision-bottom-nav" : "decision-primary-nav"} aria-label={mobile ? "移动端产品导航" : "产品导航"}>
      {PRIMARY_NAV.map((item) => {
        const isActive = item.key === active;
        return (
          <Link
            aria-current={isActive ? "page" : undefined}
            className={mobile ? "decision-bottom-link" : "decision-nav-link"}
            href={`/workspaces/${workspaceId}/${item.path}`}
            key={item.key}
          >
            {!mobile ? <span className="decision-nav-glyph" aria-hidden="true">{item.glyph}</span> : null}
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export default function ProductShell({ workspaceId, active, children }: ProductShellProps) {
  const settingsHref = `/workspaces/${workspaceId}/settings`;

  return (
    <div className="decision-app-shell">
      <a className="decision-skip-link" href="#main-content">
        跳到主要内容
      </a>
      <aside className="decision-sidebar">
        <Brand />
        <Link className="decision-mobile-settings" href={settingsHref} aria-label="打开工作区设置">
          <span aria-hidden="true">⚙</span>
        </Link>

        <section className="decision-workspace-card" aria-label="当前工作区">
          <small>当前工作区</small>
          <strong title={workspaceId}>{workspaceId}</strong>
          <span><i aria-hidden="true" />数据状态已连接</span>
        </section>

        <PrimaryNavigation workspaceId={workspaceId} active={active} />

        <div className="decision-sidebar-footer">
          <Link aria-current={active === "settings" ? "page" : undefined} href={settingsHref}>
            <span aria-hidden="true">⚙</span>
            <span>工作区设置</span>
          </Link>
          <Link href="/workspaces">
            <span aria-hidden="true">↗</span>
            <span>返回工作区列表</span>
          </Link>
        </div>
      </aside>

      <div className="decision-main-shell">
        <header className="decision-topbar">
          <div className="decision-breadcrumb">
            <span>工作区</span>
            <span aria-hidden="true">/</span>
            <strong>{ACTIVE_LABELS[active]}</strong>
          </div>
          <div className="decision-top-actions">
            <ModelModePill workspaceId={workspaceId} />
            <Link className="decision-settings-link" href={settingsHref} aria-label="打开工作区设置">
              <span className="decision-settings-glyph" aria-hidden="true">⚙</span>
              <span>工作区设置</span>
            </Link>
          </div>
        </header>

        <main className="decision-content" id="main-content">
          {children}
        </main>
      </div>

      <PrimaryNavigation workspaceId={workspaceId} active={active} mobile />
    </div>
  );
}
