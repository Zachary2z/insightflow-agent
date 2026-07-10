"use client";

import Link from "next/link";
import React, { FormEvent, useEffect, useState } from "react";
import { importSqliteSource, listSources, uploadSource, type WorkspaceSource } from "../lib/api";
import ProductCard from "./ProductCard";
import { StatusPill } from "./ProductStatus";

type DatasetManagerProps = {
  workspaceId: string;
};

export default function DatasetManager({ workspaceId }: DatasetManagerProps) {
  const [sources, setSources] = useState<WorkspaceSource[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [sqlitePath, setSqlitePath] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  async function refreshSources() {
    const response = await listSources(workspaceId);
    setSources(response.sources ?? []);
  }

  useEffect(() => {
    refreshSources().catch((err) =>
      setError(`数据源加载失败：${err instanceof Error ? err.message : "请稍后重试。"}`),
    );
  }, [workspaceId]);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedFiles.length === 0) {
      setError("请先选择一个或多个 CSV / Excel 文件。");
      return;
    }
    try {
      setIsBusy(true);
      setError("");
      const importedTables: string[] = [];
      for (const file of selectedFiles) {
        const response = await uploadSource(workspaceId, file);
        importedTables.push(...(response.imported_tables ?? []));
      }
      setStatus(formatUploadStatus(selectedFiles.length, importedTables));
      setSelectedFiles([]);
      await refreshSources();
    } catch (err) {
      setError(`文件上传失败：${err instanceof Error ? err.message : "请检查文件后重试。"}`);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleSqlite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sqlitePath.trim()) {
      setError("请填写 SQLite 文件路径。");
      return;
    }
    try {
      setIsBusy(true);
      setError("");
      const response = await importSqliteSource(workspaceId, sqlitePath.trim());
      setStatus(formatImportStatus(response.imported_tables));
      setSqlitePath("");
      await refreshSources();
    } catch (err) {
      setError(`SQLite 导入失败：${err instanceof Error ? err.message : "请检查路径后重试。"}`);
    } finally {
      setIsBusy(false);
    }
  }

  const sourceCount = sources.length;
  const importedTableCount = sources.reduce((count, source) => count + (source.imported_tables?.length ?? 0), 0);

  return (
    <section className="dataset-manager">
      <div className="dataset-main-column">
        <ProductCard>
          <div className="product-section-title">
            <div>
              <p className="product-eyebrow">已导入文件</p>
              <h2>已导入数据源</h2>
            </div>
            <StatusPill tone={sourceCount > 0 ? "green" : "neutral"}>
              {sourceCount > 0 ? `${sourceCount} 个数据源` : "等待导入"}
            </StatusPill>
          </div>

          {sourceCount === 0 ? (
            <div className="dataset-empty-state">
              <h3>还没有导入数据源</h3>
              <p>请先上传 CSV / Excel 文件，或导入本地 SQLite 数据库。导入后会在这里显示文件、类型、识别表和可分析状态。</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="dataset-source-table">
                <thead>
                  <tr>
                    <th>文件名</th>
                    <th>类型</th>
                    <th>识别表</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((source, index) => (
                    <tr key={source.source_id ?? `${source.name}-${index}`}>
                      <td>
                        <strong>{source.name ?? "未命名数据源"}</strong>
                      </td>
                      <td>{formatSourceType(source.source_type)}</td>
                      <td>{formatImportedTables(source.imported_tables)}</td>
                      <td>
                        <StatusPill tone="green">已导入</StatusPill>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ProductCard>

        <div className="dataset-action-grid" role="region" aria-label="数据源操作区">
          <ProductCard>
            <div className="dataset-card-heading">
              <p className="product-eyebrow">上传文件</p>
              <h2>上传业务文件</h2>
              <p>支持一次选择多个 CSV / Excel 文件，导入后会写入当前工作区的分析数据库。</p>
            </div>
            <form className="form-grid" onSubmit={handleUpload}>
              <label htmlFor="source-file">选择 CSV 或 Excel 文件</label>
              <input
                id="source-file"
                name="source-file"
                type="file"
                accept=".csv,.xlsx,.xls"
                multiple
                onChange={(event) => setSelectedFiles(Array.from(event.target.files ?? []))}
              />
              <button type="submit" disabled={isBusy}>
                上传 CSV / Excel
              </button>
            </form>
          </ProductCard>

          <ProductCard>
            <div className="dataset-card-heading">
              <p className="product-eyebrow">SQLite 数据库</p>
              <h2>导入数据库文件</h2>
              <p>输入服务器可访问的 SQLite 文件路径，系统会保留现有导入逻辑并识别其中的表。</p>
            </div>
            <form className="form-grid" onSubmit={handleSqlite}>
              <label htmlFor="sqlite-path">SQLite 文件路径</label>
              <input
                id="sqlite-path"
                name="sqlite-path"
                type="text"
                autoComplete="off"
                spellCheck={false}
                value={sqlitePath}
                onChange={(event) => setSqlitePath(event.target.value)}
                placeholder="例如：/absolute/path/to/source.db…"
              />
              <button type="submit" disabled={isBusy}>
                导入 SQLite
              </button>
            </form>
          </ProductCard>

          <ProductCard>
            <p className="product-eyebrow">准备状态</p>
            <h2>数据准备状态</h2>
            <div className="dataset-readiness-list">
              <div>
                <span aria-hidden="true">✓</span>
                {sourceCount > 0 ? `${sourceCount} 个文件已导入` : "等待导入第一个文件"}
              </div>
              <div>
                <span aria-hidden="true">✓</span>
                {importedTableCount > 0 ? `${importedTableCount} 个表已识别` : "导入后自动识别表结构"}
              </div>
              <div>
                <span aria-hidden="true">✓</span>
                {sourceCount > 0 ? "可进入分析工作台" : "完成导入后继续分析"}
              </div>
            </div>
          </ProductCard>

          <ProductCard className="dataset-next-card">
            <p className="product-eyebrow">下一步</p>
            <h2>下一步</h2>
            <div className="dataset-next-links">
              <Link className="button secondary-button" href={`/workspaces/${workspaceId}/profile`}>
                生成数据画像
              </Link>
              <Link className="button secondary-button" href={`/workspaces/${workspaceId}/settings`}>
                进入数据设置
              </Link>
              <Link className="button" href={`/workspaces/${workspaceId}/analysis`}>
                前往分析工作台
              </Link>
            </div>
          </ProductCard>
        </div>

        {status ? <p role="status">{status}</p> : null}
        {error ? <p role="alert">{error}</p> : null}
      </div>
    </section>
  );
}

function formatUploadStatus(fileCount: number, importedTables?: string[]) {
  if (!importedTables || importedTables.length === 0) {
    return `已上传 ${fileCount} 个文件，正在刷新数据源列表。`;
  }
  return `已上传 ${fileCount} 个文件，导入表：${importedTables.join(", ")}`;
}

function formatImportStatus(importedTables?: string[]) {
  if (!importedTables || importedTables.length === 0) {
    return "导入已完成，正在刷新数据源列表。";
  }
  return `已导入表：${importedTables.join(", ")}`;
}

function formatImportedTables(importedTables?: string[]) {
  if (!importedTables || importedTables.length === 0) {
    return "待识别";
  }
  return importedTables.join(", ");
}

function formatSourceType(sourceType?: string) {
  if (!sourceType) {
    return "数据源";
  }
  return sourceType.toUpperCase();
}
