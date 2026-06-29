import AnalysisRunner from "@/components/AnalysisRunner";
import ProductPageHeader from "@/components/ProductPageHeader";
import ProductShell from "@/components/ProductShell";

type AnalysisPageProps = {
  params: Promise<{ workspaceId: string }>;
};

export default async function AnalysisPage({ params }: AnalysisPageProps) {
  const { workspaceId } = await params;

  return (
    <ProductShell workspaceId={workspaceId} active="analysis">
      <ProductPageHeader
        eyebrow="Analysis Workbench"
        title="分析工作台"
        description="问一个业务问题，在同一条分析线程里补充追问，并查看业务结论、证据、图表和折叠技术详情。"
      />
      <AnalysisRunner workspaceId={workspaceId} />
    </ProductShell>
  );
}
