# Architecture

The browser loads only this project’s `web/project.js` plus local copies of rendering/form helpers (`lib.js`) and spatial/visual helpers (`studio.js`). Requests reach the local threaded HTTP API in `lab/server.py`, which dispatches to `lab/robot.py`. SQLite stores states and run history. Background tasks run in a bounded thread pool, with cooperative cancellation at checked iterations. Generated media and model files are written under `runtime/`.

## Boundaries

The engine owns domain state; the client renders it and submits actions. Validation and invariants are implemented on the server. The local server rejects cross-origin writes and limits JSON/upload sizes. It is a single-user loopback service; public deployment requires a production server, authentication, resource controls and durable backups. A thread is not an isolation boundary for hostile code.

## Reading order

1. `catalog.json` and `app.py`.
2. `lab/robot.py`: actions and evaluation.
3. `lab/core.py`: paths, serialization and shared utilities.
4. `lab/server.py`: request routing, persistence and jobs.
5. `web/project.js`: domain interface.
6. `tests/`: behavioural and API checks.


## V2 client structure

`app.js` owns navigation, jobs and live stepping; `project.js` owns the domain workspace; `studio.js` contains the offline icon, graph, plot and grid helpers; `style.css` holds project themes and responsive rules. Every dependency is inside this repository. Local fonts and their SIL OFL notice are bundled in `web/`.
