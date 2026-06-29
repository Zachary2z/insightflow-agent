import BusinessQAPreview from "@/components/BusinessQAPreview";
import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";
import React from "react";

type BusinessQAPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function BusinessQAPage({ params }: BusinessQAPageProps) {
  const { workspaceId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="business-qa">
      <ProductPageHeader
        eyebrow="Business Q&A"
        title="业务问答"
        description="未来模式预览：用现有分析工作流体验一轮业务问答，查看业务结论、证据和图表，但不伪装成完整聊天产品。"
      />
      <BusinessQAPreview workspaceId={workspaceId} />
    </ProductShell>
  );
}
