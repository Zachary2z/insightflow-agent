"use client";

import { useRouter } from "next/navigation";
import React, { FormEvent, useState } from "react";
import { createWorkspaceReport, type ReportType } from "../lib/api";
import ProductCard from "./ProductCard";

type ReportGeneratorProps = {
  workspaceId: string;
};

const REPORT_TYPES: Array<{ value: ReportType; label: string; description: string }> = [
  { value: "business_review", label: "经营复盘", description: "收入、渠道、趋势和建议的管理层报告" },
  { value: "channel_performance", label: "渠道表现", description: "对比渠道贡献、效率和后续动作" },
  { value: "revenue_trend", label: "收入趋势", description: "观察收入变化、异常波动和趋势判断" },
];

const GOAL_EXAMPLES = [
  "生成最近 90 天渠道表现复盘",
  "生成管理层收入复盘报告",
  "生成客户增长与留存报告",
];

export default function ReportGenerator({ workspaceId }: ReportGeneratorProps) {
  const router = useRouter();
  const [reportType, setReportType] = useState<ReportType>("business_review");
  const [reportGoal, setReportGoal] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reportGoal.trim()) {
      setError("请先填写报告目标。");
      return;
    }
    try {
      setIsGenerating(true);
      setError("");
      const response = await createWorkspaceReport(workspaceId, {
        reportType,
        reportGoal: reportGoal.trim(),
      });
      router.push(`/workspaces/${workspaceId}/reports/${response.report_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "报告生成失败");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <ProductCard className="report-generator-card">
      <div className="product-section-title">
        <div>
          <p className="product-eyebrow">生成报告</p>
          <h2>新建报告</h2>
          <p className="panel-help">选择报告类型，写下业务目标。系统会复用当前工作区数据和安全分析链路生成报告。</p>
        </div>
      </div>
      <div className="report-goal-examples" aria-label="推荐报告目标">
        {GOAL_EXAMPLES.map((example) => (
          <button className="secondary-button" key={example} type="button" onClick={() => setReportGoal(example)}>
            {example}
          </button>
        ))}
      </div>
      <form className="form-grid report-form" onSubmit={handleSubmit}>
        <label htmlFor="report-type">报告类型</label>
        <select
          id="report-type"
          value={reportType}
          onChange={(event) => setReportType(event.target.value as ReportType)}
        >
          {REPORT_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
        <p className="panel-help">{REPORT_TYPES.find((type) => type.value === reportType)?.description}</p>
        <label htmlFor="report-goal">报告目标</label>
        <textarea
          id="report-goal"
          rows={4}
          value={reportGoal}
          onChange={(event) => setReportGoal(event.target.value)}
          placeholder="例如：生成最近 90 天渠道表现复盘，重点关注收入贡献、变化趋势和下一步建议。"
        />
        <button type="submit" disabled={isGenerating}>
          {isGenerating ? "正在生成" : "生成报告"}
        </button>
      </form>
      {error ? <p role="alert">{error}</p> : null}
    </ProductCard>
  );
}
