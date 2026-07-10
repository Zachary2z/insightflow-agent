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
        eyebrow="Workspace settings"
        title="工作区设置"
        description="查看工作区准备状态、真实模型参与范围和安全审计边界。"
      />
      <DataSettings workspaceId={workspaceId} />
    </ProductShell>
  );
}
