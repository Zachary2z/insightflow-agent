import React from "react";
import DatasetManager from "@/components/DatasetManager";
import DataPreparationTabs from "@/components/DataPreparationTabs";
import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";

type DatasetsPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function DatasetsPage({ params }: DatasetsPageProps) {
  const { workspaceId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="prepare">
      <ProductPageHeader
        eyebrow="Workspace readiness"
        title="数据准备"
        description="把文件、字段和业务口径集中在一处。先连接真实业务数据，再完成字段画像与业务语义。"
      />
      <DataPreparationTabs workspaceId={workspaceId} active="sources" />
      <DatasetManager workspaceId={workspaceId} />
    </ProductShell>
  );
}
