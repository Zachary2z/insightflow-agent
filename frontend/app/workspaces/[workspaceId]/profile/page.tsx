import Link from "next/link";
import ProfileWorkspace from "@/components/ProfileWorkspace";

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
        <Link href={`/workspaces/${workspaceId}/reports`}>Reports</Link>
        <Link href={`/workspaces/${workspaceId}/settings`}>Settings</Link>
      </nav>
      <ProfileWorkspace workspaceId={workspaceId} />
    </main>
  );
}
