# Privata demo script

This is a 2-4 minute technical demo. Start the backend and frontend using the commands in the README. Open the frontend at the Vite URL, usually `http://127.0.0.1:5173`.

## 0:00-0:30: Establish the model

Show the setup page and select **Synthetic Workforce**. Point out that it has 500 synthetic rows, public `age` bounds of 18 to 80, public `annual_income` bounds of 20,000 to 200,000, and declared department categories. State: "One row is one privacy unit. Neighbors have the same row count and differ in at most one row. This is replacement adjacency."

Create a **strict** session with total epsilon `2.0`. The session begins with 2.0 remaining.

## 0:30-1:25: Run the three releases

Run these queries with epsilon `0.5` each:

1. `COUNT_CATEGORY`, field `department`, category `Engineering`.
2. `MEAN`, field `age`.
3. `HISTOGRAM`, field `department`.

For each result, show the noisy answer, `sensitivity`, `mechanism_scale`, and remaining epsilon. Explain the values shown by the UI:

- The count has sensitivity 1, so its scale is $1 / 0.5 = 2$.
- The age mean has sensitivity $(80-18)/500 = 0.124$, so its scale is 0.248.
- The department histogram has vector $L_1$ sensitivity 2, so each bin has scale $2 / 0.5 = 4$.

Confirm that the strict responses do not show a true result. The absence of a true result matters: the noisy release is the protected output.

## 1:25-1:45: Exhaust the budget

After the three releases, 0.5 epsilon remains. Submit another mean with epsilon `0.75`. Show the budget rejection. It reports the requested 0.75 and remaining 0.5, and it does not run the mechanism or charge budget.

## 1:45-2:20: Compare strict and demo behavior

Create a second session with total epsilon `0.5` and **demo mode** selected. Run the same Engineering category count at epsilon `0.5`.

Compare the two responses: strict mode contains only the noisy result; demo mode contains a `true_result` marked `true_result_is_demo: true`. Say plainly: "This true value is exposed only because this built-in synthetic dataset is explicitly safe for demonstration. It is not a differentially private release."

## 2:20-3:05: Show experiment artifacts

Open `experiments/output/privacy_utility.png`. State the recorded seeded finding: at epsilon 0.05 to 5, category-count MAE fell from 19.84 to 0.21, and histogram mean $L_1$ error fell from 199.89 to 2.02 over 5,000 trials.

Open `experiments/output/neighboring_datasets.png`. Explain that the pair has the same size and differs in one department value, so its true Engineering counts are 89 and 88. The plot visualizes sampled noisy outputs at several epsilons. It illustrates behavior only; it is not a proof of DP.

## 3:05-3:25: One design tradeoff

State the tradeoff: "Privata uses fixed-size replacement adjacency because dataset size is public and fixed. That makes the category-count sensitivity 1, the bounded-mean sensitivity $(U-L)/n$, and histogram vector $L_1$ sensitivity 2. If the system instead allowed someone to enter or leave the dataset, the adjacency model and some sensitivity arguments would change, so we do not silently substitute add/remove formulas."

End by showing the privacy budget and release metadata again: each accepted answer has an explicit sensitivity, Laplace scale, charged epsilon, and remaining epsilon.

## Optional HTTP fallback

If the UI is unavailable, use PowerShell against the running API. Create a strict session, then substitute its `session_id` in the query URL:

```powershell
$session = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/sessions' -ContentType 'application/json' -Body '{"dataset_id":"synthetic-workforce","epsilon_total":2.0,"strict_mode":true}'
$session
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/sessions/$($session.session_id)/queries" -ContentType 'application/json' -Body '{"query_type":"COUNT_CATEGORY","field":"department","category":"Engineering","epsilon":0.5}'
```
