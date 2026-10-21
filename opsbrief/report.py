"""Self-contained HTML; all source text is escaped and no remote assets load."""

from html import escape


def render(report):
    def e(value):
        return escape(str(value), quote=True)

    people = "".join(
        f"<tr><td>{e(p['name'])}</td><td>{p['capacity_hours']:g}</td>"
        f"<td>{p['planned_hours']:g}</td><td>{p['overload_hours']:g}</td>"
        f"<td>{e(', '.join(p['unestimated']) or '—')}</td></tr>"
        for p in report["team"]
    )
    risks = "".join(
        f"<li><strong>{e(r['issue'])} · {e(r['kind'])}</strong> — {e(r['detail'])}</li>"
        for r in report["risks"]
    ) or "<li>No issue flags detected in supplied data.</li>"
    tasks = "".join(
        f"<tr><td>{e(i['key'])}</td><td>{e(i['summary'])}</td>"
        f"<td>{e(i['status'])}</td><td>{e(i['assignee'] or 'Unassigned')}</td>"
        f"<td>{e(i['remaining_hours'] if i['remaining_hours'] is not None else 'Unknown')}</td></tr>"
        for i in report["issues"] if i["planned"] and i["status"] != "done"
    )
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>OpsBrief — weekly facts</title>
<style>
body{{font:16px/1.6 system-ui,sans-serif;background:#f1f5f9;color:#172033;margin:0}}
main{{max-width:1100px;margin:40px auto;padding:28px;background:white;border-radius:16px}}
h1{{color:#164e63;margin-bottom:0}}h2{{margin-top:32px}}
table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ddd}}
th{{background:#eaf3f7}}.note{{background:#fff7dd;padding:14px;border-radius:8px}}
.scroll{{overflow-x:auto}}small{{color:#526174}}
</style><main>
<h1>OpsBrief</h1><p>{e(report['week_start'])} — {e(report['week_end'])}</p>
<p class="note"><strong>Deterministic facts · no AI recommendations yet.</strong><br>
Source: {e(report['source'])}. Captured: {e(report['captured_on'])}.
Analysis date: {e(report['as_of'])}. Snapshot age: {report['snapshot_age_days']} days.</p>
<h2>Team capacity</h2><div class="scroll"><table>
<tr><th>Person</th><th>Available h</th><th>Known planned h</th><th>Overload h</th><th>Unestimated tasks</th></tr>
{people}</table></div>
<p><small>Capacity excludes absence, meetings, operations and reserve. Planned hours include only
explicitly selected open tasks. Unknown estimates are not zero; spare capacity is not proven
when estimates are missing. No automatic assignments are made.</small></p>
<h2>Attention required</h2><ul>{risks}</ul>
<h2>Selected open work</h2><div class="scroll"><table>
<tr><th>Key</th><th>Summary</th><th>Status</th><th>Assignee</th><th>Remaining h</th></tr>
{tasks}</table></div>
<p><small>Local report. No analytics, external fonts or scripts.</small></p>
</main></html>"""
