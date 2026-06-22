import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <h1>InsightFlow Data Analyst</h1>
      <p>Bring CSV, Excel, or SQLite data into a workspace and ask real analysis questions.</p>
      <Link href="/workspaces">Open workspaces</Link>
    </main>
  );
}
