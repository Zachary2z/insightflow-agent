import Link from "next/link";
import SemanticLayerWorkspace from "@/components/SemanticLayerWorkspace";

type SemanticLayerPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function SemanticLayerPage({ params }: SemanticLayerPageProps) {
  const { workspaceId } = await params;

  return (
    <main>
      <h1>Semantic Layer</h1>
      <p>Workspace: {workspaceId}</p>
      <nav>
        <Link href={`/workspaces/${workspaceId}/datasets`}>Datasets</Link>
        <Link href={`/workspaces/${workspaceId}/profile`}>Profile</Link>
        <Link href={`/workspaces/${workspaceId}/analysis`}>Analysis</Link>
      </nav>
      <SemanticLayerWorkspace workspaceId={workspaceId} />
    </main>
  );
}
