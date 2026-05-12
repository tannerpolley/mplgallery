# GoalBuddy-Managed Tauri React Overhaul

## Objective

Manage the MPLGallery overhaul through GoalBuddy: replace the current Streamlit-hosted, plot-editing-oriented app with a Tauri + React Windows desktop app for fast local browsing of CSV, PNG, and SVG files.

## Original Request

Create a GoalBuddy board before implementation for the full overhaul from Streamlit/plot-editing app to a Tauri + React desktop app. The board must live at `docs/goals/tauri-react-overhaul/` and be the source of truth for sequencing, scope, receipts, verification, and completion.

## Intake Summary

- Input shape: `existing_plan`
- Audience: the repo owner and future Codex/GoalBuddy agents implementing the overhaul.
- Authority: `requested`
- Proof type: `artifact`
- Completion proof: the GoalBuddy control files exist, pass the board checker, and provide the starter command `/goal Follow docs/goals/tauri-react-overhaul/goal.md.`
- Likely misfire: building Tauri code or removing Streamlit immediately instead of first creating the board and enforcing GoalBuddy task gates.
- Blind spots considered: Python-free runtime boundary, side-by-side cutover risk, preserving loose image discovery, Windows installer/update continuity, and avoiding plot-editing scope creep.
- Existing plan facts: Tauri + React is locked; migration is side-by-side first; the installed app should not require Python at runtime; loose PNG/SVG files must be classified and discoverable; plot editing, Matplotlib redraw, YAML editing, and generated-plot controls are out of scope for the new app.

## Goal Kind

`existing_plan`

## Current Tranche

Create the GoalBuddy board and starter command for the overhaul. The first execution task is Scout discovery, not implementation. After `/goal` starts, the PM should keep advancing through safe verified Scout, Judge, and Worker slices until the full migration outcome is complete.

## Non-Negotiable Constraints

- GoalBuddy `state.yaml` is board truth.
- At most one active task at a time.
- Do not implement product changes outside an active Worker or PM task that permits them.
- Worker tasks must include `allowed_files`, `verify`, and `stop_if`.
- Tauri + React is the target runtime.
- The finished installed Windows app must not require Python, Streamlit, Matplotlib, pandas, or pywebview at runtime.
- Existing Python code may be used as a reference during migration, but not as a required runtime dependency for the final installed app.
- Preserve discovery of unrelated loose PNG/SVG files by classifying them separately from analysis-linked assets.
- Do not remove the current Streamlit app until the Tauri app reaches verified parity.
- Browser verification and a design audit are required before final completion.

## Stop Rule

Stop only when a final audit proves the full original outcome is complete.

Do not stop after planning, discovery, or Judge selection if a safe Worker task can be activated.

Do not stop after a single verified Worker slice when the broader owner outcome still has safe local follow-up slices. After each slice audit, advance the board to the next highest-leverage safe Worker task and continue.

Do not stop because a slice needs owner input, credentials, production access, destructive operations, or policy decisions. Mark that exact slice blocked with a receipt, create the smallest safe follow-up or workaround task, and continue all local, non-destructive work that can still move the goal toward the full outcome.

## Canonical Board

Machine truth lives at:

`docs/goals/tauri-react-overhaul/state.yaml`

If this charter and `state.yaml` disagree, `state.yaml` wins for task status, active task, receipts, verification freshness, and completion truth.

## Run Command

```text
/goal Follow docs/goals/tauri-react-overhaul/goal.md.
```

## PM Loop

On every `/goal` continuation:

1. Read this charter.
2. Read `state.yaml`.
3. Run the bundled GoalBuddy update checker when available and mention a newer version without blocking.
4. Re-check the intake: original request, input shape, authority, proof, blind spots, existing plan facts, and likely misfire.
5. Work only on the active board task.
6. Assign Scout, Judge, Worker, or PM according to the task.
7. Write a compact task receipt.
8. Update the board.
9. If Judge selected a safe Worker task with `allowed_files`, `verify`, and `stop_if`, activate it and continue unless blocked.
10. Treat a slice audit as a checkpoint, not completion, unless it explicitly proves the full original outcome is complete.
11. Finish only with a Judge/PM audit receipt that maps receipts and verification back to the original user outcome and records `full_outcome_complete: true`.

Issue and PR handoffs are supporting artifacts. `state.yaml` remains authoritative, and every external artifact decision must be recorded in a task receipt.
