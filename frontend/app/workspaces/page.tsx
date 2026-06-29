import Link from "next/link";
import ProductEntryShell from "@/components/ProductEntryShell";
import ProductPageHeader from "@/components/ProductPageHeader";
import WorkspaceList from "@/components/WorkspaceList";
import React from "react";

export default function WorkspacesPage() {
  return (
    <ProductEntryShell action={<Link className="button" href="/workspaces/new">新建工作区</Link>}>
      <ProductPageHeader
        eyebrow="工作区"
        title="选择工作区"
        description="每个工作区对应一组业务数据、语义准备、分析线程和报告记录。"
      />
      <WorkspaceList />
    </ProductEntryShell>
  );
}
