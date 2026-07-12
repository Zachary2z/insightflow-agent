"use client";

import React, { FormEvent, useState } from "react";
import { createWorkspace, type Workspace } from "../lib/api";
import ProductCard from "./ProductCard";

type WorkspaceNewFormProps = {
  onCreated?: (workspace: Workspace) => void;
};

export default function WorkspaceNewForm({ onCreated }: WorkspaceNewFormProps) {
  const [name, setName] = useState("");
  const [created, setCreated] = useState<Workspace | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setError("请填写工作区名称。");
      return;
    }
    try {
      setIsSubmitting(true);
      setError("");
      const workspace = await createWorkspace(name.trim());
      setCreated(workspace);
      onCreated?.(workspace);
      if (!onCreated && workspace.workspace_id) {
        window.location.assign(`/workspaces/${workspace.workspace_id}/datasets`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "工作区创建失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ProductCard className="workspace-create-card">
      <h2>工作区信息</h2>
      <p className="workspace-create-help">先为这次分析命名；创建后即可导入数据并配置业务口径。</p>
      <form className="form-grid workspace-create-form" onSubmit={handleSubmit}>
        <label htmlFor="workspace-name">工作区名称</label>
        <input
          id="workspace-name"
          name="workspace-name"
          type="text"
          autoComplete="off"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="例如：收入复盘工作区…"
        />
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "创建中…" : "创建工作区"}
        </button>
      </form>
      {error ? <p role="alert">{error}</p> : null}
      {created ? (
        <p role="status">
          已创建工作区：<strong>{created.name}</strong>
        </p>
      ) : null}
    </ProductCard>
  );
}
