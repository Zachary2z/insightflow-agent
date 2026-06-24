import Link from "next/link";
import ReportViewer from "@/components/ReportViewer";

type ReportDetailPageProps = {
  params: Promise<{ workspaceId: string; reportId: string }>;
};

export default async function ReportDetailPage({ params }: ReportDetailPageProps) {
  const { workspaceId, reportId } = await params;

  return (
    <main>
      <h1>Report Detail</h1>
      <p>Workspace: {workspaceId}</p>
      <p>Report: {reportId}</p>
      <nav>
        <Link href={`/workspaces/${workspaceId}/reports`}>Back to reports</Link>
        <Link href={`/workspaces/${workspaceId}/analysis`}>Analysis</Link>
        <Link href={`/workspaces/${workspaceId}/profile`}>Profile</Link>
        <Link href={`/workspaces/${workspaceId}/semantic-layer`}>Semantic layer</Link>
        <Link href={`/workspaces/${workspaceId}/settings`}>Settings</Link>
      </nav>
      <ReportViewer workspaceId={workspaceId} reportId={reportId} />
    </main>
  );
}
