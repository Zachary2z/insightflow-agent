import Link from "next/link";
import React from "react";

type DataPreparationTab = "sources" | "profile" | "semantic";

type DataPreparationTabsProps = {
  workspaceId: string;
  active: DataPreparationTab;
};

const TABS: Array<{ key: DataPreparationTab; label: string; path: string }> = [
  { key: "sources", label: "数据源", path: "datasets" },
  { key: "profile", label: "字段画像", path: "profile" },
  { key: "semantic", label: "业务语义", path: "semantic-layer" },
];

export default function DataPreparationTabs({ workspaceId, active }: DataPreparationTabsProps) {
  return (
    <nav className="data-preparation-tabs" aria-label="数据准备内容">
      {TABS.map((tab) => (
        <Link
          aria-current={tab.key === active ? "page" : undefined}
          href={`/workspaces/${workspaceId}/${tab.path}`}
          key={tab.key}
        >
          {tab.label}
        </Link>
      ))}
    </nav>
  );
}
