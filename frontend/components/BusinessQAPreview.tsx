"use client";

import Link from "next/link";
import React, { FormEvent, useState } from "react";
import { runAnalysis, type WorkspaceRunResponse } from "../lib/api";
import ProductCard from "./ProductCard";
import { StatusPill } from "./ProductStatus";
import RunResult from "./RunResult";

type BusinessQAPreviewProps = {
  workspaceId: string;
};

function resultForDisplay(run: WorkspaceRunResponse): Record<string, unknown> {
  if (run.product_result) {
    return { ...run.result, product_result: run.product_result };
  }
  return run.result;
}

function ContextItem({ title, body }: { title: string; body: string }) {
  return (
    <li className="quick-item">
      <strong>{title}</strong>
      <span>{body}</span>
    </li>
  );
}

function ArtifactItem({ children }: { children: React.ReactNode }) {
  return <li className="quick-item">{children}</li>;
}

export default function BusinessQAPreview({ workspaceId }: BusinessQAPreviewProps) {
  const [question, setQuestion] = useState("");
  const [run, setRun] = useState<WorkspaceRunResponse | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) {
      setError("请输入一个业务问题。");
      return;
    }

    try {
      setIsRunning(true);
      setError("");
      const response = await runAnalysis(workspaceId, {
        userQuestion: question.trim(),
      });
      setRun(response);
      if (response.run_id) {
        window.sessionStorage.setItem(`insightflow.run.${workspaceId}.${response.run_id}`, JSON.stringify(response));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法生成预览回答");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <section className="business-qa">
      <ProductCard className="business-qa-intro">
        <div className="section-heading">
          <div>
            <p className="product-eyebrow">Business Q&A Mode</p>
            <h2>业务问答模式</h2>
            <p className="product-lead">
              未来模式预览：这里展示的是基于现有分析工作流的一轮业务问答预览，不是完整聊天产品，也不会保存多轮消息历史。
            </p>
          </div>
          <StatusPill tone="orange">未来模式预览</StatusPill>
        </div>
        <p className="qa-preview-note">
          预览会复用当前工作区的数据源、字段画像、语义层和现有分析 API，返回同一套业务结论、证据表、图表和折叠技术详情。
        </p>
      </ProductCard>

      <div className="chat-shell">
        <section className="chat-window" aria-label="业务问答窗口">
          <div className="chat-messages" aria-label="业务问答预览消息">
            <div className="message user">
              <span className="message-label">用户示例问题</span>
              最近 90 天哪个渠道应该加预算？
            </div>
            <div className="message system">
              <strong>正在理解问题</strong>
              <span>我会按最近 90 天，比较渠道收入、投放成本和 ROI；正式结果仍走现有分析工作流。</span>
            </div>
            <div className="message answer">
              <strong>业务回答预览</strong>
              <span>提交真实问题后，这里会显示本轮分析返回的业务结论、证据、图表和默认折叠的技术详情。</span>
            </div>
            {run ? (
              <div className="qa-run-result">
                <RunResult result={resultForDisplay(run)} />
              </div>
            ) : null}
          </div>

          <form className="chat-input-row" onSubmit={handleSubmit}>
            <label htmlFor="business-qa-question">业务问题</label>
            <textarea
              className="chat-input"
              id="business-qa-question"
              rows={2}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="继续追问数据..."
            />
            <button type="submit" disabled={isRunning}>
              {isRunning ? "生成中..." : "生成预览回答"}
            </button>
          </form>
          {error ? <p role="alert">{error}</p> : null}
        </section>

        <aside className="qa-side-panel">
          <ProductCard>
            <p className="product-eyebrow">Context</p>
            <h3>当前上下文</h3>
            <ul className="quick-list qa-context-list">
              <ContextItem title="当前数据源" body="订单表、客户表、营销投放表。" />
              <ContextItem title="字段画像" body="字段类型、行数、候选角色和示例值。" />
              <ContextItem title="语义层" body="指标、维度、实体和时间字段草稿。" />
            </ul>
          </ProductCard>

          <ProductCard>
            <p className="product-eyebrow">Artifacts</p>
            <h3>本轮产物</h3>
            {run?.run_id ? <span className="status-chip">{run.run_id}</span> : null}
            <ul className="quick-list qa-artifact-list">
              <ArtifactItem>业务结论</ArtifactItem>
              <ArtifactItem>证据表</ArtifactItem>
              <ArtifactItem>图表</ArtifactItem>
              <ArtifactItem>报告草稿</ArtifactItem>
            </ul>
          </ProductCard>

          <Link className="button" href={`/workspaces/${workspaceId}/analysis`}>
            打开工作台查看完整证据
          </Link>
          <Link className="button secondary-button" href={`/workspaces/${workspaceId}/reports`}>
            进入报告中心
          </Link>
        </aside>
      </div>
    </section>
  );
}
