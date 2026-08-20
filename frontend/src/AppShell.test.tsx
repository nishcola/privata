import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { BudgetSummary } from "./AppShell";

afterEach(cleanup);

describe("BudgetSummary", () => {
  it("renders floating-point accounting values without binary precision artifacts", () => {
    render(
      <BudgetSummary
        epsilonTotal={1}
        epsilonSpent={0.30000000000000004}
        epsilonRemaining={0.7}
      />,
    );

    expect(screen.getByText("Spent epsilon").parentElement).toHaveTextContent("0.3");
    expect(screen.queryByText("0.30000000000000004")).not.toBeInTheDocument();
  });
});
