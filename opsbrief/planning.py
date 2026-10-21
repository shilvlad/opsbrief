"""Validate normalized snapshots and calculate capacity without an LLM."""

import math
from datetime import date


def hours(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field}: expected a number")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field}: expected finite nonnegative hours")
    return value


def required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected nonempty text")
    return value


def analyze(snapshot, as_of):
    """planned=True is explicit scope, not an inference from all open work.

    Capacity values belong to the supplied week. This function does not prorate
    them by as_of, infer estimates, assign people, or schedule dependencies.
    """
    start = date.fromisoformat(snapshot["week_start"])
    end = date.fromisoformat(snapshot["week_end"])
    captured = date.fromisoformat(snapshot["captured_on"])
    if end < start:
        raise ValueError("week_end must not precede week_start")
    if captured > as_of:
        raise ValueError("snapshot is dated in the future")
    team = snapshot["team"]
    issues = snapshot["issues"]
    if not isinstance(team, list) or not isinstance(issues, list):
        raise ValueError("team and issues must be arrays")
    people = {}
    for person in team:
        name = required_text(person["id"], "person.id")
        if name in people:
            raise ValueError(f"duplicate person: {name}")
        available = hours(person["working_hours"], "working_hours")
        deductions = sum(hours(person[field], field) for field in (
            "absence_hours", "meeting_hours", "operations_hours", "reserve_hours"
        ))
        if deductions > available:
            raise ValueError(f"{name}: deductions exceed working hours")
        people[name] = {
            "id": name, "name": required_text(person["name"], "person.name"),
            "capacity_hours": available - deductions,
            "planned_hours": 0, "unestimated": [],
        }
    seen = set()
    risks = []
    normalized = []
    for issue in issues:
        key = required_text(issue["key"], "issue.key")
        if key in seen:
            raise ValueError(f"duplicate issue: {key}")
        seen.add(key)
        required_text(issue["summary"], "issue.summary")
        if issue["status"] not in {"todo", "in_progress", "done"}:
            raise ValueError(f"{key}: unsupported normalized status")
        if type(issue["planned"]) is not bool:
            raise ValueError(f"{key}: planned must be boolean")
        assignee = issue["assignee"]
        if assignee is not None and assignee not in people:
            raise ValueError(f"{key}: unknown assignee {assignee}")
        estimate = issue["remaining_hours"]
        if estimate is not None:
            hours(estimate, "remaining_hours")
        due = date.fromisoformat(issue["due_date"]) if issue["due_date"] else None
        blockers = issue["blocked_by"]
        if not isinstance(blockers, list):
            raise ValueError(f"{key}: blocked_by must be an array")
        for blocker in blockers:
            required_text(blocker, "blocked_by")
        normalized.append(dict(issue))
        if issue["status"] == "done":
            continue
        if due and due < as_of:
            risks.append({"kind": "overdue", "issue": key,
                          "detail": f"Due {due.isoformat()}"})
        if issue["planned"]:
            if assignee is None:
                risks.append({"kind": "unassigned", "issue": key,
                              "detail": "Planned work has no assignee"})
            elif estimate is None:
                people[assignee]["unestimated"].append(key)
            else:
                people[assignee]["planned_hours"] += estimate
            if estimate is None:
                risks.append({"kind": "missing_estimate", "issue": key,
                              "detail": "Remaining effort is unknown"})
    statuses = {issue["key"]: issue["status"] for issue in normalized}
    for issue in normalized:
        if issue["status"] == "done" or not issue["planned"]:
            continue
        for blocker in issue["blocked_by"]:
            if statuses.get(blocker) != "done":
                risks.append({
                    "kind": "blocked" if blocker in statuses else "unknown_dependency",
                    "issue": issue["key"],
                    "detail": f"Depends on {blocker}" + (
                        " (not in snapshot; status unknown)" if blocker not in statuses else ""
                    ),
                })
    for person in people.values():
        person["overload_hours"] = max(0, person["planned_hours"] - person["capacity_hours"])
    return {
        "source": required_text(snapshot["source"], "source"),
        "week_start": start.isoformat(), "week_end": end.isoformat(),
        "captured_on": captured.isoformat(), "as_of": as_of.isoformat(),
        "snapshot_age_days": (as_of - captured).days,
        "team": list(people.values()), "issues": normalized, "risks": risks,
    }
