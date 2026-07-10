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
  business_answer: "业务回答",
  visualization: "图表建议",
  report_composer: "报告撰写",
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

function enabledFeatureLabels(features?: Record<string, boolean>) {
  return Object.entries(features ?? {})
    .filter(([, enabled]) => enabled)
    .map(([feature]) => FEATURE_LABELS[feature] ?? feature.replaceAll("_", " "));
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
        if (isMounted) setSettings(response);
      } catch (err) {
        if (isMounted) setError(err instanceof Error ? err.message : "工作区设置加载失败");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    void loadSettings();
    return () => {
      isMounted = false;
    };
  }, [workspaceId]);

  if (isLoading) return <p role="status">正在加载工作区设置…</p>;
  if (error) return <p role="alert">{error}</p>;
  if (!settings) return <p role="alert">没有返回工作区设置，请刷新后重试。</p>;

  const sources = settings.data_sources.sources ?? [];
  const profileTables = settings.profile.tables ?? [];
  const metrics = settings.semantic_layer.metrics ?? [];
  const dimensions = settings.semantic_layer.dimensions ?? [];
  const enabledFeatures = enabledFeatureLabels(settings.model_mode.provider_features);
  const sourceCount = settings.data_sources.source_count ?? sources.length;
  const importedTableCount =
    settings.data_sources.imported_table_count ??
    sources.reduce((count, source) => count + (source.imported_tables?.length ?? 0), 0);
  const tableCount = settings.profile.table_count ?? profileTables.length;
  const columnCount =
    settings.profile.column_count ?? profileTables.reduce((count, table) => count + table.columns.length, 0);
  const providerName = settings.model_mode.provider?.name ?? "DeepSeek";
  const providerModel = settings.model_mode.provider?.model;
  const providerLabel = providerModel ? `${providerName} / ${providerModel}` : providerName;

  const readinessItems = [
    {
      label: "数据源",
      status: settings.data_sources.status,
      detail: `${sourceCount} 个数据源 / ${importedTableCount} 张导入表`,
    },
    {
      label: "字段画像",
      status: settings.profile.status,
      detail: `${tableCount} 张表 / ${columnCount} 个字段`,
    },
    {
      label: "业务语义",
      status: settings.semantic_layer.status,
      detail: `${metrics.length} 个指标 / ${dimensions.length} 个维度`,
    },
    {
      label: "真实模型",
      status: settings.model_mode.product_live_mode ? "ready" : "missing",
      detail: settings.model_mode.product_live_mode ? "真实模型已参与" : "真实模型未开启",
    },
  ];

  return (
    <section className="stack data-settings">
      <ProductCard>
        <div className="product-section-title">
          <div>
            <p className="product-eyebrow">Workspace readiness</p>
            <h2>工作区概览</h2>
            <p className="panel-help">这里保留状态和治理信息；数据明细统一在“数据准备”中管理。</p>
          </div>
          <Link className="button secondary-button" href={`/workspaces/${workspaceId}/datasets`}>
            打开数据准备
          </Link>
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
            <p className="product-eyebrow">Model participation</p>
            <h2>真实模型模式</h2>
            <p className="panel-help">{providerLabel}</p>
          </div>
          <StatusPill tone={settings.model_mode.product_live_mode ? "green" : "neutral"}>
            {settings.model_mode.product_live_mode ? "真实模型已参与" : "真实模型未开启"}
          </StatusPill>
        </div>
        {enabledFeatures.length ? (
          <div className="settings-chip-list" aria-label="真实模型参与能力">
            {enabledFeatures.map((feature) => (
              <span className="settings-chip" key={feature}>{feature}</span>
            ))}
          </div>
        ) : (
          <p className="panel-help">暂无真实模型能力参与。</p>
        )}
      </ProductCard>

      <ProductCard>
        <div className="product-section-title">
          <div>
            <p className="product-eyebrow">Safety & audit</p>
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
              策略：{settings.safety.technical_details_policy === "collapsed_by_default"
                ? "默认折叠"
                : settings.safety.technical_details_policy}
            </p>
          </div>
        </div>
        <details className="technical-details">
          <summary onClick={() => setIsTechnicalOpen((current) => !current)}>技术详情</summary>
          {isTechnicalOpen ? (
            <div className="technical-content">
              <p>Provider 配置和原始安全策略只在审计或排查时查看。</p>
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
