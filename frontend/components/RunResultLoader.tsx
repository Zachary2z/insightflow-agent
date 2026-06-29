"use client";

import React, { useEffect, useState } from "react";
import { getWorkspaceRun, type WorkspaceRunResponse } from "../lib/api";
import RunResult from "./RunResult";

type RunResultLoaderProps = {
  workspaceId: string;
  runId: string;
};

function resultForDisplay(run: WorkspaceRunResponse): Record<string, unknown> {
  if (run.product_result) {
    return { ...run.result, product_result: run.product_result };
  }
  return run.result;
}

export default function RunResultLoader({ workspaceId, runId }: RunResultLoaderProps) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isActive = true;

    async function loadRunDetail() {
      try {
        setIsLoading(true);
        setError("");
        setResult(null);
        const response = await getWorkspaceRun(workspaceId, runId);
        if (isActive) {
          setResult(resultForDisplay(response));
        }
      } catch {
        if (isActive) {
          setError("无法加载分析详情");
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadRunDetail();

    return () => {
      isActive = false;
    };
  }, [workspaceId, runId]);

  if (isLoading) {
    return (
      <section className="panel">
        <h2>分析结果</h2>
        <p>正在加载分析详情</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel" role="alert">
        <h2>{error}</h2>
        <p>请回到分析工作台，从历史分析中重新打开这条记录。</p>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="panel">
        <h2>分析结果</h2>
        <p>这条分析记录暂时没有可展示的结果。</p>
      </section>
    );
  }

  return <RunResult result={result} />;
}
