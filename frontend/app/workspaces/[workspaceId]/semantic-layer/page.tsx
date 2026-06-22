import Link from "next/link";

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
      <section className="panel">
        <h2>Draft Semantic Model</h2>
        <p>Draft metrics, dimensions, and entities will be editable here.</p>
      </section>
    </main>
  );
}
