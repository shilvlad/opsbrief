# Normalized snapshot v0.1

See `examples/demo.json` for a complete fixture. Dates use YYYY-MM-DD.

Top-level fields: `source` (nonempty label), `captured_on`, `week_start`, `week_end`,
`team` (array), `issues` (array). Analysis date must not precede snapshot date.

Each person has unique `id`, `name` and numeric nonnegative hour fields:
`working_hours`, `absence_hours`, `meeting_hours`, `operations_hours`, `reserve_hours`.
Deductions must not overlap and their sum must not exceed working hours.
Capacity = working hours minus those four deductions. No implicit 40-hour assumption.

Each issue has unique `key`, `summary`, `assignee` (team ID or null),
`status` (`todo`, `in_progress`, `done`), `planned` (boolean),
`remaining_hours` (nonnegative number or null), `due_date` (date or null),
`blocked_by` (array of blocking task keys).

`planned` explicitly identifies this week's selected scope. It is not inferred
from due date, priority or assignment. Remaining effort is counted in full for
planned open tasks; split work across weeks before importing if appropriate.
Null estimate means unknown, never zero. Zero is a valid known estimate.

A referenced task outside the snapshot has unknown status. A referenced done task
is no longer a blocker. All open overdue tasks are flagged, including backlog;
dependency flags apply to selected work. The tool does not compute a feasible
schedule or infer permission to move assignments.

Store real snapshots in ignored directories. This schema is a local boundary;
the upcoming Jira adapter must map fields and validate pagination before writing it.
