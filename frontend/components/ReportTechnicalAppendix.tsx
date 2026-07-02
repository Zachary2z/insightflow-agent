"use client";

import React, { useState } from "react";
import type { WorkspaceReport } from "../lib/api";

type ReportTechnicalAppendixProps = {
  report: WorkspaceReport;
};

function hasValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (value && typeof value === "object") {
    return Object.keys(value).length > 0;
  }
  return typeof value === "string" ? value.trim().length > 0 : Boolean(value);
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  if (!hasValue(value)) {
    return null;
  }
  return (
    <div className="technical-block">
      <h4>{title}</h4>
      <pre>{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</pre>
    </div>
  );
}

export default function ReportTechnicalAppendix({ report }: ReportTechnicalAppendixProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <details className="technical-details">
      <summary onClick={() => setIsOpen((current) => !current)}>技术附录</summary>
      {isOpen ? (
        <div className="technical-content">
          <section className="technical-block">
            <h3>报告元数据</h3>
            <JsonBlock title="报告 ID" value={report.report_id} />
            <JsonBlock title="工作区 ID" value={report.workspace_id} />
            <JsonBlock title="JSON 路径" value={report.json_path} />
            <JsonBlock title="Markdown 路径" value={report.markdown_path} />
            <JsonBlock title="Trace 路径" value={report.trace_path} />
            <JsonBlock title="产物目录" value={report.artifact_dir} />
            <JsonBlock title="模型元数据" value={report.provider_metadata} />
          </section>
          <section className="technical-block">
            <h3>报告合同</h3>
            <JsonBlock title="报告规划" value={report.plan} />
            <JsonBlock title="证据包" value={report.evidence_pack} />
            <JsonBlock title="校验结果" value={report.validation} />
            <JsonBlock title="技术明细" value={report.document?.technical_appendix} />
          </section>
        </div>
      ) : null}
    </details>
  );
}
