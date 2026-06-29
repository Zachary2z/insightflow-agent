"use client";

import Link from "next/link";
import React, { FormEvent, useState } from "react";
import { runAnalysis, type WorkspaceRunResponse } from "../lib/api";
import RunResult from "./RunResult";
import WorkspaceReadinessHeader from "./WorkspaceReadinessHeader";

type AnalysisRunnerProps = {
  workspaceId: string;
};

type ContinuePayload = {
  pendingRunId: string;
  clarificationAnswer: string;
};

function resultForDisplay(run: WorkspaceRunResponse): Record<string, unknown> {
  if (run.product_result) {
    return { ...run.result, product_result: run.product_result };
  }
  return run.result;
}

export default function AnalysisRunner({ workspaceId }: AnalysisRunnerProps) {
  const [question, setQuestion] = useState("");
  const [initialSql, setInitialSql] = useState("");
  const [run, setRun] = useState<WorkspaceRunResponse | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isContinuing, setIsContinuing] = useState(false);
  const [error, setError] = useState("");
  const [continuationError, setContinuationError] = useState("");

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
    } catch (err) {
      setContinuationError(err instanceof Error ? err.message : "无法继续分析");
    } finally {
      setIsContinuing(false);
    }
  }

  return (
    <section className="analysis-workbench">
      <div className="workbench-local-heading">
        <p className="product-eyebrow">Analysis Workbench</p>
        <h2>分析工作台</h2>
      </div>
      <WorkspaceReadinessHeader workspaceId={workspaceId} />
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
            {run.run_id ? <span className="status-chip">{run.run_id}</span> : null}
          </div>
          <RunResult
            result={resultForDisplay(run)}
            onContinueClarification={handleContinue}
            isContinuing={isContinuing}
            continuationError={continuationError}
          />
          {run.run_id ? (
            <Link className="button secondary-button" href={`/workspaces/${workspaceId}/runs/${run.run_id}`}>
              查看本次分析详情
            </Link>
          ) : null}
        </article>
      ) : null}
    </section>
  );
}
