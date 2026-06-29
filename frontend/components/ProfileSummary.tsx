import React from "react";
import ProductCard from "./ProductCard";

type ProfileColumn = {
  name: string;
  sql_type?: string;
  null_count?: number;
  distinct_count?: number;
  role_candidates?: Record<string, boolean>;
};

type ProfileTable = {
  table_name: string;
  row_count: number;
  columns: ProfileColumn[];
};

type ProfileSummaryProps = {
  profile: {
    tables?: ProfileTable[];
  };
};

export default function ProfileSummary({ profile }: ProfileSummaryProps) {
  const tables = profile.tables ?? [];

  return (
    <section className="stack">
      <h2>字段画像结果</h2>
      {tables.length === 0 ? <p>暂未返回字段画像结果。</p> : null}
      {tables.map((table) => (
        <ProductCard key={table.table_name}>
          <h3>{table.table_name}</h3>
          <p>{table.row_count} 行</p>
          <ul>
            {table.columns.map((column) => {
              const roles = Object.entries(column.role_candidates ?? {})
                .filter(([, enabled]) => enabled)
                .map(([role]) => roleLabel(role));
              return (
                <li key={column.name}>
                  <span>{column.name}</span>
                  {column.sql_type ? <span> ({column.sql_type})</span> : null}
                  {roles.length ? (
                    <span>
                      {" "}
                      {roles.map((role, index) => (
                        <span key={role}>
                          {index > 0 ? ", " : ""}
                          {role}
                        </span>
                      ))}
                    </span>
                  ) : null}
                  {typeof column.null_count === "number" ? <span> 空值: {column.null_count}</span> : null}
                  {typeof column.distinct_count === "number" ? <span> 不同值: {column.distinct_count}</span> : null}
                </li>
              );
            })}
          </ul>
        </ProductCard>
      ))}
    </section>
  );
}

function roleLabel(role: string) {
  const labels: Record<string, string> = {
    measure: "指标",
    dimension: "维度",
    entity: "实体",
    time: "时间字段",
    identifier: "标识字段",
  };
  return labels[role] ?? role;
}
