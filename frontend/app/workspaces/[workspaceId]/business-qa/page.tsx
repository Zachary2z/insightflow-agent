import { redirect } from "next/navigation";

type BusinessQAPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function BusinessQAPage({ params }: BusinessQAPageProps) {
  const { workspaceId } = await params;
  redirect(`/workspaces/${workspaceId}/analysis`);
}
