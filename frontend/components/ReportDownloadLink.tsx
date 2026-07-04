import React from "react";
import { getWorkspaceReportDownloadUrl } from "../lib/api";

type ReportDownloadLinkProps = {
  workspaceId: string;
  reportId: string;
  label?: string;
};

export default function ReportDownloadLink({ workspaceId, reportId, label = "下载 Markdown" }: ReportDownloadLinkProps) {
  return (
    <a className="button" href={getWorkspaceReportDownloadUrl(workspaceId, reportId)}>
      {label}
    </a>
  );
}
