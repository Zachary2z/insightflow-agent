import React from "react";
import Link from "next/link";
import DataSettings from "@/components/DataSettings";

type SettingsPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function SettingsPage({ params }: SettingsPageProps) {
  const { workspaceId } = await params;

  return (
    <main>
      <h1>数据设置</h1>
      <p>Workspace: {workspaceId}</p>
      <nav>
        <Link href={`/workspaces/${workspaceId}/analysis`}>Analysis</Link>
        <Link href={`/workspaces/${workspaceId}/reports`}>Reports</Link>
        <Link href={`/workspaces/${workspaceId}/datasets`}>Datasets</Link>
        <Link href={`/workspaces/${workspaceId}/profile`}>Profile</Link>
        <Link href={`/workspaces/${workspaceId}/semantic-layer`}>Semantic layer</Link>
      </nav>
      <DataSettings workspaceId={workspaceId} />
    </main>
  );
}
