"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { getWorkspaceSettings, type WorkspaceSettings } from "../lib/api";
import ProductCard from "./ProductCard";
import { StatusPill } from "./ProductStatus";

type DataSettingsProps = {
  workspaceId: string;
};

type StatusTone = "green" | "orange" | "blue" | "neutral";

const FEATURE_LABELS: Record<string, string> = {
  question_understanding: "问题理解",
  clarification: "追问判断",
  sql_planning: "SQL 规划",
  sql_candidate: "SQL 草案",
  insight_drafting: "结论撰写",
  claim_typing: "证据判断",
  visualization: "图表建议",
};

const ROLE_LABELS: Record<string, string> = {
  measure: "指标",
  metric: "指标",
  dimension: "维度",
  entity: "实体",
  time: "时间字段",
  id: "标识字段",
  identifier: "标识字段",
  status: "状态字段",
  text: "文本字段",
};

function readinessLabel(status?: string) {
  if (status === "ready") return "已准备";
  if (status === "missing") return "未生成";
  if (status === "empty") return "暂无数据";
  return status ?? "未知";
}

function readinessTone(status?: string): StatusTone {
  if (status === "ready") return "green";
  if (status === "missing") return "orange";
  if (status === "empty") return "neutral";
  return "blue";
}

function itemName(item: Record<string, unknown>) {
  return String(item.name ?? item.label ?? item.field ?? "未命名");
}

function roleText(roleCandidates?: Record<string, boolean>) {
  const roles = Object.entries(roleCandidates ?? {})
    .filter(([, enabled]) => enabled)
    .map(([role]) => ROLE_LABELS[role] ?? role);
  return roles.length ? roles.join(" / ") : "待分类";
}

function enabledFeatureLabels(features?: Record<string, boolean>) {
  return Object.entries(features ?? {})
    .filter(([, enabled]) => enabled)
    .map(([feature]) => FEATURE_LABELS[feature] ?? feature.replaceAll("_", " "));
}

function formatSourceType(sourceType?: string) {
  if (!sourceType) return "数据源";
  if (sourceType.toLowerCase() === "csv") return "CSV 文件";
  if (sourceType.toLowerCase() === "xlsx" || sourceType.toLowerCase() === "excel") return "Excel 文件";
  if (sourceType.toLowerCase() === "sqlite") return "SQLite 数据库";
  return sourceType.toUpperCase();
}

function formatImportedTables(tables?: string[]) {
  return tables && tables.length > 0 ? tables.join(", ") : "待识别";
}

function enabledText(value?: string) {
  return value === "enabled" ? "已开启" : value === "disabled" ? "未开启" : (value ?? "未知");
}

