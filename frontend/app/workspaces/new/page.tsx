import Link from "next/link";
import WorkspaceNewForm from "@/components/WorkspaceNewForm";

export default function NewWorkspacePage() {
  return (
    <main>
      <h1>Create Workspace</h1>
      <nav>
        <Link href="/workspaces">Back to workspaces</Link>
      </nav>
      <WorkspaceNewForm />
    </main>
  );
}
