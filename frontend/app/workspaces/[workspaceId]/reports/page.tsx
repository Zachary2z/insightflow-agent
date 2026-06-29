import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";
import ReportGenerator from "@/components/ReportGenerator";
import ReportList from "@/components/ReportList";

type ReportsPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function ReportsPage({ params }: ReportsPageProps) {
  const { workspaceId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="reports">
      <ProductPageHeader
        eyebrow="Report Center"
        title="报告中心"
        description="用于生成、阅读、下载管理层报告。正文业务化，技术信息默认收起。"
      />
      <section className="stack">
        <ReportGenerator workspaceId={workspaceId} />
        <ReportList workspaceId={workspaceId} />
      </section>
    </ProductShell>
  );
}
