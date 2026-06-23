"use client";

import Link from "next/link";
import React, { FormEvent, useState } from "react";
import { runAnalysis, type WorkspaceRunResponse } from "../lib/api";
import RunResult from "./RunResult";

type AnalysisRunnerProps = {
  workspaceId: string;
};

export default function AnalysisRunner({ workspaceId }: AnalysisRunnerProps) {
  const [question, setQuestion] = useState("");
  const [initialSql, setInitialSql] = useState("");
  const [run, setRun] = useState<WorkspaceRunResponse | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) {
      setError("Question is required.");
      return;
    }
    try {
      setIsRunning(true);
      setError("");
      const response = await runAnalysis(workspaceId, {
        userQuestion: question.trim(),
        initialSql,
      });
      setRun(response);
      if (response.run_id) {
        window.sessionStorage.setItem(`insightflow.run.${workspaceId}.${response.run_id}`, JSON.stringify(response));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run analysis");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <section className="stack">
      <article className="panel">
        <h2>Analysis Question</h2>
        <form className="form-grid" onSubmit={handleSubmit}>
          <label htmlFor="analysis-question">Question</label>
          <textarea
            id="analysis-question"
            rows={4}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Which channel has the strongest revenue trend?"
          />
          <label htmlFor="initial-sql">Initial SQL</label>
          <textarea
            id="initial-sql"
            rows={3}
            value={initialSql}
            onChange={(event) => setInitialSql(event.target.value)}
            placeholder="Optional reviewed starting SQL"
          />
          <button type="submit" disabled={isRunning}>
            {isRunning ? "Running..." : "Run analysis"}
          </button>
        </form>
      </article>
      {error ? <p role="alert">{error}</p> : null}
      {run ? (
        <article className="panel">
          <h2>Run Summary</h2>
          <p>Status: {run.success ? "completed" : "failed"}</p>
          {run.run_id ? <p>Run ID: {run.run_id}</p> : null}
          <RunResult result={run.result} />
          {run.run_id ? (
            <Link className="button" href={`/workspaces/${workspaceId}/runs/${run.run_id}`}>
              Open run result
            </Link>
          ) : null}
        </article>
      ) : null}
    </section>
  );
}
