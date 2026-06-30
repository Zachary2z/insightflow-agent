import React from "react";
import type { BusinessAnswer } from "../lib/api";

type BusinessAnswerCardProps = {
  answer?: BusinessAnswer;
};

function TextList({ title, items }: { title: string; items?: string[] }) {
  const visibleItems = items?.filter((item) => item.trim()) ?? [];
  if (!visibleItems.length) {
    return null;
  }
  return (
    <div>
      <h4>{title}</h4>
      <ul className="compact-list">
        {visibleItems.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function BusinessAnswerCard({ answer }: BusinessAnswerCardProps) {
  if (!answer) {
    return null;
  }

  return (
    <article className="panel business-answer">
      <div className="section-heading">
        <div>
          <p className="product-eyebrow">业务回答</p>
          <h3>业务结论</h3>
        </div>
        <span className="status-chip">置信度 {answer.confidence}</span>
      </div>
      <section>
        <h4>结论</h4>
        <p className="answer-headline">{answer.headline}</p>
      </section>
      <section>
        <h4>直接回答</h4>
        <p className="answer-summary">{answer.direct_answer}</p>
      </section>
      <section>
        <h4>为什么</h4>
        <p>{answer.why}</p>
      </section>
      <div className="answer-grid">
        <TextList title="关键证据" items={answer.evidence_bullets} />
        <TextList title="建议动作" items={answer.recommendations} />
        <TextList title="限制说明" items={answer.caveats} />
      </div>
    </article>
  );
}
