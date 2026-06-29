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
    <li>
      <strong>{title}</strong>
      <span>{body}</span>
    </li>
  );
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

      <div className="business-qa-grid">
        <ProductCard>
          <div className="section-heading">
            <div>
              <p className="product-eyebrow">Current Context</p>
              <h2>当前上下文</h2>
              <p className="product-lead">这些是未来问答模式会复用的现有产品对象。</p>
            </div>
          </div>
          <ul className="qa-context-list">
            <ContextItem title="当前数据源" body="来自数据源管理的 CSV、Excel 或 SQLite 导入表。" />
            <ContextItem title="字段画像" body="沿用字段类型、行数、候选角色和示例值。" />
            <ContextItem title="语义层" body="复用指标、维度、实体和时间字段草稿。" />
            <ContextItem title="最近分析结果" body="本页提交后会展示当前这一轮分析返回的产品结果。" />
            <ContextItem title="报告草稿" body="正式沉淀结论时仍进入报告中心生成结构化报告。" />
          </ul>
        </ProductCard>

        <ProductCard className="question-panel">
          <div className="section-heading">
            <div>
              <p className="product-eyebrow">Preview Question</p>
              <h2>业务问题</h2>
              <p className="product-lead">提交一个问题，使用现有分析工作流生成一次预览回答。</p>
            </div>
          </div>
          <form className="form-grid" onSubmit={handleSubmit}>
            <label htmlFor="business-qa-question">业务问题</label>
            <textarea
              id="business-qa-question"
              rows={4}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="例如：下个月预算应该优先投哪个渠道？"
            />
            <button type="submit" disabled={isRunning}>
              {isRunning ? "生成中..." : "生成预览回答"}
            </button>
          </form>
          {error ? <p role="alert">{error}</p> : null}
        </ProductCard>
      </div>

      <ProductCard className="business-qa-answer">
        <div className="section-heading">
          <div>
            <p className="product-eyebrow">Preview Answer</p>
            <h2>业务结论</h2>
            <p className="product-lead">回答区复用现有分析结果对象；SQL、raw rows 和 provider metadata 仍在技术详情里默认折叠。</p>
          </div>
          {run?.run_id ? <span className="status-chip">{run.run_id}</span> : null}
        </div>
        {run ? (
          <RunResult result={resultForDisplay(run)} />
        ) : (
          <div className="qa-answer-placeholder">
            提交业务问题后，会在这里展示业务结论、分析线程、证据表、图表和折叠技术详情。
          </div>
        )}
      </ProductCard>

      <ProductCard className="business-qa-next">
        <div className="section-heading">
          <div>
            <p className="product-eyebrow">Next Step</p>
            <h2>继续处理</h2>
            <p className="product-lead">需要拆解指标、追问补充或正式产出时，进入已经完成的产品流程。</p>
          </div>
        </div>
        <div className="qa-action-row">
          <Link className="button secondary-button" href={`/workspaces/${workspaceId}/analysis`}>
            进入分析工作台
          </Link>
          <Link className="button secondary-button" href={`/workspaces/${workspaceId}/reports`}>
            进入报告中心
          </Link>
        </div>
      </ProductCard>
    </section>
  );
}
