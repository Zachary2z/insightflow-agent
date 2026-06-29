import React from "react";
import DataSettings from "@/components/DataSettings";
import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";

type SettingsPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function SettingsPage({ params }: SettingsPageProps) {
  const { workspaceId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="settings">
      <ProductPageHeader
        eyebrow="数据准备"
        title="数据设置"
        description="管理数据源、字段画像、语义层、真实模型模式和安全边界。"
      />
      <DataSettings workspaceId={workspaceId} />
    </ProductShell>
  );
}
