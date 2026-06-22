import Link from "next/link";

export default function NewWorkspacePage() {
  return (
    <main>
      <h1>Create Workspace</h1>
      <nav>
        <Link href="/workspaces">Back to workspaces</Link>
      </nav>
      <section className="panel">
        <h2>Workspace Details</h2>
        <p>Create workspace controls will connect to the API client in the next frontend flow slice.</p>
      </section>
    </main>
  );
}
