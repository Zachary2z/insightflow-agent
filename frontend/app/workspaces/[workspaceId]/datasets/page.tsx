import Link from "next/link";
import DatasetManager from "@/components/DatasetManager";

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
        <Link href={`/workspaces/${workspaceId}/reports`}>Reports</Link>
      </nav>
      <DatasetManager workspaceId={workspaceId} />
    </main>
  );
}
