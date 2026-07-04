import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";
import RunResultLoader from "@/components/RunResultLoader";
import React from "react";

type RunDetailPageProps = {
  params: Promise<{ workspaceId: string; runId: string }>;
};

export default async function RunDetailPage({ params }: RunDetailPageProps) {
  const { workspaceId, runId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="analysis">
      <ProductPageHeader
        eyebrow="分析记录"
        title="分析详情"
        description={`查看本次分析结果、证据和默认折叠的技术详情。Run: ${runId}`}
      />
      <RunResultLoader workspaceId={workspaceId} runId={runId} />
    </ProductShell>
  );
}
