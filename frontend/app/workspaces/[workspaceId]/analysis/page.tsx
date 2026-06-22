import Link from "next/link";

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
      </nav>
      <section className="panel">
        <h2>Analysis Question</h2>
        <p>Natural-language analysis controls will call the workspace run API here.</p>
      </section>
    </main>
  );
}
