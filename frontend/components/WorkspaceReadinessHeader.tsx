import React from "react";

type WorkspaceReadinessHeaderProps = {
  workspaceId: string;
  workspaceName?: string;
};

function StatusPill({ label, value }: { label: string; value: string }) {
  return (
    <span className="readiness-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </span>
  );
}

export default function WorkspaceReadinessHeader({
  workspaceId,
  workspaceName,
}: WorkspaceReadinessHeaderProps) {
  return (
    <article className="panel workbench-header" aria-label="工作区状态">
      <div>
        <p className="eyebrow">Analysis Workbench</p>
        <h2>{workspaceName || `工作区 ${workspaceId}`}</h2>
      </div>
      <div className="readiness-grid">
        <StatusPill label="数据" value="就绪状态待同步" />
        <StatusPill label="Profile" value="可生成" />
        <StatusPill label="Semantic" value="可草拟" />
        <StatusPill label="模式" value="Product / Live" />
      </div>
    </article>
  );
}
