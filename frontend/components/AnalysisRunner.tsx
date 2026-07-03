"use client";

import Link from "next/link";
import React, { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  getWorkspaceRun,
  listWorkspaceRuns,
  runAnalysis,
  type QuestionThread,
  type WorkspaceRunResponse,
  type WorkspaceRunSummary,
} from "../lib/api";
import AnalysisHistoryPanel from "./AnalysisHistoryPanel";
import RunResult from "./RunResult";
import WorkspaceReadinessHeader from "./WorkspaceReadinessHeader";

type AnalysisRunnerProps = {
  workspaceId: string;
};

type ContinuePayload = {
  pendingRunId: string;
  clarificationAnswer: string;
};

type FollowUpPayload = {
  followUpQuestion: string;
  thread: QuestionThread;
};

type CacheCandidate = {
  matchedRunId: string;
  message: string;
};

const POLL_INTERVAL_MS = 1500;

function activeRunStorageKey(workspaceId: string) {
  return `insightflow.activeRun.${workspaceId}`;
}

function responseStatus(run: WorkspaceRunResponse | null) {
  if (!run) {
    return "";
  }
  const resultStatus = typeof run.result?.status === "string" ? run.result.status : "";
  return String(run.status || run.product_result?.status || resultStatus || "");
}

function isActiveRunStatus(status: string) {
  return status === "queued" || status === "running";
}

function taskQuestion(run: WorkspaceRunResponse | null) {
  if (!run) {
    return "";
  }
  const resultQuestion = typeof run.result?.original_question === "string" ? run.result.original_question : "";
  return run.product_result?.question_thread?.original_question || resultQuestion || "未记录问题";
}

function taskStatusLabel(status: string) {
  const labels: Record<string, string> = {
    queued: "排队中",
    running: "正在分析",
    waiting_for_clarification: "等待补充",
    completed: "已完成",
    failed: "失败",
  };
  return labels[status] ?? (status || "状态未知");
}

function taskProgressText(run: WorkspaceRunResponse | null) {
  if (!run) {
    return "正在准备分析";
  }
  const status = responseStatus(run);
  const steps = run.product_result?.progress_steps ?? [];
  const runningStep = steps.find((step) => step.status === "running");
  if (runningStep?.summary) {
    return runningStep.summary;
  }
  if (status === "queued") {
    return "正在准备分析";
  }
  if (status === "waiting_for_clarification") {
    return "等待补充分析条件";
  }
  if (status === "completed") {
    return run.product_result?.business_answer?.direct_answer || run.product_result?.business_answer?.headline || "已完成";
  }
  if (status === "failed") {
    return run.product_result?.business_answer?.direct_answer || "本轮分析失败";
  }
  return steps[0]?.summary || "正在处理";
}

function shouldRenderCompactTask(run: WorkspaceRunResponse | null) {
  return isActiveRunStatus(responseStatus(run));
}

function RunTaskCard({ run, workspaceId }: { run: WorkspaceRunResponse; workspaceId: string }) {
  const runId = runIdForDisplay(run);
  const status = responseStatus(run);
  const href = runId ? `/workspaces/${workspaceId}/runs/${runId}` : `/workspaces/${workspaceId}/analysis`;
  return (
    <Link className="run-task-card" aria-label="当前分析任务" href={href}>
      <span className="run-task-row">
        <span className="run-task-label">问题</span>
        <span className="run-task-question">{taskQuestion(run)}</span>
      </span>
      <span className="run-task-meta">
        <span className={`history-status ${status === "failed" ? "history-status-failed" : "history-status-running"}`}>
          {taskStatusLabel(status)}
        </span>
        <span className="run-task-progress">进度：{taskProgressText(run)}</span>
      </span>
    </Link>
  );
}

function resultForDisplay(run: WorkspaceRunResponse): Record<string, unknown> {
  if (run.product_result) {
    return { ...run.result, product_result: run.product_result };
  }
  return run.result;
}

function buildFollowUpQuestion(thread: QuestionThread, followUpQuestion: string) {
  const previousQuestion = thread.resolved_question || thread.original_question || "";
  const originalQuestion = thread.original_question && thread.original_question !== previousQuestion ? thread.original_question : "";
  return [
    "基于上一轮分析继续追问。",
    originalQuestion ? `上一轮用户问题：${originalQuestion}` : "",
    previousQuestion ? `上一轮整理后问题：${previousQuestion}` : "",
    `本轮追问：${followUpQuestion}`,
    "请结合同一工作区数据继续分析，并给出业务结论、证据和必要图表。",
  ]
    .filter(Boolean)
    .join("。");
}

function runIdForDisplay(run: WorkspaceRunResponse | null) {
  if (!run) {
    return null;
  }
  if (run.run_id) {
    return run.run_id;
  }
  if (run.product_result?.run_id) {
    return run.product_result.run_id;
  }
  const productResult = run.result.product_result;
  if (productResult && typeof productResult === "object" && "run_id" in productResult) {
    const candidate = (productResult as { run_id?: unknown }).run_id;
    return typeof candidate === "string" ? candidate : null;
  }
  return null;
}

