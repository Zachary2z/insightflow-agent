import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";
import ProfileWorkspace from "@/components/ProfileWorkspace";
import DataPreparationTabs from "@/components/DataPreparationTabs";
import React from "react";

type ProfilePageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function ProfilePage({ params }: ProfilePageProps) {
  const { workspaceId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="prepare">
      <ProductPageHeader
        eyebrow="Field profile"
        title="数据准备"
        description="确认表结构、字段类型和候选业务角色，为后续业务语义和分析提供可靠上下文。"
      />
      <DataPreparationTabs workspaceId={workspaceId} active="profile" />
      <ProfileWorkspace workspaceId={workspaceId} />
    </ProductShell>
  );
}
