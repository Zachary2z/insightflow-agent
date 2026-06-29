"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { listWorkspaces, type Workspace } from "../lib/api";
import ProductCard from "./ProductCard";

export default function WorkspaceList() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setIsLoading(true);
        const response = await listWorkspaces();
        if (!cancelled) {
          setWorkspaces(response.workspaces ?? []);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "工作区加载失败");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (isLoading) {
    return <p role="status">正在加载工作区</p>;
  }

  if (error) {
    return (
      <ProductCard role="alert">
        <h2>工作区加载失败</h2>
        <p>{error}</p>
      </ProductCard>
    );
  }

  if (workspaces.length === 0) {
    return (
      <ProductCard>
        <h2>还没有工作区</h2>
        <p>先创建一个工作区，用来导入 CSV、Excel 或 SQLite 数据。</p>
      </ProductCard>
    );
  }

  return (
    <section className="stack">
      {workspaces.map((workspace) => (
        <ProductCard className="item-row" key={workspace.workspace_id}>
          <div>
            <h2>{workspace.name}</h2>
            <p>{workspace.workspace_id}</p>
            {workspace.updated_at ? <p>更新时间：{workspace.updated_at}</p> : null}
          </div>
          <Link className="button" href={`/workspaces/${workspace.workspace_id}/datasets`}>
            打开数据源管理
          </Link>
        </ProductCard>
      ))}
    </section>
  );
}
