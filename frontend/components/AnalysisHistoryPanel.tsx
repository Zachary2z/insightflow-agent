import React from "react";
import type { WorkspaceRunSummary } from "../lib/api";

type AnalysisHistoryPanelProps = {
  runs: WorkspaceRunSummary[];
  selectedRunId?: string | null;
  isLoading: boolean;
  error: string;
  onSelectRun: (run: WorkspaceRunSummary) => void;
};

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    completed: "已完成",
    failed: "失败",
    queued: "排队中",
    waiting_for_clarification: "等待补充",
    running: "分析中",
  };
  return labels[status] ?? status;
}

function statusClass(status: string) {
  if (status === "completed") {
    return "history-status-completed";
  }
  if (status === "failed") {
    return "history-status-failed";
  }
  if (status === "waiting_for_clarification") {
    return "history-status-waiting";
  }
  return "history-status-running";
}

function safeSummary(run: WorkspaceRunSummary) {
  const text = run.status === "failed" ? run.failure_reason || run.headline : run.headline || run.failure_reason;
  const trimmed = text?.trim() || "";
  if (/unknown (table|column)|no such (table|column)|trace|select\s+/i.test(trimmed)) {
    return "本轮分析未能执行，请打开详情查看技术信息。";
  }
  return trimmed || "暂无摘要";
}

function summaryLabel(run: WorkspaceRunSummary) {
  return run.status === "failed" ? "原因" : "摘要";
}

function displayTime(run: WorkspaceRunSummary) {
  const timestamp = run.saved_at || run.created_at;
  if (!timestamp) {
    return "时间未知";
  }
  return timestamp.replace("T", " ").replace(/\.\d+Z?$/, "Z").replace(/Z$/, "");
}

export default function AnalysisHistoryPanel({
  runs,
  selectedRunId,
  isLoading,
  error,
  onSelectRun,
}: AnalysisHistoryPanelProps) {
  return (
    <aside className="product-card analysis-history-panel" aria-label="历史分析">
      <div className="section-heading">
        <div>
          <p className="product-eyebrow">History</p>
          <h2>历史分析</h2>
          <p className="product-lead">历史来自工作区已保存的分析 run，可点击恢复完整结果。</p>
        </div>
      </div>
      {isLoading ? <p role="status">正在加载历史分析</p> : null}
      {error ? <p role="alert">历史分析加载失败：{error}</p> : null}
      {!isLoading && !error && runs.length === 0 ? (
        <p className="history-empty">还没有历史分析。开始提问后会保存在这里。</p>
      ) : null}
      {!error && runs.length > 0 ? (
        <div className="history-list">
          {runs.map((run) => {
            const isSelected = run.run_id === selectedRunId;
            return (
              <button
                className={`history-card${isSelected ? " selected" : ""}`}
                type="button"
                key={run.run_id}
                aria-current={isSelected ? "true" : undefined}
                onClick={() => onSelectRun(run)}
              >
                <span className="history-card-topline">
                  <span className={`history-status ${statusClass(run.status)}`}>{statusLabel(run.status)}</span>
                  <span className="history-time">{displayTime(run)}</span>
                </span>
                <span className="history-question">{run.question || "未记录问题"}</span>
                <span className="history-summary">
                  {summaryLabel(run)}：{safeSummary(run)}
                </span>
                <span className="history-meta-row">
                  <span>{run.has_chart ? "有图表" : "无图表"}</span>
                  {run.requires_clarification ? <span>等待补充</span> : null}
                </span>
              </button>
            );
          })}
        </div>
      ) : null}
    </aside>
  );
}
