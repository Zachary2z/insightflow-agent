import Link from "next/link";
import ReportGenerator from "@/components/ReportGenerator";
import ReportList from "@/components/ReportList";

type ReportsPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function ReportsPage({ params }: ReportsPageProps) {
  const { workspaceId } = await params;

  return (
    <main>
      <h1>Reports</h1>
      <p>Workspace: {workspaceId}</p>
      <nav>
        <Link href={`/workspaces/${workspaceId}/datasets`}>Datasets</Link>
        <Link href={`/workspaces/${workspaceId}/profile`}>Profile</Link>
        <Link href={`/workspaces/${workspaceId}/semantic-layer`}>Semantic layer</Link>
        <Link href={`/workspaces/${workspaceId}/analysis`}>Analysis</Link>
        <Link href={`/workspaces/${workspaceId}/settings`}>Settings</Link>
      </nav>
      <section className="stack">
        <ReportGenerator workspaceId={workspaceId} />
        <ReportList workspaceId={workspaceId} />
      </section>
    </main>
  );
}
