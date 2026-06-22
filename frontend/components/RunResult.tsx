import React from "react";

type RunResultProps = {
  result: {
    generated_sql?: string;
    execution_result?: {
      columns: string[];
      rows: unknown[][];
    };
  };
};

export default function RunResult({ result }: RunResultProps) {
  const execution = result.execution_result;

  return (
    <section>
      <h2>Analysis Result</h2>
      {result.generated_sql ? <pre>{result.generated_sql}</pre> : null}
      {execution ? (
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
                {row.map((value, index) => (
                  <td key={index}>{String(value)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
