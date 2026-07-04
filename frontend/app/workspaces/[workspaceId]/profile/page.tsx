import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";
import ProfileWorkspace from "@/components/ProfileWorkspace";
import React from "react";

type ProfilePageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function ProfilePage({ params }: ProfilePageProps) {
  const { workspaceId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="sources">
      <ProductPageHeader
        eyebrow="字段准备"
        title="字段画像"
        description="从已导入数据生成表、字段和候选角色画像，为语义层和分析工作台提供上下文。"
      />
      <ProfileWorkspace workspaceId={workspaceId} />
    </ProductShell>
  );
}
