import React from "react";

export type StatusPillProps = {
  children: React.ReactNode;
  tone?: "green" | "orange" | "blue" | "neutral";
};

export function StatusPill({ children, tone = "green" }: StatusPillProps) {
  return (
    <span className={`status-pill status-pill-${tone}`}>
      <span className="status-dot" aria-hidden="true" />
      {children}
    </span>
  );
}

export default StatusPill;
