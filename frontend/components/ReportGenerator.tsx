"use client";

import { useRouter } from "next/navigation";
import React, { FormEvent, useState } from "react";
import { createWorkspaceReport, type ReportType } from "../lib/api";

type ReportGeneratorProps = {
  workspaceId: string;
};

const REPORT_TYPES: Array<{ value: ReportType; label: string }> = [
  { value: "business_review", label: "Business review" },
  { value: "channel_performance", label: "Channel performance" },
  { value: "revenue_trend", label: "Revenue trend" },
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
      setError("Report goal is required.");
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
      setError(err instanceof Error ? err.message : "Unable to generate report");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <article className="panel">
      <h2>Generate Report</h2>
      <form className="form-grid" onSubmit={handleSubmit}>
        <label htmlFor="report-type">Report type</label>
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
        <label htmlFor="report-goal">Report goal</label>
        <textarea
          id="report-goal"
          rows={4}
          value={reportGoal}
          onChange={(event) => setReportGoal(event.target.value)}
          placeholder="Create a leadership report focused on revenue, channel performance, trend changes, and recommendations."
        />
        <button type="submit" disabled={isGenerating}>
          {isGenerating ? "Generating..." : "Generate report"}
        </button>
      </form>
      {error ? <p role="alert">{error}</p> : null}
    </article>
  );
}
