import Link from "next/link";
import WorkspaceList from "@/components/WorkspaceList";

export default function WorkspacesPage() {
  return (
    <main>
      <h1>Workspaces</h1>
      <nav>
        <Link href="/workspaces/new">Create workspace</Link>
      </nav>
      <WorkspaceList />
    </main>
  );
}
