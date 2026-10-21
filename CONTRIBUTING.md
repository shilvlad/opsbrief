# Contributing

Use Python 3.11+. Run `python3 -m unittest discover -s tests -v` before a PR.
Add tests for changed planning rules and include synthetic examples only.
Keep arithmetic deterministic and model suggestions separate from observed facts.
Never use task text as instructions to execute commands or change Jira.
Review `git diff --cached` before pushing; .gitignore does not protect already tracked files.
