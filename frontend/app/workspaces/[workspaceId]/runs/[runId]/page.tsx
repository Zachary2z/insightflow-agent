import Link from "next/link";

type RunDetailPageProps = {
  params: Promise<{ workspaceId: string; runId: string }>;
};

export default async function RunDetailPage({ params }: RunDetailPageProps) {
  const { workspaceId, runId } = await params;

  return (
    <main>
      <h1>Run Detail</h1>
      <p>Workspace: {workspaceId}</p>
      <p>Run: {runId}</p>
      <nav>
        <Link href={`/workspaces/${workspaceId}/analysis`}>Back to analysis</Link>
        <Link href={`/workspaces/${workspaceId}/profile`}>Profile</Link>
        <Link href={`/workspaces/${workspaceId}/semantic-layer`}>Semantic layer</Link>
      </nav>
      <section className="panel">
        <h2>Result and Trace</h2>
        <p>SQL, result rows, charts, and trace events will render here.</p>
      </section>
    </main>
  );
}
