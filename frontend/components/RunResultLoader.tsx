"use client";

import React, { useEffect, useState } from "react";
import RunResult from "./RunResult";

type RunResultLoaderProps = {
  workspaceId: string;
  runId: string;
};

export default function RunResultLoader({ workspaceId, runId }: RunResultLoaderProps) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const stored = window.sessionStorage.getItem(`insightflow.run.${workspaceId}.${runId}`);
    if (!stored) {
      setResult(null);
      return;
    }
    try {
      const parsed = JSON.parse(stored) as { result?: Record<string, unknown> };
      setResult(parsed.result ?? parsed);
    } catch {
      setResult(null);
    }
  }, [workspaceId, runId]);

  if (!result) {
    return (
      <section className="panel">
        <h2>Run Result</h2>
        <p>This browser session does not have a cached result for this run.</p>
      </section>
    );
  }

  return <RunResult result={result} />;
}
