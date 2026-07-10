import React, { type ReactNode } from "react";

type ProductEntryShellProps = {
  children: ReactNode;
  action?: ReactNode;
};

export default function ProductEntryShell({ children, action }: ProductEntryShellProps) {
  return (
    <div className="decision-entry-shell">
      <a className="decision-skip-link" href="#main-content">
        跳到主要内容
      </a>
      <header className="decision-entry-topbar">
        <div className="decision-entry-topbar-inner">
          <div className="decision-entry-brand" aria-label="InsightFlow">
            <span className="decision-brand-mark" aria-hidden="true" />
            <div>
              <strong>InsightFlow</strong>
              <span>把数据变成下一步行动</span>
            </div>
          </div>
          {action ? <div className="decision-entry-action">{action}</div> : null}
        </div>
      </header>
      <main className="decision-entry-main" id="main-content">{children}</main>
    </div>
  );
}