function cacheCandidateFromResponse(response: WorkspaceRunResponse): CacheCandidate | null {
  if (response.status !== "cache_candidate" || !response.matched_run_id) {
    return null;
  }
  return {
    matchedRunId: response.matched_run_id,
    message: response.message || "已找到同一数据版本下的历史分析",
  };
}

export default function AnalysisRunner({ workspaceId }: AnalysisRunnerProps) {
  const [question, setQuestion] = useState("");
  const [initialSql, setInitialSql] = useState("");
  const [run, setRun] = useState<WorkspaceRunResponse | null>(null);
  const [cacheCandidate, setCacheCandidate] = useState<CacheCandidate | null>(null);
  const [historyRuns, setHistoryRuns] = useState<WorkspaceRunSummary[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isContinuing, setIsContinuing] = useState(false);
  const [error, setError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [continuationError, setContinuationError] = useState("");
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refreshHistory = useCallback(async () => {
    try {
      setIsHistoryLoading(true);
      setHistoryError("");
      const response = await listWorkspaceRuns(workspaceId);
      setHistoryRuns(response.runs ?? []);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "无法加载历史分析");
    } finally {
      setIsHistoryLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory]);

  const clearPollTimer = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  function cacheRun(response: WorkspaceRunResponse) {
    if (response.run_id) {
      window.sessionStorage.setItem(`insightflow.run.${workspaceId}.${response.run_id}`, JSON.stringify(response));
    }
  }

  const rememberActiveRun = useCallback(
    (response: WorkspaceRunResponse) => {
      const runId = runIdForDisplay(response);
      if (runId && isActiveRunStatus(responseStatus(response))) {
        window.sessionStorage.setItem(activeRunStorageKey(workspaceId), runId);
      }
    },
    [workspaceId],
  );

  const clearActiveRun = useCallback(() => {
    window.sessionStorage.removeItem(activeRunStorageKey(workspaceId));
  }, [workspaceId]);

  const pollRun = useCallback(
    async (runId: string) => {
      clearPollTimer();
      try {
        const latest = await getWorkspaceRun(workspaceId, runId);
        if (!latest || typeof latest !== "object") {
          throw new Error("无法恢复分析任务");
        }
        setRun(latest);
        cacheRun(latest);
        if (isActiveRunStatus(responseStatus(latest))) {
          rememberActiveRun(latest);
          pollTimerRef.current = setTimeout(() => {
            void pollRun(runId);
          }, POLL_INTERVAL_MS);
          return;
        }
        clearActiveRun();
        await refreshHistory();
      } catch (err) {
        setHistoryError(err instanceof Error ? err.message : "无法恢复分析任务");
      }
    },
    [clearActiveRun, clearPollTimer, refreshHistory, rememberActiveRun, workspaceId],
  );

  useEffect(() => {
    const activeRunId = window.sessionStorage.getItem(activeRunStorageKey(workspaceId));
    if (activeRunId) {
      void pollRun(activeRunId);
    }
    return () => clearPollTimer();
  }, [clearPollTimer, pollRun, workspaceId]);

  function handleRunResponse(response: WorkspaceRunResponse) {
    setRun(response);
    cacheRun(response);
    if (isActiveRunStatus(responseStatus(response))) {
      rememberActiveRun(response);
      const runId = runIdForDisplay(response);
      if (runId) {
        void pollRun(runId);
      }
      return;
    }
    clearActiveRun();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) {
      setError("请输入一个业务问题。");
      return;
    }
    try {
      setIsRunning(true);
      setError("");
      setContinuationError("");
      const response = await runAnalysis(workspaceId, {
        userQuestion: question.trim(),
        initialSql,
      });
      const candidate = cacheCandidateFromResponse(response);
      if (candidate) {
        setCacheCandidate(candidate);
        setRun(null);
        return;
      }
      setCacheCandidate(null);
      handleRunResponse(response);
      await refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法发起分析");
    } finally {
      setIsRunning(false);
    }
  }

  async function handleContinue({ pendingRunId, clarificationAnswer }: ContinuePayload) {
    try {
      setIsContinuing(true);
      setContinuationError("");
      const response = await runAnalysis(workspaceId, {
        pendingRunId,
        clarificationAnswer,
      });
      setCacheCandidate(null);
      handleRunResponse(response);
      await refreshHistory();
    } catch (err) {
      setContinuationError(err instanceof Error ? err.message : "无法继续分析");
    } finally {
      setIsContinuing(false);
    }
  }

  async function handleFollowUp({ followUpQuestion, thread }: FollowUpPayload) {
    try {
      setIsContinuing(true);
      setContinuationError("");
      const contextualQuestion = buildFollowUpQuestion(thread, followUpQuestion);
      const response = await runAnalysis(workspaceId, {
        userQuestion: contextualQuestion,
      });
      setCacheCandidate(null);
      handleRunResponse(response);
      setQuestion(followUpQuestion);
      await refreshHistory();
    } catch (err) {
      setContinuationError(err instanceof Error ? err.message : "无法继续追问");
    } finally {
      setIsContinuing(false);
    }
  }

  async function handleSelectHistoryRun(historyRun: WorkspaceRunSummary) {
    try {
      setError("");
      setContinuationError("");
      const response = await getWorkspaceRun(workspaceId, historyRun.run_id);
      setCacheCandidate(null);
      setRun(response);
      cacheRun(response);
      if (isActiveRunStatus(responseStatus(response))) {
        rememberActiveRun(response);
        void pollRun(historyRun.run_id);
      }
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "无法打开历史分析");
    }
  }

  async function handleViewCacheCandidate() {
    if (!cacheCandidate) {
      return;
    }
    try {
      setError("");
      setContinuationError("");
      const response = await getWorkspaceRun(workspaceId, cacheCandidate.matchedRunId);
      setCacheCandidate(null);
      setRun(response);
      cacheRun(response);
      clearActiveRun();
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法打开历史分析");
    }
  }

  async function handleForceReanalysis() {
    if (!question.trim()) {
      setError("请输入一个业务问题。");
      return;
    }
    try {
      setIsRunning(true);
      setError("");
      setContinuationError("");
      const response = await runAnalysis(workspaceId, {
        userQuestion: question.trim(),
        initialSql,
        forceReanalysis: true,
      });
      setCacheCandidate(null);
      handleRunResponse(response);
      await refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法重新分析");
    } finally {
      setIsRunning(false);
    }
  }

  const selectedRunId = runIdForDisplay(run);

  return (
    <section className="analysis-workbench">
      <div className="workbench-local-heading">
        <p className="product-eyebrow">Analysis Workbench</p>
        <h2>分析工作台</h2>
      </div>
      <WorkspaceReadinessHeader workspaceId={workspaceId} />
      <div className="analysis-main-grid">
        <div className="analysis-primary-column">
          <article className="product-card question-panel">
            <div className="section-heading">
              <div>
                <p className="product-eyebrow">Ask</p>
                <h2>问一个业务问题</h2>
                <p className="product-lead">输入自然语言问题；如果缺少时间范围或口径，系统会在同一条分析线程里追问。</p>
              </div>
            </div>
            <form className="form-grid" onSubmit={handleSubmit}>
              <label htmlFor="analysis-question">业务问题</label>
              <textarea
                id="analysis-question"
                rows={4}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="例如：帮我分析最近 90 天哪个渠道应该加预算"
              />
              <details className="advanced-options">
                <summary>高级选项：SQL 起点</summary>
                <div className="advanced-options-body">
                  <label htmlFor="initial-sql">初始 SQL</label>
                  <textarea
                    id="initial-sql"
                    rows={3}
                    value={initialSql}
                    onChange={(event) => setInitialSql(event.target.value)}
                    placeholder="可选：只在需要指定已审核 SQL 起点时填写"
                  />
                </div>
              </details>
              <button type="submit" disabled={isRunning}>
                {isRunning ? "分析中..." : "开始分析"}
              </button>
            </form>
          </article>
          {error ? <p role="alert">{error}</p> : null}
          {cacheCandidate ? (
            <article className="panel cache-candidate-panel" aria-label="历史分析复用提示">
              <div className="section-heading">
                <div>
                  <p className="product-eyebrow">History Match</p>
                  <h3>可复用历史分析</h3>
                  <p>{cacheCandidate.message}</p>
                </div>
              </div>
              <div className="button-row">
                <button type="button" onClick={handleViewCacheCandidate}>
                  查看历史结果
                </button>
                <button type="button" className="secondary-button" onClick={handleForceReanalysis} disabled={isRunning}>
                  {isRunning ? "重新分析中..." : "重新分析"}
                </button>
              </div>
            </article>
          ) : null}
          {run ? (
            <article className="run-shell">
              <div className="section-heading">
                <div>
                  <p className="product-eyebrow">Analysis Flow</p>
                  <h2>分析线程与结果</h2>
                </div>
                {selectedRunId ? <span className="status-chip">{selectedRunId}</span> : null}
              </div>
              {shouldRenderCompactTask(run) ? (
                <RunTaskCard run={run} workspaceId={workspaceId} />
              ) : (
                <RunResult
                  result={resultForDisplay(run)}
                  onContinueClarification={handleContinue}
                  onAskFollowUp={handleFollowUp}
                  isContinuing={isContinuing}
                  continuationError={continuationError}
                />
              )}
              {selectedRunId ? (
                <Link className="button secondary-button" href={`/workspaces/${workspaceId}/runs/${selectedRunId}`}>
                  查看本次分析详情
                </Link>
              ) : null}
            </article>
          ) : null}
        </div>
        <AnalysisHistoryPanel
          runs={historyRuns}
          selectedRunId={selectedRunId}
          isLoading={isHistoryLoading}
          error={historyError}
          onSelectRun={handleSelectHistoryRun}
        />
      </div>
    </section>
  );
}
