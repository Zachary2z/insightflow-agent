import React from "react";

export type StatusPillProps = React.HTMLAttributes<HTMLSpanElement> & {
  children: React.ReactNode;
  tone?: "green" | "orange" | "red" | "blue" | "neutral";
};

export function StatusPill({ children, tone = "green", className = "", ...spanProps }: StatusPillProps) {
  return (
    <span {...spanProps} className={[`status-pill status-pill-${tone}`, className].filter(Boolean).join(" ")}>
      <span className="status-dot" aria-hidden="true" />
      {children}
    </span>
  );
}

export default StatusPill;
