import React from "react";

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
      <h2>Data Profile</h2>
      {tables.length === 0 ? <p>No profile tables returned.</p> : null}
      {tables.map((table) => (
        <article className="panel" key={table.table_name}>
          <h3>{table.table_name}</h3>
          <p>{table.row_count} rows</p>
          <ul>
            {table.columns.map((column) => {
              const roles = Object.entries(column.role_candidates ?? {})
                .filter(([, enabled]) => enabled)
                .map(([role]) => role);
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
                  {typeof column.null_count === "number" ? <span> nulls: {column.null_count}</span> : null}
                  {typeof column.distinct_count === "number" ? <span> distinct: {column.distinct_count}</span> : null}
                </li>
              );
            })}
          </ul>
        </article>
      ))}
    </section>
  );
}
