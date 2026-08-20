import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import QueryConsole from "./QueryConsole";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("Privata frontend", () => {
  it("shows the overview with persistent primary navigation", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            dataset_id: "synthetic-workforce",
            name: "Synthetic Workforce",
            row_count: 500,
            safe_for_demo: true,
            schema: { fields: [] },
          },
        ]),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    const navigation = screen.getByRole("navigation", { name: "Primary navigation" });
    expect(navigation).toHaveTextContent("Overview");
    expect(navigation).toHaveTextContent("Datasets");
    expect(navigation).toHaveTextContent("Sessions");
    expect(navigation).toHaveTextContent("Experiments");
    expect(navigation).toHaveTextContent("About Privacy");
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("href", "/");
    expect(screen.getByText("No analysis sessions have been created in this tab.")).toBeInTheDocument();
  });

  it("updates the active navigation state after a browser history event", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    await screen.findByRole("heading", { name: "Overview" });
    window.history.pushState({}, "", "/about-privacy");
    window.dispatchEvent(new PopStateEvent("popstate"));

    expect(await screen.findByRole("heading", { name: "About Privacy" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "About Privacy" })).toHaveAttribute("aria-current", "page");
  });

  it("retries a failed overview dataset load", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              dataset_id: "synthetic-workforce",
              name: "Synthetic Workforce",
              row_count: 500,
              safe_for_demo: true,
              schema: { fields: [] },
            },
          ]),
          { status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load public dataset metadata.");
    await user.click(screen.getByRole("button", { name: "Retry loading datasets" }));

    expect(await screen.findByText("Synthetic Workforce")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("renders public dataset metadata after discovery", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            dataset_id: "synthetic-workforce",
            name: "Synthetic Workforce",
            row_count: 500,
            safe_for_demo: true,
            schema: {
              fields: [
                {
                  name: "age",
                  field_type: "numeric",
                  value_type: "integer",
                  lower_bound: 18,
                  upper_bound: 80,
                  histogram_bins: { edges: [18, 40, 80] },
                },
                {
                  name: "department",
                  field_type: "categorical",
                  categories: ["Engineering", "Sales"],
                },
              ],
            },
          },
        ]),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);
    await user.click(await screen.findByRole("link", { name: "Datasets" }));
    expect(await screen.findByRole("heading", { name: "Datasets" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Synthetic Workforce" }),
    ).toBeInTheDocument();
    expect(screen.getByText("500 public rows")).toBeInTheDocument();
    expect(screen.getByText("Demo eligible")).toBeInTheDocument();
    const schemaTable = screen.getByRole("table", { name: "Public schema" });
    expect(schemaTable).toHaveTextContent("age");
    expect(schemaTable).toHaveTextContent("Numeric");
    expect(schemaTable).toHaveTextContent("18–80");
    expect(schemaTable).toHaveTextContent("department");
    expect(schemaTable).toHaveTextContent("Engineering");
    expect(screen.getByText("2 public bins")).toBeInTheDocument();
    expect(screen.getByText("Show public bin edges")).toBeInTheDocument();
    expect(screen.getByText("18, 40, 80")).toBeInTheDocument();
  });

  it("preselects a dataset when its catalog action opens Sessions", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            dataset_id: "synthetic-workforce",
            name: "Synthetic Workforce",
            row_count: 500,
            safe_for_demo: true,
            schema: { fields: [] },
          },
          {
            dataset_id: "synthetic-health",
            name: "Synthetic Health",
            row_count: 240,
            safe_for_demo: false,
            schema: { fields: [] },
          },
        ]),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);
    await user.click(await screen.findByRole("link", { name: "Datasets" }));
    await user.click(screen.getAllByRole("button", { name: "Create a session for this dataset" })[1]!);

    expect(await screen.findByRole("heading", { name: "Sessions" })).toBeInTheDocument();
    expect(screen.getByLabelText("Dataset")).toHaveValue("synthetic-health");
  });

  it("explains when a direct session route is unavailable in this tab", async () => {
    window.history.replaceState({}, "", "/sessions/not-in-this-tab");
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Session unavailable" })).toBeInTheDocument();
    expect(screen.getByText("Sessions are held only for this tab. Create a new session to begin an analysis.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Create a session" }));
    expect(await screen.findByRole("heading", { name: "Sessions" })).toBeInTheDocument();
  });

  it("creates a demo session before opening the query console", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              dataset_id: "synthetic-workforce",
              name: "Synthetic Workforce",
              row_count: 500,
              safe_for_demo: true,
              schema: {
                fields: [
                  {
                    name: "department",
                    field_type: "categorical",
                    categories: ["Engineering", "Sales"],
                  },
                ],
              },
            },
          ]),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            session_id: "session-1",
            dataset_id: "synthetic-workforce",
            epsilon_total: 2,
            epsilon_spent: 0,
            epsilon_remaining: 2,
            strict_mode: false,
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            session_id: "session-1",
            dataset_id: "synthetic-workforce",
            epsilon_total: 2,
            epsilon_spent: 0,
            epsilon_remaining: 2,
            strict_mode: false,
          }),
          { status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);
    await user.click(await screen.findByRole("link", { name: "Sessions" }));
    await screen.findByRole("heading", { name: "Set up a privacy session" });

    await user.clear(screen.getByLabelText("Total epsilon"));
    await user.type(screen.getByLabelText("Total epsilon"), "2");
    await user.click(screen.getByLabelText("Demo mode"));
    await user.click(screen.getByRole("button", { name: "Create session" }));

    expect(
      await screen.findByRole("heading", { name: "Query console" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Total epsilon").parentElement).toHaveTextContent("2");
    expect(
      screen.getByText("Mode: demo. Ground truth, if returned, is intentionally non-private."),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      new URL("/sessions", "http://127.0.0.1:8000"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          dataset_id: "synthetic-workforce",
          epsilon_total: 2,
          strict_mode: false,
        }),
      }),
    );
  });

  it("provides query controls from the selected public schema", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              dataset_id: "synthetic-workforce",
              name: "Synthetic Workforce",
              row_count: 500,
              safe_for_demo: true,
              schema: {
                fields: [
                  {
                    name: "age",
                    field_type: "numeric",
                    value_type: "integer",
                    lower_bound: 18,
                    upper_bound: 80,
                    histogram_bins: { edges: [18, 40, 80] },
                  },
                  {
                    name: "department",
                    field_type: "categorical",
                    categories: ["Engineering", "Sales"],
                  },
                ],
              },
            },
          ]),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            session_id: "session-1",
            dataset_id: "synthetic-workforce",
            epsilon_total: 2,
            epsilon_spent: 0,
            epsilon_remaining: 2,
            strict_mode: false,
          }),
          { status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);
    await user.click(await screen.findByRole("link", { name: "Sessions" }));
    await screen.findByRole("heading", { name: "Set up a privacy session" });
    await user.click(screen.getByLabelText("Demo mode"));
    await user.click(screen.getByRole("button", { name: "Create session" }));

    await screen.findByLabelText("Query type");
    await user.selectOptions(screen.getByLabelText("Query type"), "HISTOGRAM");

    expect(screen.getByText("Histogram bins: 18–40, 40–80")).toBeInTheDocument();
  });

  it("displays API-returned demo truth after a successful query", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              dataset_id: "synthetic-workforce",
              name: "Synthetic Workforce",
              row_count: 500,
              safe_for_demo: true,
              schema: {
                fields: [
                  {
                    name: "department",
                    field_type: "categorical",
                    categories: ["Engineering", "Sales"],
                  },
                ],
              },
            },
          ]),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            session_id: "session-1",
            dataset_id: "synthetic-workforce",
            epsilon_total: 2,
            epsilon_spent: 0,
            epsilon_remaining: 2,
            strict_mode: false,
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            query_id: "query-1",
            query_type: "COUNT_CATEGORY",
            dataset_id: "synthetic-workforce",
            epsilon_charged: 0.1,
            epsilon_remaining: 1.9,
            sensitivity: 1,
            mechanism_name: "laplace",
            mechanism_scale: 10,
            timestamp: "2026-08-18T00:00:00Z",
            noisy_result: 80.77935755000792,
            true_result: 120,
            true_result_is_demo: true,
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            session_id: "session-1",
            dataset_id: "synthetic-workforce",
            epsilon_total: 2,
            epsilon_spent: 0.1,
            epsilon_remaining: 1.9,
            strict_mode: false,
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              query_id: "query-1",
              query_type: "COUNT_CATEGORY",
              epsilon_charged: 0.1,
              epsilon_remaining: 1.9,
              timestamp: "2026-08-18T00:00:00Z",
            },
          ]),
          { status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);
    await user.click(await screen.findByRole("link", { name: "Sessions" }));
    await screen.findByRole("heading", { name: "Set up a privacy session" });
    await user.click(screen.getByLabelText("Demo mode"));
    await user.click(screen.getByRole("button", { name: "Create session" }));
    await screen.findByLabelText("Query type");
    await user.click(screen.getByRole("button", { name: "Run query" }));

    expect(await screen.findByText("80.78")).toBeInTheDocument();
    expect(screen.getByText("Noisy result")).toBeInTheDocument();
    expect(screen.getByText("Show full precision")).toBeInTheDocument();
    expect(screen.getByText("80.77935755000792")).toBeInTheDocument();
    expect(screen.getByText("Sensitivity")).toBeInTheDocument();
    expect(screen.getByText("Laplace scale")).toBeInTheDocument();
    expect(
      screen.getByText("Demo ground truth (intentionally non-private): 120"),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      new URL("/sessions/session-1/queries", "http://127.0.0.1:8000"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          query_type: "COUNT_CATEGORY",
          field: "department",
          category: "Engineering",
          epsilon: 0.1,
        }),
      }),
    );
    const historyTable = screen.getByRole("table", { name: "Query history" });
    expect(historyTable).toHaveTextContent("Query type");
    expect(historyTable).toHaveTextContent("Epsilon charged");
    expect(historyTable).toHaveTextContent("Remaining epsilon");
    expect(historyTable).toHaveTextContent("COUNT_CATEGORY");
    expect(historyTable).toHaveTextContent("0.1");
    expect(historyTable).toHaveTextContent("1.9");
    await user.click(screen.getByRole("link", { name: "Overview" }));
    expect(await screen.findByText("Active session for synthetic-workforce")).toBeInTheDocument();
    expect(screen.getByText("Remaining epsilon").parentElement).toHaveTextContent("1.9");
  });

  it("explains all four reference experiment categories", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            dataset_id: "synthetic-workforce",
            name: "Synthetic Workforce",
            row_count: 500,
            safe_for_demo: true,
            schema: { fields: [] },
          },
        ]),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);
    await user.click(await screen.findByRole("link", { name: "Experiments" }));

    expect(
      screen.getByRole("heading", { name: "Reference experiments" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Privacy vs. utility")).toBeInTheDocument();
    expect(screen.getByText("Dataset size vs. mean utility")).toBeInTheDocument();
    expect(screen.getByText("Sequential composition")).toBeInTheDocument();
    expect(screen.getByText("Neighboring-dataset distributions")).toBeInTheDocument();
    expect(
      screen.getByText(/Empirical overlap is illustrative, not a formal differential privacy proof/),
    ).toBeInTheDocument();
  });

  it("shows a structured query error without changing displayed accounting", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "BUDGET_EXCEEDED",
            message: "Requested epsilon exceeds the remaining privacy budget.",
            details: { requested_epsilon: 0.1, remaining_epsilon: 0.05 },
          },
        }),
        { status: 409 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(
      <QueryConsole
        dataset={{
          dataset_id: "synthetic-workforce",
          name: "Synthetic Workforce",
          row_count: 500,
          safe_for_demo: true,
          schema: {
            fields: [
              {
                name: "department",
                field_type: "categorical",
                categories: ["Engineering"],
              },
            ],
          },
        }}
        session={{
          session_id: "session-1",
          dataset_id: "synthetic-workforce",
          epsilon_total: 2,
          epsilon_spent: 0,
          epsilon_remaining: 2,
          strict_mode: true,
        }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Run query" }));

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("Requested epsilon exceeds the remaining privacy budget.");
    expect(screen.getByText("Total epsilon").parentElement).toHaveTextContent("2");
    expect(screen.queryByLabelText("Query release")).not.toBeInTheDocument();
  });

  it("does not display an unlabeled true result in strict mode", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            query_id: "query-1",
            query_type: "COUNT_CATEGORY",
            dataset_id: "synthetic-workforce",
            epsilon_charged: 0.1,
            epsilon_remaining: 1.9,
            sensitivity: 1,
            mechanism_name: "laplace",
            mechanism_scale: 10,
            timestamp: "2026-08-18T00:00:00Z",
            noisy_result: 121.4,
            true_result: 120,
            true_result_is_demo: true,
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            session_id: "session-1",
            dataset_id: "synthetic-workforce",
            epsilon_total: 2,
            epsilon_spent: 0.1,
            epsilon_remaining: 1.9,
            strict_mode: true,
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(
      <QueryConsole
        dataset={{
          dataset_id: "synthetic-workforce",
          name: "Synthetic Workforce",
          row_count: 500,
          safe_for_demo: true,
          schema: {
            fields: [
              {
                name: "department",
                field_type: "categorical",
                categories: ["Engineering"],
              },
            ],
          },
        }}
        session={{
          session_id: "session-1",
          dataset_id: "synthetic-workforce",
          epsilon_total: 2,
          epsilon_spent: 0,
          epsilon_remaining: 2,
          strict_mode: true,
        }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Run query" }));

    expect(await screen.findByLabelText("Noisy result")).toHaveTextContent("121.4");
    expect(screen.queryByText(/Demo ground truth/)).not.toBeInTheDocument();
  });
});
