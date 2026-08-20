import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import QueryConsole from "./QueryConsole";

afterEach(cleanup);

describe("QueryConsole", () => {
  it("formats floating-point budget totals without binary precision artifacts", () => {
    render(
      <QueryConsole
        dataset={{
          dataset_id: "synthetic-workforce",
          name: "Synthetic Workforce",
          row_count: 500,
          safe_for_demo: true,
          schema: { fields: [] },
        }}
        session={{
          session_id: "session-1",
          dataset_id: "synthetic-workforce",
          epsilon_total: 1,
          epsilon_spent: 0.30000000000000004,
          epsilon_remaining: 0.7,
          strict_mode: true,
        }}
      />,
    );

    expect(screen.getByText("Spent epsilon").parentElement).toHaveTextContent("0.3");
    expect(screen.queryByText("0.30000000000000004")).not.toBeInTheDocument();
  });
});
