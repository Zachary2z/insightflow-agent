import React, { type ReactNode } from "react";

type ProductEntryShellProps = {
  children: ReactNode;
  action?: ReactNode;
};

export default function ProductEntryShell({ children, action }: ProductEntryShellProps) {
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
          {action ? <div className="product-topbar-meta">{action}</div> : null}
        </div>
      </header>
      <main className="product-page">{children}</main>
    </div>
  );
}
