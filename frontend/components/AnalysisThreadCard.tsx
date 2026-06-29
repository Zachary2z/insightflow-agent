import React, { FormEvent, useState } from "react";
import type { QuestionThread } from "../lib/api";

type ContinuePayload = {
  pendingRunId: string;
  clarificationAnswer: string;
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
  const pendingRunId = thread?.pending_run_id || "";
  const currentStatus = status || thread?.status;
  const waitingForClarification = currentStatus === "waiting_for_clarification" && pendingRunId;
  const canAskFollowUp = currentStatus === "completed" && Boolean(onAskFollowUp);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!answer.trim() || !pendingRunId || !onContinue) {
      return;
    }
    onContinue({ pendingRunId, clarificationAnswer: answer.trim() });
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
      </dl>
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
          <p>围绕这次分析继续问，系统会带上上一轮问题作为上下文，并重新走安全分析流程。</p>
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
