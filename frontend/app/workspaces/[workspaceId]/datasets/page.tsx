import React from "react";
import DatasetManager from "@/components/DatasetManager";
import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";

type DatasetsPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function DatasetsPage({ params }: DatasetsPageProps) {
  const { workspaceId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="sources">
      <ProductPageHeader
        eyebrow="数据导入"
        title="数据源管理"
        description="先把真实业务文件导入工作区，再生成数据画像、语义层和可分析问题。"
      />
      <DatasetManager workspaceId={workspaceId} />
    </ProductShell>
  );
}
