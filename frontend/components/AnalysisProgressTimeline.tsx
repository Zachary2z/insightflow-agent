import React from "react";
import type { ProgressStep } from "../lib/api";

type AnalysisProgressTimelineProps = {
  steps?: ProgressStep[];
};

const STATUS_LABELS: Record<ProgressStep["status"], string> = {
  pending: "待处理",
  running: "进行中",
  completed: "已完成",
  failed: "未完成",
  skipped: "已跳过",
};

function validStep(step: ProgressStep) {
  return Boolean(step.key?.trim() && step.label?.trim() && step.summary?.trim() && STATUS_LABELS[step.status]);
}

export default function AnalysisProgressTimeline({ steps = [] }: AnalysisProgressTimelineProps) {
  const visibleSteps = steps.filter(validStep);

  if (visibleSteps.length === 0) {
    return null;
  }

  return (
    <article className="panel progress-timeline" aria-label="分析进度">
      <div className="section-heading compact-heading">
        <div>
          <p className="product-eyebrow">Progress</p>
          <h3>分析进度</h3>
        </div>
      </div>
      <ol className="progress-step-list">
        {visibleSteps.map((step) => (
          <li className={`progress-step progress-step-${step.status}`} key={step.key}>
            <span className="progress-marker" aria-hidden="true" />
            <div className="progress-step-copy">
              <span className="progress-step-head">
                <strong>{step.label}</strong>
                <span>{STATUS_LABELS[step.status]}</span>
              </span>
              <p>{step.summary}</p>
            </div>
          </li>
        ))}
      </ol>
    </article>
  );
}
