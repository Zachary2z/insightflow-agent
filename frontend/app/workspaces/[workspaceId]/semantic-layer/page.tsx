import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";
import SemanticLayerWorkspace from "@/components/SemanticLayerWorkspace";
import DataPreparationTabs from "@/components/DataPreparationTabs";
import React from "react";

type SemanticLayerPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function SemanticLayerPage({ params }: SemanticLayerPageProps) {
  const { workspaceId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="prepare">
      <ProductPageHeader
        eyebrow="Business semantics"
        title="数据准备"
        description="把技术字段整理成指标、维度、实体和时间口径，让业务问题稳定落到真实数据。"
      />
      <DataPreparationTabs workspaceId={workspaceId} active="semantic" />
      <SemanticLayerWorkspace workspaceId={workspaceId} />
    </ProductShell>
  );
}
