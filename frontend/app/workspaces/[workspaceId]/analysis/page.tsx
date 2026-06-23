import Link from "next/link";
import AnalysisRunner from "@/components/AnalysisRunner";

type AnalysisPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function AnalysisPage({ params }: AnalysisPageProps) {
  const { workspaceId } = await params;

  return (
    <main>
      <h1>Ask InsightFlow</h1>
      <p>Workspace: {workspaceId}</p>
      <nav>
        <Link href={`/workspaces/${workspaceId}/datasets`}>Datasets</Link>
        <Link href={`/workspaces/${workspaceId}/profile`}>Profile</Link>
        <Link href={`/workspaces/${workspaceId}/semantic-layer`}>Semantic layer</Link>
        <Link href={`/workspaces/${workspaceId}/reports`}>Reports</Link>
      </nav>
      <AnalysisRunner workspaceId={workspaceId} />
    </main>
  );
}
