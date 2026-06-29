import React from "react";
import type { ProductAnalysisResult } from "../lib/api";
import AnalysisThreadCard from "./AnalysisThreadCard";
import BusinessAnswerCard from "./BusinessAnswerCard";
import ChartArtifactGallery from "./ChartArtifactGallery";
import EvidencePanel from "./EvidencePanel";
import TechnicalDetailsDisclosure from "./TechnicalDetailsDisclosure";

type ContinuePayload = {
  pendingRunId: string;
  clarificationAnswer: string;
};

type RunResultProps = {
  result: Record<string, unknown> | ProductAnalysisResult;
  onContinueClarification?: (payload: ContinuePayload) => Promise<void> | void;
  isContinuing?: boolean;
  continuationError?: string;
};

type ExecutionResult = {
  columns: string[];
  rows: Array<unknown[] | Record<string, unknown>>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function productResult(result: Record<string, unknown> | ProductAnalysisResult): ProductAnalysisResult | null {
  if (!isRecord(result)) {
    return null;
  }
  const record = result as Record<string, unknown>;
  if (isRecord(record.product_result)) {
    return record.product_result as ProductAnalysisResult;
  }
  if (record.question_thread || record.business_answer || record.technical_details) {
    return record as ProductAnalysisResult;
  }
  return null;
}

function stringField(result: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = result[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return "";
}

function listField(result: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = result[key];
    if (Array.isArray(value)) {
      return value.map((item) => String(item));
    }
    if (typeof value === "string" && value.trim()) {
      return [value];
    }
  }
  return [];
}

function executionResult(result: Record<string, unknown>): ExecutionResult | null {
  const candidate = result.execution_result;
  if (!isRecord(candidate)) {
    return null;
  }
  const rows = Array.isArray(candidate.rows) ? (candidate.rows as Array<unknown[] | Record<string, unknown>>) : [];
  const columns = Array.isArray(candidate.columns)
    ? candidate.columns.map((column) => String(column))
    : rows.length > 0 && isRecord(rows[0])
      ? Object.keys(rows[0])
      : [];
  return { columns, rows };
}

function fallbackProduct(result: Record<string, unknown>): ProductAnalysisResult {
  const execution = executionResult(result);
  const finalAnswer = stringField(result, ["final_answer", "answer", "summary", "error"]);
  const sql = stringField(result, ["generated_sql", "final_sql", "sql"]);
  const tracePath = stringField(result, ["trace_path"]);
  const chartPaths = listField(result, ["chart_path", "chart_paths"]);

  return {
    version: "compat",
    status: String(result.status || ""),
    run_id: typeof result.run_id === "string" ? result.run_id : null,
    question_thread: {
      original_question: stringField(result, ["original_question", "user_question", "question"]),
      system_understanding: "",
      status: typeof result.status === "string" ? result.status : "",
    },
    business_answer: finalAnswer
      ? {
          headline: finalAnswer.split(/[。.!?？]/)[0] || finalAnswer,
          summary: finalAnswer,
          confidence: "medium",
        }
      : undefined,
    evidence: execution
      ? {
          table_preview: {
            columns: execution.columns,
            rows: execution.rows,
          },
        }
      : undefined,
    chart_artifacts: chartPaths.map((path) => ({ title: "分析图表", path })),
    technical_details: {
      sql,
      raw_rows: execution?.rows ?? [],
      trace_path: tracePath,
      provider_metadata: {
        ...(isRecord(result.question_understanding) ? { question_understanding: result.question_understanding } : {}),
        ...(isRecord(result.sql_planning) ? { sql_planning: result.sql_planning } : {}),
        ...(isRecord(result.visualization_trace) ? { visualization: result.visualization_trace } : {}),
      },
    },
  };
}

export default function RunResult({
  result,
  onContinueClarification,
  isContinuing = false,
  continuationError = "",
}: RunResultProps) {
  const product = productResult(result) ?? fallbackProduct(result as Record<string, unknown>);
  const hasProductContent =
    product.question_thread ||
    product.business_answer ||
    product.evidence ||
    product.chart_artifacts?.length ||
    product.technical_details;

  if (!hasProductContent) {
    return <p>本次分析暂未返回可展示结果。</p>;
  }

  return (
    <section className="workbench-result" aria-label="业务分析结果">
      <AnalysisThreadCard
        thread={product.question_thread}
        status={product.status}
        onContinue={onContinueClarification}
        isContinuing={isContinuing}
        continuationError={continuationError}
      />
      <BusinessAnswerCard answer={product.business_answer} />
      <EvidencePanel evidence={product.evidence} />
      <ChartArtifactGallery artifacts={product.chart_artifacts} />
      <TechnicalDetailsDisclosure details={product.technical_details} />
    </section>
  );
}
