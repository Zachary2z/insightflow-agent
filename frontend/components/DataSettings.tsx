"use client";

import React, { useEffect, useState } from "react";
import { getWorkspaceSettings, type WorkspaceSettings } from "../lib/api";

type DataSettingsProps = {
  workspaceId: string;
};

function statusText(status?: string) {
  if (status === "ready") return "Ready";
  if (status === "missing") return "Not ready";
  if (status === "empty") return "No data yet";
  return status ?? "Unknown";
}

function itemName(item: Record<string, unknown>) {
  return String(item.name ?? item.label ?? item.field ?? "Unnamed");
}

function roleText(roleCandidates?: Record<string, boolean>) {
  const roles = Object.entries(roleCandidates ?? {})
    .filter(([, enabled]) => enabled)
    .map(([role]) => role);
  return roles.length ? roles.join(", ") : "unclassified";
}

function enabledFeatureLabels(features?: Record<string, boolean>) {
  const labels: Record<string, string> = {
    question_understanding: "Question understanding",
    clarification: "Clarification",
    sql_planning: "SQL planning",
    sql_candidate: "Guarded SQL candidate",
    insight_drafting: "Insight drafting",
    claim_typing: "Claim typing",
    visualization: "Visualization",
    report_writer: "Report writing",
  };
  return Object.entries(features ?? {})
    .filter(([, enabled]) => enabled)
    .map(([feature]) => labels[feature] ?? feature.replaceAll("_", " "));
}

export default function DataSettings({ workspaceId }: DataSettingsProps) {
  const [settings, setSettings] = useState<WorkspaceSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

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
          setError(err instanceof Error ? err.message : "Unable to load data settings");
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
    return <p role="status">Loading data settings</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  if (!settings) {
    return <p>No settings returned.</p>;
  }

  const sources = settings.data_sources.sources ?? [];
  const profileTables = settings.profile.tables ?? [];
  const metrics = settings.semantic_layer.metrics ?? [];
  const dimensions = settings.semantic_layer.dimensions ?? [];
  const entities = settings.semantic_layer.entities ?? [];
  const timeFields = settings.semantic_layer.time_fields ?? [];
  const enabledFeatures = enabledFeatureLabels(settings.model_mode.provider_features);

  return (
    <section className="stack data-settings">
      <article className="panel settings-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Readiness</p>
            <h2>Data sources</h2>
          </div>
          <span className="status-chip">{statusText(settings.data_sources.status)}</span>
        </div>
        {sources.length === 0 ? (
          <p>No data sources imported yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Imported tables</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((source, index) => (
                  <tr key={source.source_id ?? `${source.name}-${index}`}>
                    <td>{source.name ?? "Unnamed source"}</td>
                    <td>{source.source_type ?? "source"}</td>
                    <td>{(source.imported_tables ?? []).join(", ") || "None"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>

      <article className="panel settings-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Profile</p>
            <h2>Field profile</h2>
          </div>
          <span className="status-chip">{statusText(settings.profile.status)}</span>
        </div>
        {profileTables.length === 0 ? (
          <p>Generate a profile to see row counts, columns, and inferred field roles.</p>
        ) : (
          <div className="settings-list">
            {profileTables.map((table) => (
              <section key={table.table_name}>
                <h3>{table.table_name} table</h3>
                <p>{table.row_count} rows</p>
                <ul className="compact-list">
                  {table.columns.map((column) => (
                    <li key={column.name}>
                      <span>{column.name}</span>
                      <span> - {roleText(column.role_candidates)}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
      </article>

      <article className="panel settings-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Meaning</p>
            <h2>Semantic layer</h2>
          </div>
          <span className="status-chip">{statusText(settings.semantic_layer.status)}</span>
        </div>
        <div className="settings-grid">
          <section>
            <h3>Metrics</h3>
            {metrics.length ? (
              <ul className="compact-list">
                {metrics.map((metric, index) => (
                  <li key={`${itemName(metric)}-${index}`}>{itemName(metric)}</li>
                ))}
              </ul>
            ) : (
              <p>No metrics drafted yet.</p>
            )}
          </section>
          <section>
            <h3>Dimensions</h3>
            {dimensions.length ? (
              <ul className="compact-list">
                {dimensions.map((dimension, index) => (
                  <li key={`${itemName(dimension)}-${index}`}>{itemName(dimension)}</li>
                ))}
              </ul>
            ) : (
              <p>No dimensions drafted yet.</p>
            )}
          </section>
          <section>
            <h3>Entities</h3>
            {entities.length ? (
              <ul className="compact-list">
                {entities.map((entity, index) => (
                  <li key={`${itemName(entity)}-${index}`}>{itemName(entity)}</li>
                ))}
              </ul>
            ) : (
              <p>No entities drafted yet.</p>
            )}
          </section>
          <section>
            <h3>Time fields</h3>
            {timeFields.length ? (
              <ul className="compact-list">
                {timeFields.map((field, index) => (
                  <li key={`${itemName(field)}-${index}`}>{itemName(field)}</li>
                ))}
              </ul>
            ) : (
              <p>No time fields drafted yet.</p>
            )}
          </section>
        </div>
      </article>

      <article className="panel settings-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Runtime</p>
            <h2>Product/live mode</h2>
          </div>
          <span className="status-chip">{settings.model_mode.product_live_mode ? "On" : "Off"}</span>
        </div>
        <p>{settings.model_mode.status_label ?? "Product/live mode status unavailable"}</p>
        <p>
          Provider: {settings.model_mode.provider?.name ?? "DeepSeek"}{" "}
          {settings.model_mode.provider?.model ? `(${settings.model_mode.provider.model})` : ""}
        </p>
        {enabledFeatures.length ? (
          <ul className="compact-list">
            {enabledFeatures.map((feature) => (
              <li key={feature}>{feature}</li>
            ))}
          </ul>
        ) : (
          <p>Provider-backed product features are not enabled.</p>
        )}
      </article>

      <article className="panel settings-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Guardrails</p>
            <h2>Safety and audit</h2>
          </div>
          <span className="status-chip">Enabled</span>
        </div>
        <ul className="compact-list">
          <li>SQL review {settings.safety.sql_review}</li>
          <li>Sensitive field blocking {settings.safety.sensitive_field_blocking}</li>
          <li>Trace {settings.safety.trace_available === "enabled" ? "available" : settings.safety.trace_available}</li>
          <li>
            Technical details{" "}
            {settings.safety.technical_details_policy === "collapsed_by_default"
              ? "collapsed by default"
              : settings.safety.technical_details_policy}
          </li>
        </ul>
        <details className="technical-details">
          <summary>Technical details policy</summary>
          <div className="technical-content">
            <p>SQL, raw rows, provider metadata, validation logs, and traces stay available for audit.</p>
          </div>
        </details>
      </article>
    </section>
  );
}
