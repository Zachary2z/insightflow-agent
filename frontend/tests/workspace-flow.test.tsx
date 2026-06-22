import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ProfileSummary from "../components/ProfileSummary";
import RunResult from "../components/RunResult";

describe("workspace product components", () => {
  it("renders profile tables and candidate roles", () => {
    render(
      <ProfileSummary
        profile={{
          tables: [
            {
              table_name: "orders",
              row_count: 10,
              columns: [
                { name: "revenue", role_candidates: { measure: true } },
                { name: "channel", role_candidates: { dimension: true } },
              ],
            },
          ],
        }}
      />,
    );
    expect(screen.getByText("orders")).toBeTruthy();
    expect(screen.getByText("revenue")).toBeTruthy();
    expect(screen.getByText("measure")).toBeTruthy();
  });

  it("renders SQL and execution rows for a run result", () => {
    render(
      <RunResult
        result={{
          generated_sql: "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
          execution_result: { columns: ["channel", "revenue"], rows: [["email", 100]] },
        }}
      />,
    );
    expect(screen.getByText(/SELECT channel/)).toBeTruthy();
    expect(screen.getByText("email")).toBeTruthy();
  });
});