export default function DataSettings({ workspaceId }: DataSettingsProps) {
  const [settings, setSettings] = useState<WorkspaceSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [isTechnicalOpen, setIsTechnicalOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function loadSettings() {
      try {
        setIsLoading(true);
        setError("");
        const response = await getWorkspaceSettings(workspaceId);
        if (isMounted) {
          setSettings(response);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "数据设置加载失败");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadSettings();
    return () => {
      isMounted = false;
    };
  }, [workspaceId]);

  if (isLoading) {
    return <p role="status">正在加载数据设置</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  if (!settings) {
    return <p>没有返回数据设置。</p>;
  }

  const sources = settings.data_sources.sources ?? [];
  const profileTables = settings.profile.tables ?? [];
  const metrics = settings.semantic_layer.metrics ?? [];
  const dimensions = settings.semantic_layer.dimensions ?? [];
  const entities = settings.semantic_layer.entities ?? [];
  const timeFields = settings.semantic_layer.time_fields ?? [];
  const enabledFeatures = enabledFeatureLabels(settings.model_mode.provider_features);
  const sourceCount = settings.data_sources.source_count ?? sources.length;
  const importedTableCount =
    settings.data_sources.imported_table_count ??
    sources.reduce((count, source) => count + (source.imported_tables?.length ?? 0), 0);
  const tableCount = settings.profile.table_count ?? profileTables.length;
  const columnCount =
    settings.profile.column_count ?? profileTables.reduce((count, table) => count + table.columns.length, 0);
  const rowCount = settings.profile.row_count ?? profileTables.reduce((count, table) => count + table.row_count, 0);
  const providerName = settings.model_mode.provider?.name ?? "DeepSeek";
  const providerModel = settings.model_mode.provider?.model;
  const providerLabel = providerModel ? `${providerName} / ${providerModel}` : providerName;

  const readinessItems = [
    { label: "数据源状态", status: settings.data_sources.status, detail: `${sourceCount} 个数据源 / ${importedTableCount} 张导入表` },
    { label: "字段画像状态", status: settings.profile.status, detail: `${tableCount} 张表 / ${columnCount} 个字段` },
    { label: "语义层状态", status: settings.semantic_layer.status, detail: `${metrics.length} 个指标 / ${dimensions.length} 个维度` },
    {
      label: "真实模型状态",
      status: settings.model_mode.product_live_mode ? "ready" : "missing",
      detail: settings.model_mode.product_live_mode ? "真实模型已参与" : "真实模型未开启",
    },
    { label: "安全审计状态", status: "ready", detail: "SQL 审核、敏感字段、Trace 边界保留" },
  ];

  return (
    <section className="stack data-settings">
      <ProductCard>
        <div className="product-section-title">
          <div>
            <p className="product-eyebrow">准备状态</p>
            <h2>数据准备总览</h2>
            <p className="panel-help">确认数据源、字段画像、语义层、真实模型和安全审计是否已经可以支撑业务分析。</p>
          </div>
        </div>
        <div className="settings-overview-grid">
          {readinessItems.map((item) => (
            <div className="settings-summary-card" key={item.label}>
              <span>{item.label}</span>
              <StatusPill tone={readinessTone(item.status)}>{readinessLabel(item.status)}</StatusPill>
              <p>{item.detail}</p>
            </div>
          ))}
        </div>
      </ProductCard>

      <ProductCard>
        <div className="product-section-title">
          <div>
            <p className="product-eyebrow">来源与表</p>
            <h2>数据源</h2>
          </div>
          <StatusPill tone={readinessTone(settings.data_sources.status)}>
            {readinessLabel(settings.data_sources.status)}
          </StatusPill>
        </div>
        {sources.length === 0 ? (
          <div className="dataset-empty-state">
            <h3>暂无数据源</h3>
            <p>先回到数据源管理导入 CSV、Excel 或 SQLite。</p>
            <Link className="button secondary-button" href={`/workspaces/${workspaceId}/datasets`}>
              前往数据源管理
            </Link>
          </div>
        ) : (
          <div className="settings-card-grid">
            {sources.map((source, index) => (
              <div className="settings-detail-card" key={source.source_id ?? `${source.name}-${index}`}>
                <strong>{source.name ?? "未命名数据源"}</strong>
                <span>{formatSourceType(source.source_type)}</span>
                <p>导入表：{formatImportedTables(source.imported_tables)}</p>
              </div>
            ))}
          </div>
        )}
      </ProductCard>

      <ProductCard>
        <div className="product-section-title">
          <div>
            <p className="product-eyebrow">表结构与字段角色</p>
            <h2>字段画像</h2>
          </div>
          <StatusPill tone={readinessTone(settings.profile.status)}>{readinessLabel(settings.profile.status)}</StatusPill>
        </div>
        <div className="settings-metric-row">
          <div>
            <span>表数量</span>
            <strong>{tableCount} 张表</strong>
          </div>
          <div>
            <span>字段数量</span>
            <strong>{columnCount} 个字段</strong>
          </div>
          <div>
            <span>行数</span>
            <strong>{rowCount} 行</strong>
          </div>
        </div>
        {profileTables.length === 0 ? (
          <p className="panel-help">未生成字段画像。完成画像后会显示表数量、字段数量、行数和字段角色。</p>
        ) : (
          <div className="settings-list">
            {profileTables.map((table) => (
              <section className="settings-table-profile" key={table.table_name}>
                <div>
                  <h3>{table.table_name}</h3>
                  <p>{table.row_count} 行</p>
                </div>
                <div className="settings-chip-list">
                  {table.columns.map((column) => (
                    <span className="settings-chip" key={column.name}>
                      {column.name} · {roleText(column.role_candidates)}
                    </span>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </ProductCard>

      <ProductCard>
        <div className="product-section-title">
          <div>
            <p className="product-eyebrow">业务语义</p>
            <h2>语义层</h2>
          </div>
          <StatusPill tone={readinessTone(settings.semantic_layer.status)}>
            {readinessLabel(settings.semantic_layer.status)}
          </StatusPill>
        </div>
        <div className="settings-grid">
          <SemanticGroup title="指标" items={metrics} emptyText="未生成指标" />
          <SemanticGroup title="维度" items={dimensions} emptyText="未生成维度" />
          <SemanticGroup title="实体" items={entities} emptyText="未生成实体" />
          <SemanticGroup title="时间字段" items={timeFields} emptyText="未生成时间字段" />
        </div>
      </ProductCard>

      <ProductCard>
        <div className="product-section-title">
          <div>
            <p className="product-eyebrow">模型参与范围</p>
            <h2>真实模型模式</h2>
          </div>
          <StatusPill tone={settings.model_mode.product_live_mode ? "green" : "neutral"}>
            {settings.model_mode.product_live_mode ? "真实模型已参与" : "真实模型未开启"}
          </StatusPill>
        </div>
        <p className="panel-help">{providerLabel}</p>
        {enabledFeatures.length ? (
          <div className="settings-chip-list" aria-label="真实模型参与能力">
            {enabledFeatures.map((feature) => (
              <span className="settings-chip" key={feature}>
                {feature}
              </span>
            ))}
          </div>
        ) : (
          <p className="panel-help">暂无真实模型能力参与。</p>
        )}
      </ProductCard>

      <ProductCard>
        <div className="product-section-title">
          <div>
            <p className="product-eyebrow">守护边界</p>
            <h2>安全与审计</h2>
          </div>
          <StatusPill tone="green">已开启</StatusPill>
        </div>
        <div className="settings-card-grid">
          <div className="settings-detail-card settings-safety-card">
            <strong>SQL 审核不可绕过</strong>
            <p>状态：{enabledText(settings.safety.sql_review)}</p>
          </div>
          <div className="settings-detail-card settings-safety-card">
            <strong>敏感字段拦截已开启</strong>
            <p>状态：{enabledText(settings.safety.sensitive_field_blocking)}</p>
          </div>
          <div className="settings-detail-card settings-safety-card">
            <strong>Trace 可审计</strong>
            <p>状态：{enabledText(settings.safety.trace_available)}</p>
          </div>
          <div className="settings-detail-card settings-safety-card">
            <strong>技术详情默认折叠</strong>
            <p>
              策略：
              {settings.safety.technical_details_policy === "collapsed_by_default"
                ? "默认折叠"
                : settings.safety.technical_details_policy}
            </p>
          </div>
        </div>
        <details className="technical-details">
          <summary onClick={() => setIsTechnicalOpen((current) => !current)}>技术详情</summary>
          {isTechnicalOpen ? (
            <div className="technical-content">
              <p>provider metadata、raw config、SQL、原始行、校验日志和 Trace 仅在审计或排查时展开查看。</p>
              <pre>
                {JSON.stringify(
                  {
                    provider: settings.model_mode.provider ?? null,
                    provider_features: settings.model_mode.provider_features ?? {},
                    safety: settings.safety,
                    raw_config_policy: "collapsed_by_default",
                  },
                  null,
                  2,
                )}
              </pre>
            </div>
          ) : null}
        </details>
      </ProductCard>
    </section>
  );
}

function SemanticGroup({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: Array<Record<string, unknown>>;
  emptyText: string;
}) {
  return (
    <section className="settings-semantic-group">
      <h3>{title}</h3>
      {items.length ? (
        <div className="settings-chip-list">
          {items.map((item, index) => (
            <span className="settings-chip" key={`${itemName(item)}-${index}`}>
              {itemName(item)}
            </span>
          ))}
        </div>
      ) : (
        <p className="panel-help">{emptyText}</p>
      )}
    </section>
  );
}
