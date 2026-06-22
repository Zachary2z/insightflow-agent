import Link from "next/link";

type DatasetsPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function DatasetsPage({ params }: DatasetsPageProps) {
  const { workspaceId } = await params;

  return (
    <main>
      <h1>Datasets</h1>
      <p>Workspace: {workspaceId}</p>
      <nav>
        <Link href={`/workspaces/${workspaceId}/profile`}>Profile</Link>
        <Link href={`/workspaces/${workspaceId}/semantic-layer`}>Semantic layer</Link>
        <Link href={`/workspaces/${workspaceId}/analysis`}>Analysis</Link>
      </nav>
      <section className="panel">
        <h2>Imported Data</h2>
        <p>CSV, Excel, and SQLite sources will appear here after upload/import support lands.</p>
      </section>
    </main>
  );
}
