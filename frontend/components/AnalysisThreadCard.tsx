import React, { FormEvent, useState } from "react";
import type { QuestionThread } from "../lib/api";

type ContinuePayload = {
  message: string;
};

type FollowUpPayload = {
  followUpQuestion: string;
  thread: QuestionThread;
};

type AnalysisThreadCardProps = {
  thread?: QuestionThread;
  status?: string;
  isContinuing?: boolean;
  continuationError?: string;
  onContinue?: (payload: ContinuePayload) => Promise<void> | void;
  onAskFollowUp?: (payload: FollowUpPayload) => Promise<void> | void;
};

function ThreadItem({ label, value }: { label: string; value?: string }) {
  if (!value?.trim()) {
    return null;
  }
  return (
    <div className="thread-item">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function statusLabel(status?: string) {
  if (status === "waiting_for_clarification") {
    return "等待用户补充";
  }
  if (status === "completed") {
    return "已完成";
  }
  if (status === "running") {
    return "分析中";
  }
  return status || "";
}

function textValue(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function listFrom(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object" && !Array.isArray(item))) : [];
}

function businessLensTimeNote(thread: QuestionThread) {
  return textValue(thread.current_business_lens?.time_policy_note);
}

function businessLensMetricText(thread: QuestionThread) {
  const lens = thread.current_business_lens ?? {};
  const metrics = listFrom(lens.metrics);
  if (!metrics.length) {
    return "";
  }
  return metrics
    .slice(0, 4)
    .map((metric) => {
      const label = textValue(metric.label) || textValue(metric.source_field);
      const field = textValue(metric.source_field);
      const timeField = textValue(metric.time_field);
      const source = [field, timeField ? `按 ${timeField}` : ""].filter(Boolean).join(" / ");
      return source ? `${label}（${source}）` : label;
    })
    .filter(Boolean)
    .join("；");
}

function evidenceSummary(thread: QuestionThread) {
  const refs = (thread.evidence_refs ?? []).filter((item) => item.trim()).slice(0, 4);
  if (!refs.length) {
    return "";
  }
  const ledgerCount = refs.filter((item) => item.startsWith("question_evidence_ledger")).length;
  const evidenceCount = refs.length - ledgerCount;
  const parts = [];
  if (ledgerCount) {
    parts.push("已保留本轮证据摘要");
  }
  if (evidenceCount) {
    parts.push(`已关联 ${evidenceCount} 条证据`);
  }
  return parts.join("；");
}

function turnLabel(turn: Record<string, unknown>, index: number) {
  return textValue(turn.user_input) || `第 ${index + 1} 轮`;
}

function turnSummary(turn: Record<string, unknown>) {
  return [textValue(turn.resolved_question), textValue(turn.answer_summary)].filter(Boolean).join(" · ");
}

export default function AnalysisThreadCard({
  thread,
  status,
  isContinuing = false,
  continuationError = "",
  onContinue,
  onAskFollowUp,
}: AnalysisThreadCardProps) {
  const [answer, setAnswer] = useState("");
  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const currentStatus = status || thread?.status;
  const waitingForClarification = currentStatus === "waiting_for_clarification";
  const canAskFollowUp = currentStatus === "completed" && Boolean(onAskFollowUp);
  const turns = thread?.turns ?? [];
  const timeNote = thread ? businessLensTimeNote(thread) : "";
  const metricText = thread ? businessLensMetricText(thread) : "";
  const refsText = thread ? evidenceSummary(thread) : "";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!answer.trim() || !onContinue) {
      return;
    }
    onContinue({ message: answer.trim() });
  }

  function handleFollowUpSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!followUpQuestion.trim() || !thread || !onAskFollowUp) {
      return;
    }
    onAskFollowUp({ followUpQuestion: followUpQuestion.trim(), thread });
    setFollowUpQuestion("");
  }

  if (!thread) {
    return null;
  }

  return (
    <article className="panel analysis-thread" aria-label="分析线程">
      <div className="section-heading">
        <div>
          <p className="product-eyebrow">Question Thread</p>
          <h3>分析线程</h3>
          <p className="thread-help">追问是正常分析流程；补充缺失信息后，无需重写完整问题。</p>
        </div>
        {thread.status || status ? <span className="status-chip">{statusLabel(thread.status || status)}</span> : null}
      </div>
      <dl className="thread-list">
        <ThreadItem label="用户问题" value={thread.original_question} />
        <ThreadItem label="系统理解" value={thread.system_understanding} />
        <ThreadItem label="追问" value={thread.clarification_question} />
        <ThreadItem label="用户补充" value={thread.clarification_answer} />
        <ThreadItem label="整理后" value={thread.resolved_question} />
        <ThreadItem label="时间口径" value={timeNote} />
        <ThreadItem label="业务口径" value={metricText} />
        <ThreadItem label="证据引用" value={refsText} />
      </dl>
      {turns.length ? (
        <section className="thread-turns" aria-label="线程记录">
          <h4>线程记录</h4>
          <ol>
            {turns.map((turn, index) => (
              <li key={textValue(turn.turn_id) || `${index}`}>
                <strong>{turnLabel(turn, index)}</strong>
                {turnSummary(turn) ? <span>{turnSummary(turn)}</span> : null}
              </li>
            ))}
          </ol>
        </section>
      ) : null}
      {waitingForClarification && onContinue ? (
        <form className="clarification-form" onSubmit={handleSubmit}>
          <label htmlFor="clarification-answer">用户补充</label>
          <p>只回答上面的追问即可，系统会自动合并原问题和补充信息。</p>
          <div className="inline-form-row">
            <input
              id="clarification-answer"
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              placeholder="例如：最近 90 天"
            />
            <button type="submit" disabled={isContinuing || !answer.trim()}>
              {isContinuing ? "继续中..." : "继续分析"}
            </button>
          </div>
          {continuationError ? <p role="alert">{continuationError}</p> : null}
        </form>
      ) : null}
      {canAskFollowUp ? (
        <form className="clarification-form follow-up-form" onSubmit={handleFollowUpSubmit}>
          <label htmlFor="analysis-follow-up">继续追问</label>
          <p>围绕当前分析继续追问；系统会带上上一轮问题、口径和证据摘要，并继续更新同一条分析线程。</p>
          <div className="inline-form-row">
            <input
              id="analysis-follow-up"
              value={followUpQuestion}
              onChange={(event) => setFollowUpQuestion(event.target.value)}
              placeholder="例如：为什么 email 渠道收益最好？"
            />
            <button type="submit" disabled={isContinuing || !followUpQuestion.trim()}>
              {isContinuing ? "追问中..." : "发送追问"}
            </button>
          </div>
          {continuationError ? <p role="alert">{continuationError}</p> : null}
        </form>
      ) : null}
    </article>
  );
}
