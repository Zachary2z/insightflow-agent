import React from "react";
import { getWorkspaceReportDownloadUrl } from "../lib/api";

type ReportDownloadLinkProps = {
  workspaceId: string;
  reportId: string;
  label?: string;
  className?: string;
};

export default function ReportDownloadLink({
  workspaceId,
  reportId,
  label = "下载 Markdown",
  className = "button",
}: ReportDownloadLinkProps) {
  return (
    <a className={className} href={getWorkspaceReportDownloadUrl(workspaceId, reportId)}>
      {label}
    </a>
  );
}
