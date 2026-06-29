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
        <h2>分析结果</h2>
        <p>当前浏览器会话没有缓存这次分析结果。请回到分析工作台重新打开最近一次分析。</p>
      </section>
    );
  }

  return <RunResult result={result} />;
}
