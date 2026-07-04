import React from "react";
import type { BusinessAnswer, ProductAnalysisResult } from "../lib/api";
import AnalysisProgressTimeline from "./AnalysisProgressTimeline";
import AnalysisThreadCard from "./AnalysisThreadCard";
import BusinessAnswerCard from "./BusinessAnswerCard";
import ChartArtifactGallery from "./ChartArtifactGallery";
import EvidencePanel from "./EvidencePanel";
import TechnicalDetailsDisclosure from "./TechnicalDetailsDisclosure";

type ContinuePayload = {
  pendingRunId: string;
  clarificationAnswer: string;
};

type FollowUpPayload = {
  followUpQuestion: string;
  thread: NonNullable<ProductAnalysisResult["question_thread"]>;
};

type RunResultEnvelope = Record<string, unknown> & {
  product_result?: unknown;
};

type RunResultProps = {
  result: RunResultEnvelope;
  onContinueClarification?: (payload: ContinuePayload) => Promise<void> | void;
  onAskFollowUp?: (payload: FollowUpPayload) => Promise<void> | void;
  isContinuing?: boolean;
  continuationError?: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

const BUSINESS_ANSWER_KEYS = [
  "headline",
  "direct_answer",
  "why",
  "evidence_bullets",
  "recommendations",
  "caveats",
  "confidence",
];

function isBusinessAnswer(value: unknown): value is BusinessAnswer {
  if (!isRecord(value)) {
    return false;
  }
  const keys = Object.keys(value).sort();
  if (keys.length !== BUSINESS_ANSWER_KEYS.length || keys.join("|") !== [...BUSINESS_ANSWER_KEYS].sort().join("|")) {
    return false;
  }
  return (
    typeof value.headline === "string" &&
    value.headline.trim().length > 0 &&
    typeof value.direct_answer === "string" &&
    value.direct_answer.trim().length > 0 &&
    typeof value.why === "string" &&
    value.why.trim().length > 0 &&
    Array.isArray(value.evidence_bullets) &&
    Array.isArray(value.recommendations) &&
    Array.isArray(value.caveats) &&
    ["low", "medium", "high"].includes(String(value.confidence))
  );
}

function productResult(result: RunResultEnvelope): ProductAnalysisResult | null {
  if (!isRecord(result)) {
    return null;
  }
  const record = result as Record<string, unknown>;
  if (isRecord(record.product_result)) {
    const product = record.product_result as Record<string, unknown>;
    if (product.version === "p16.v1" && isBusinessAnswer(product.business_answer)) {
      return product as ProductAnalysisResult;
    }
  }
  return null;
}

function ProductResultError() {
  return (
    <section className="panel soft-warning" role="alert">
      <h3>分析结果结构异常</h3>
      <p>后端没有返回当前 P16 业务答案结构，请重新运行分析。</p>
    </section>
  );
}

export default function RunResult({
  result,
  onContinueClarification,
  onAskFollowUp,
  isContinuing = false,
  continuationError = "",
}: RunResultProps) {
  const product = productResult(result);

  if (!product) {
    return <ProductResultError />;
  }

  return (
    <section className="workbench-result" aria-label="业务分析结果">
      <AnalysisThreadCard
        thread={product.question_thread}
        status={product.status}
        onContinue={onContinueClarification}
        onAskFollowUp={onAskFollowUp}
        isContinuing={isContinuing}
        continuationError={continuationError}
      />
      <AnalysisProgressTimeline steps={product.progress_steps} />
      <BusinessAnswerCard answer={product.business_answer} />
      <EvidencePanel evidence={product.evidence} />
      <ChartArtifactGallery artifacts={product.chart_artifacts} />
      <TechnicalDetailsDisclosure details={product.technical_details} />
    </section>
  );
}
