# OpsBrief

Local-first planning assistant for engineering teams. [Русская версия](README.ru.md).

**Stage 1: working offline facts report.** Jira ingestion, Ollama recommendations,
snapshot history, scheduling and Alice are roadmap items, not implemented features.
No network requests or AI model are required for this demo.

## Quick start

Python 3.11+; no runtime dependencies. From a checkout:

```bash
git clone https://github.com/shilvlad/opsbrief.git
cd opsbrief
python3 -m opsbrief --input examples/demo.json --as-of 2026-10-19
open reports/weekly.html  # macOS; otherwise open in a browser
```

The date is fixed intentionally: the fixture is synthetic and reproducible.
For your own current snapshot, omit `--as-of` to use your local date.
Output: `reports/weekly.html` and `reports/weekly.json` (ignored by Git).

Optional installation: `python3 -m pip install -e .`, then use `opsbrief`.

## What works

- Validate normalized JSON snapshots; reject duplicate IDs, invalid hours and unknown assignees.
- Calculate capacity after absence, meetings, operations and reserve.
- Count only explicitly planned, unfinished work; unknown estimates remain unknown.
- Flag overdue tasks, open/unknown dependencies, missing estimates and unassigned work.
- Render a self-contained HTML report with escaped source text and no external resources.
- Export facts as JSON for a future model adapter; never automatically reassign work.

Demo expectations: DevOps has 20 available hours, 24 known planned hours and 4 hours
overload. DBA has 16 available hours and 8 known planned hours, plus one unestimated
task. This is not proof that DBA has eight free hours. Done/backlog work is excluded.

## Data and calculations

See [the input contract](docs/input.md). Keep real input in `data/` or `local/`.
The CLI accepts normalized snapshots, **not raw Jira exports**. Capacity is for the
whole stated week; it is not prorated by the analysis date. No automatic scheduling,
skill matching or story-point-to-hour conversion is performed.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q opsbrief
```

CI runs tests on Python 3.11 and 3.13 and scans commits with Gitleaks.
CI uses synthetic data only. See [CONTRIBUTING](CONTRIBUTING.md) and [SECURITY](SECURITY.md).

## Roadmap

1. Read-only Jira Data Center adapter: version-aware authentication, pagination,
   custom field/status mapping and complete-snapshot validation.
2. SQLite snapshot history: distinguish completed, removed and inaccessible tasks.
3. Local Ollama/Qwen adapter: bounded context, structured output and validated task references.
4. Weekly availability, skills and proposed allocation with human review.
5. macOS scheduling: retry, locking, VPN availability and explicit freshness.
6. Optional private Alice skill: approved voice summary only; this sends summary text
   outside the local machine and is not an offline feature.

## License

Apache-2.0. See [LICENSE](LICENSE).
