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
  if (!answer || (!answer.headline && !answer.summary)) {
    return null;
  }

  const flags = answer.quality_flags ?? [];
  const hasRawParameterWarning = flags.includes("raw_parameter_dump_detected");

  return (
    <article className="panel business-answer">
      <div className="section-heading">
        <div>
          <p className="product-eyebrow">Business Answer</p>
          <h3>业务结论</h3>
          {answer.headline ? <p className="answer-headline">{answer.headline}</p> : null}
        </div>
        {answer.confidence ? <span className="status-chip">置信度 {answer.confidence}</span> : null}
      </div>
      {answer.summary ? <p className="answer-summary">{answer.summary}</p> : null}
      {hasRawParameterWarning ? (
        <p className="soft-warning">回答已自动过滤技术参数，建议结合证据表补充业务解读。</p>
      ) : null}
      <div className="answer-grid">
        <TextList title="建议" items={answer.recommendations} />
        <TextList title="下一步" items={answer.next_actions} />
        <TextList title="注意事项" items={answer.caveats} />
      </div>
    </article>
  );
}
