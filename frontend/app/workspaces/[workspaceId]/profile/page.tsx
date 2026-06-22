import Link from "next/link";
import ProfileSummary from "@/components/ProfileSummary";

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
      <ProfileSummary profile={{ tables: [] }} />
    </main>
  );
}
