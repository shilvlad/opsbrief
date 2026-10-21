# Data boundaries

The current CLI reads local JSON and writes local HTML/JSON; it has no network client.
Reports escape imported text and load no third-party scripts or assets.

Never commit real Jira snapshots, credentials, internal hostnames, employee details,
SQLite databases or generated work reports. Keep them in `data/`, `local/`, `reports/`
or outside the checkout. Ignore rules and secret scanning are safeguards, not guarantees.
Future adapters must use read-only access, verify TLS and avoid logging secrets.
Do not paste sensitive data into public issues. Use GitHub private vulnerability
reporting if enabled; otherwise contact the maintainer privately before sharing details.
