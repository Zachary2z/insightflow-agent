import Link from "next/link";
import ProductEntryShell from "@/components/ProductEntryShell";
import ProductPageHeader from "@/components/ProductPageHeader";
import WorkspaceNewForm from "@/components/WorkspaceNewForm";
import React from "react";

export default function NewWorkspacePage() {
  return (
    <ProductEntryShell action={<Link className="button" href="/workspaces">返回工作区</Link>}>
      <ProductPageHeader
        eyebrow="工作区"
        title="新建工作区"
        description="先创建一个干净的分析空间，再导入真实业务文件并开始准备数据。"
      />
      <WorkspaceNewForm />
    </ProductEntryShell>
  );
}
