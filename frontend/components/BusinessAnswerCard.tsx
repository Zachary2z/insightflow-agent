import React from "react";
import type { BusinessAnswer } from "../lib/api";

type BusinessAnswerCardProps = {
  answer?: BusinessAnswer;
};

function TextList({
  title,
  items,
  className = "",
}: {
  title: string;
  items?: string[];
  className?: string;
}) {
  const visibleItems = items?.filter((item) => item.trim()) ?? [];
  if (!visibleItems.length) {
    return null;
  }
  return (
    <section className={`decision-support-block ${className}`.trim()}>
      <h4>{title}</h4>
      <ul className="compact-list">
        {visibleItems.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

const CONFIDENCE_LABELS: Record<BusinessAnswer["confidence"], string> = {
  low: "低",
  medium: "中",
  high: "高",
};

export default function BusinessAnswerCard({ answer }: BusinessAnswerCardProps) {
  if (!answer) {
    return null;
  }

  return (
    <article className="decision-summary">
      <header className="decision-summary-header">
        <div>
          <p className="product-eyebrow">业务回答</p>
          <h3>业务结论</h3>
        </div>
        <span className="status-chip">置信度 {CONFIDENCE_LABELS[answer.confidence]}</span>
      </header>
      <section className="decision-summary-thesis">
        <p className="answer-headline">{answer.headline}</p>
        <p className="answer-summary">{answer.direct_answer}</p>
      </section>
      <div className="decision-support-grid">
        <section className="decision-support-block decision-reasoning">
          <h4>为什么</h4>
          <p>{answer.why}</p>
        </section>
        <TextList className="decision-evidence" title="关键证据" items={answer.evidence_bullets} />
        <TextList className="decision-recommendations" title="建议动作" items={answer.recommendations} />
        <TextList className="decision-caveats" title="限制说明" items={answer.caveats} />
      </div>
    </article>
  );
}
