import React from "react";
import { StatusPill } from "./ProductStatus";

type WorkspaceReadinessHeaderProps = {
  workspaceId: string;
  workspaceName?: string;
};

function ReadinessMetric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className={`workbench-metric ${tone}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

export default function WorkspaceReadinessHeader({
  workspaceId,
  workspaceName,
}: WorkspaceReadinessHeaderProps) {
  return (
    <article className="product-card workbench-readiness-card" aria-label="工作区状态">
      <div className="section-heading">
        <div>
          <p className="product-eyebrow">Current Workspace</p>
          <h2>{workspaceName || `工作区 ${workspaceId}`}</h2>
          <p className="product-lead">数据源、字段画像和语义层准备好后，可以直接进入业务分析流程。</p>
        </div>
        <StatusPill tone="green">可分析</StatusPill>
      </div>
      <div className="workbench-metric-grid">
        <ReadinessMetric label="数据源" value="已连接" tone="blue" />
        <ReadinessMetric label="字段画像" value="可生成" tone="green" />
        <ReadinessMetric label="语义层" value="可草拟" tone="orange" />
      </div>
    </article>
  );
}
