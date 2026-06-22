import Link from "next/link";

type ProfilePageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function ProfilePage({ params }: ProfilePageProps) {
  const { workspaceId } = await params;

  return (
    <main>
      <h1>Data Profile</h1>
      <p>Workspace: {workspaceId}</p>
      <nav>
        <Link href={`/workspaces/${workspaceId}/datasets`}>Datasets</Link>
        <Link href={`/workspaces/${workspaceId}/semantic-layer`}>Semantic layer</Link>
        <Link href={`/workspaces/${workspaceId}/analysis`}>Analysis</Link>
      </nav>
      <section className="panel">
        <h2>Profile Summary</h2>
        <p>Table and column profile summaries will render here.</p>
      </section>
    </main>
  );
}
