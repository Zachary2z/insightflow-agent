"use client";

import React, { useState } from "react";
import type { WorkspaceReport } from "../lib/api";

type ReportTechnicalAppendixProps = {
  report: WorkspaceReport;
};

export default function ReportTechnicalAppendix({ report }: ReportTechnicalAppendixProps) {
  const [isOpen, setIsOpen] = useState(false);
  const validation = report.validation;
  const factCount = report.evidence_pack?.facts?.length ?? 0;
  const tableCount = report.evidence_pack?.tables?.length ?? 0;
  const chartCount = report.evidence_pack?.charts?.length ?? 0;
  const warnings = validation?.warnings?.filter((item) => item.trim()) ?? [];
  const unsupportedClaims = validation?.unsupported_claims?.filter((item) => item.trim()) ?? [];

  return (
    <details className="technical-details">
      <summary onClick={() => setIsOpen((current) => !current)}>技术附录</summary>
      {isOpen ? (
        <div className="technical-content">
          <section className="technical-block">
            <h3>证据概况</h3>
            <p>校验状态：{validation?.status ?? "未校验"}</p>
            <p>
              已整理 {factCount} 个关键事实、{tableCount} 张证据表、{chartCount} 个图表或图表意图。
            </p>
            {warnings.length ? (
              <>
                <h4>校验提醒</h4>
                <ul>
                  {warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </>
            ) : null}
            {unsupportedClaims.length ? (
              <>
                <h4>待复核表述</h4>
                <ul>
                  {unsupportedClaims.map((claim) => (
                    <li key={claim}>{claim}</li>
                  ))}
                </ul>
              </>
            ) : null}
          </section>
        </div>
      ) : null}
    </details>
  );
}
