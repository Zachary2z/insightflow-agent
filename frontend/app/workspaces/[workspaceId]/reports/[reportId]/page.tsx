import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";
import ReportViewer from "@/components/ReportViewer";
import React from "react";

type ReportDetailPageProps = {
  params: Promise<{ workspaceId: string; reportId: string }>;
};

export default async function ReportDetailPage({ params }: ReportDetailPageProps) {
  const { workspaceId, reportId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="reports">
      <ProductPageHeader
        eyebrow="Report reader"
        title="报告"
        description="阅读报告正文、查看章节和图表，并在需要时展开技术附录。"
      />
      <ReportViewer workspaceId={workspaceId} reportId={reportId} />
    </ProductShell>
  );
}
