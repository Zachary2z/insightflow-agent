import Link from "next/link";
import ProductCard from "@/components/ProductCard";
import ProductEntryShell from "@/components/ProductEntryShell";
import ProductPageHeader from "@/components/ProductPageHeader";
import React from "react";

export default function HomePage() {
  return (
    <ProductEntryShell action={<Link className="button" href="/workspaces">进入工作区</Link>}>
      <ProductPageHeader
        eyebrow="业务数据分析"
        title="InsightFlow"
        description="导入 CSV、Excel 或 SQLite 数据，生成字段画像和语义层，再用真实大模型完成业务问答与管理层报告。"
      />
      <ProductCard>
        <div className="product-section-title">
          <p className="product-eyebrow">开始使用</p>
          <h2>从一个工作区开始</h2>
          <p className="panel-help">工作区会保存数据源、语义准备、分析线程和报告产物，方便后续继续追问和复盘。</p>
        </div>
        <Link className="button" href="/workspaces">打开工作区列表</Link>
      </ProductCard>
    </ProductEntryShell>
  );
}
