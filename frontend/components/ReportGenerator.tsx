"use client";

import { useRouter } from "next/navigation";
import React, { FormEvent, useState } from "react";
import { createWorkspaceReport } from "../lib/api";
import ProductCard from "./ProductCard";

type ReportGeneratorProps = {
  workspaceId: string;
};

const GOAL_EXAMPLES = [
  {
    label: "经营复盘",
    description: "收入、客户、商品、渠道与建议",
    goal: "生成一份最近90天经营复盘报告，包含收入、客户、商品、渠道投放表现和建议。",
  },
  {
    label: "管理层简报",
    description: "渠道效率、商品表现与客户分群",
    goal: "生成一份管理层经营简报，重点看渠道效率、商品表现和客户分群。",
  },
  {
    label: "收入趋势",
    description: "最近90天收入变化",
    goal: "生成一份最近90天收入趋势变化报告。",
  },
];

export default function ReportGenerator({ workspaceId }: ReportGeneratorProps) {
  const router = useRouter();
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
      <div className="report-generator-layout">
        <section className="report-generator-guidance">
          <p className="product-eyebrow">生成报告</p>
          <h2>新建报告</h2>
          <p className="panel-help">写下想生成的报告目标，系统会结合当前工作区数据推断标题、章节和证据范围。</p>
          <div className="report-goal-examples" aria-label="推荐报告目标">
            {GOAL_EXAMPLES.map((example) => (
              <button
                aria-label={`${example.label} ${example.description}`}
                className="secondary-button report-goal-template"
                key={example.label}
                type="button"
                onClick={() => setReportGoal(example.goal)}
              >
                <strong>{example.label}</strong>
                <span>{example.description}</span>
              </button>
            ))}
          </div>
        </section>
        <form className="form-grid report-form report-generator-composer" onSubmit={handleSubmit}>
          <div className="report-composer-heading">
            <label htmlFor="report-goal">报告目标</label>
            <span>选择左侧模板，或直接描述这份报告需要回答的问题。</span>
          </div>
          <textarea
            className="report-goal-input"
            id="report-goal"
            name="report-goal"
            autoComplete="off"
            rows={5}
            style={{ resize: "none" }}
            value={reportGoal}
            onChange={(event) => setReportGoal(event.target.value)}
            placeholder="例如：生成一份最近90天经营复盘报告，包含收入、客户、商品、渠道投放表现和建议…"
          />
          <button type="submit" disabled={isGenerating}>
            {isGenerating ? "正在生成…" : "生成报告"}
          </button>
        </form>
      </div>
      {error ? <p role="alert">{error}</p> : null}
    </ProductCard>
  );
}
