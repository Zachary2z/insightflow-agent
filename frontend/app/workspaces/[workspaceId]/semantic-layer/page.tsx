import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";
import SemanticLayerWorkspace from "@/components/SemanticLayerWorkspace";
import React from "react";

type SemanticLayerPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function SemanticLayerPage({ params }: SemanticLayerPageProps) {
  const { workspaceId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="sources">
      <ProductPageHeader
        eyebrow="业务语义"
        title="语义层草稿"
        description="基于字段画像生成指标、维度、实体和时间字段建议，帮助业务问题稳定落到数据口径。"
      />
      <SemanticLayerWorkspace workspaceId={workspaceId} />
    </ProductShell>
  );
}
