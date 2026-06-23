import React from "react";

type RunResultProps = {
  result: Record<string, unknown>;
};

type ExecutionResult = {
  columns: string[];
  rows: Array<unknown[] | Record<string, unknown>>;
};

function stringField(result: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = result[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return "";
}

function listField(result: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = result[key];
    if (Array.isArray(value)) {
      return value.map((item) => String(item));
    }
    if (typeof value === "string" && value.trim()) {
      return [value];
    }
  }
  return [];
}

function executionResult(result: Record<string, unknown>): ExecutionResult | null {
  const candidate = result.execution_result;
  if (!candidate || typeof candidate !== "object") {
    return null;
  }
  const record = candidate as Record<string, unknown>;
  const rows = Array.isArray(record.rows) ? (record.rows as Array<unknown[] | Record<string, unknown>>) : [];
  const columns = Array.isArray(record.columns)
    ? record.columns.map((column) => String(column))
    : rows.length > 0 && !Array.isArray(rows[0]) && typeof rows[0] === "object"
      ? Object.keys(rows[0] as Record<string, unknown>)
      : [];
  return { columns, rows };
}

function rowValue(row: unknown[] | Record<string, unknown>, column: string, index: number) {
  if (Array.isArray(row)) {
    return row[index];
  }
  return row[column];
}

export default function RunResult({ result }: RunResultProps) {
  const execution = executionResult(result);
  const finalAnswer = stringField(result, ["final_answer", "answer", "summary", "error"]);
  const sql = stringField(result, ["generated_sql", "final_sql", "sql"]);
  const chartPaths = listField(result, ["chart_path", "chart_paths"]);
  const tracePath = stringField(result, ["trace_path"]);
  const providerMetadata = [
    ["Question understanding", result.question_understanding],
    ["SQL planning", result.sql_planning],
    ["Visualization", result.visualization_trace],
  ].filter(([, value]) => value && typeof value === "object");

  return (
    <section className="stack">
      <h2>Analysis Result</h2>
      {finalAnswer ? (
        <article className="panel">
          <h3>Final Answer</h3>
          <p>{finalAnswer}</p>
        </article>
      ) : null}
      {sql ? (
        <article className="panel">
          <h3>SQL</h3>
          <pre>{sql}</pre>
        </article>
      ) : null}
      {execution ? (
        <article className="panel">
          <h3>Execution Rows</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {execution.columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {execution.rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {execution.columns.map((column, index) => (
                      <td key={column}>{String(rowValue(row, column, index) ?? "")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : null}
      {chartPaths.length ? (
        <article className="panel">
          <h3>Chart Artifacts</h3>
          <ul>
            {chartPaths.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </article>
      ) : null}
      {tracePath ? (
        <article className="panel">
          <h3>Trace</h3>
          <p>{tracePath}</p>
        </article>
      ) : null}
      {providerMetadata.length ? (
        <article className="panel">
          <h3>Provider Metadata</h3>
          <ul>
            {providerMetadata.map(([label, value]) => (
              <li key={label as string}>
                <strong>{label as string}</strong>
                <pre>{JSON.stringify(value, null, 2)}</pre>
              </li>
            ))}
          </ul>
        </article>
      ) : null}
      {!finalAnswer && !sql && !execution && !chartPaths.length && !tracePath ? (
        <p>No result fields returned for this run.</p>
      ) : null}
    </section>
  );
}
