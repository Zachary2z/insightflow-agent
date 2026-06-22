import Link from "next/link";

export default function WorkspacesPage() {
  return (
    <main>
      <h1>Workspaces</h1>
      <nav>
        <Link href="/workspaces/new">Create workspace</Link>
      </nav>
      <section className="panel">
        <h2>Workspace List</h2>
        <p>Workspace data will load from the InsightFlow API in the next frontend flow slice.</p>
      </section>
    </main>
  );
}
