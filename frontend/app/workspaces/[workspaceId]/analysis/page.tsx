import Link from "next/link";
import AnalysisRunner from "@/components/AnalysisRunner";

type AnalysisPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function AnalysisPage({ params }: AnalysisPageProps) {
  const { workspaceId } = await params;

  return (
    <main>
      <h1>Analysis Workbench</h1>
      <p>工作区：{workspaceId}</p>
      <nav>
        <Link href={`/workspaces/${workspaceId}/datasets`}>Datasets</Link>
        <Link href={`/workspaces/${workspaceId}/profile`}>Profile</Link>
        <Link href={`/workspaces/${workspaceId}/semantic-layer`}>Semantic layer</Link>
        <Link href={`/workspaces/${workspaceId}/reports`}>Reports</Link>
        <Link href={`/workspaces/${workspaceId}/settings`}>Settings</Link>
      </nav>
      <AnalysisRunner workspaceId={workspaceId} />
    </main>
  );
}
