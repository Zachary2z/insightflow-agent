import React from "react";
import { getWorkspaceReportDownloadUrl } from "../lib/api";

type ReportDownloadLinkProps = {
  workspaceId: string;
  reportId: string;
};

export default function ReportDownloadLink({ workspaceId, reportId }: ReportDownloadLinkProps) {
  return (
    <a className="button" href={getWorkspaceReportDownloadUrl(workspaceId, reportId)}>
      Download Markdown
    </a>
  );
}
