"use client";

import Link from "next/link";
import React, { FormEvent, useCallback, useEffect, useState } from "react";
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

export default function AnalysisRunner({ workspaceId }: AnalysisRunnerProps) {
  const [question, setQuestion] = useState("");
  const [initialSql, setInitialSql] = useState("");
  const [run, setRun] = useState<WorkspaceRunResponse | null>(null);
  const [historyRuns, setHistoryRuns] = useState<WorkspaceRunSummary[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isContinuing, setIsContinuing] = useState(false);
  const [error, setError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [continuationError, setContinuationError] = useState("");

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

  function cacheRun(response: WorkspaceRunResponse) {
    if (response.run_id) {
      window.sessionStorage.setItem(`insightflow.run.${workspaceId}.${response.run_id}`, JSON.stringify(response));
    }
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
      setRun(response);
      cacheRun(response);
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
      setRun(response);
      cacheRun(response);
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
      setRun(response);
      setQuestion(followUpQuestion);
      cacheRun(response);
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
      setRun(response);
      cacheRun(response);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "无法打开历史分析");
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
          {run ? (
            <article className="run-shell">
              <div className="section-heading">
                <div>
                  <p className="product-eyebrow">Analysis Flow</p>
                  <h2>分析线程与结果</h2>
                </div>
                {selectedRunId ? <span className="status-chip">{selectedRunId}</span> : null}
              </div>
              <RunResult
                result={resultForDisplay(run)}
                onContinueClarification={handleContinue}
                onAskFollowUp={handleFollowUp}
                isContinuing={isContinuing}
                continuationError={continuationError}
              />
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
