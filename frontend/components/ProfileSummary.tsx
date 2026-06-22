import React from "react";

type ProfileColumn = {
  name: string;
  role_candidates?: Record<string, boolean>;
};

type ProfileTable = {
  table_name: string;
  row_count: number;
  columns: ProfileColumn[];
};

type ProfileSummaryProps = {
  profile: {
    tables: ProfileTable[];
  };
};

export default function ProfileSummary({ profile }: ProfileSummaryProps) {
  return (
    <section>
      <h2>Data Profile</h2>
      {profile.tables.map((table) => (
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
                </li>
              );
            })}
          </ul>
        </article>
      ))}
    </section>
  );
}
