import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";
import ReportGenerator from "@/components/ReportGenerator";
import ReportList from "@/components/ReportList";
import React from "react";

type ReportsPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function ReportsPage({ params }: ReportsPageProps) {
  const { workspaceId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="reports">
      <ProductPageHeader
        eyebrow="Report center"
        title="报告"
        description="集中管理业务复盘、渠道表现和收入趋势报告。报告正文面向管理层阅读，技术信息默认收起。"
      />
      <section className="report-center">
        <ReportGenerator workspaceId={workspaceId} />
        <ReportList workspaceId={workspaceId} />
      </section>
    </ProductShell>
  );
}
