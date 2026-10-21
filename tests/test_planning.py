import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from opsbrief.planning import analyze
from opsbrief.report import render

ROOT = Path(__file__).resolve().parents[1]


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'examples/demo.json').read_text())

    def report(self):
        return analyze(self.data, date(2026, 10, 19))

    def test_capacity_and_scope(self):
        devops, dba = self.report()['team']
        self.assertEqual((devops['capacity_hours'], devops['planned_hours'], devops['overload_hours']), (20, 24, 4))
        self.assertEqual((dba['capacity_hours'], dba['planned_hours']), (16, 8))
        self.assertEqual(dba['unestimated'], ['DEMO-3'])

    def test_dependency_and_missing_data_flags(self):
        flags = {(r['issue'], r['kind']) for r in self.report()['risks']}
        self.assertIn(('DEMO-2', 'overdue'), flags)
        self.assertIn(('DEMO-3', 'blocked'), flags)
        self.assertIn(('DEMO-3', 'missing_estimate'), flags)
        self.assertIn(('DEMO-4', 'unassigned'), flags)
        self.assertIn(('DEMO-4', 'unknown_dependency'), flags)

    def test_done_dependency_is_not_blocker(self):
        self.data['issues'][1]['status'] = 'done'
        self.assertFalse(any(r['kind'] == 'blocked' for r in self.report()['risks']))

    def test_due_today_is_not_overdue(self):
        self.data['issues'][1]['due_date'] = '2026-10-19'
        self.assertFalse(any(r['kind'] == 'overdue' for r in self.report()['risks']))

    def test_zero_is_known_estimate(self):
        self.data['issues'][2]['remaining_hours'] = 0
        self.assertEqual(self.report()['team'][1]['unestimated'], [])

    def test_invalid_numbers(self):
        for value in (-1, float('nan'), float('inf'), True, '8'):
            with self.subTest(value=value):
                self.data['issues'][0]['remaining_hours'] = value
                with self.assertRaises(ValueError):
                    self.report()

    def test_overdeducted_capacity(self):
        self.data['team'][0]['absence_hours'] = 40
        with self.assertRaises(ValueError):
            self.report()

    def test_duplicates(self):
        for field in ('team', 'issues'):
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                data[field].append(data[field][0])
                with self.assertRaises(ValueError):
                    analyze(data, date(2026, 10, 19))

    def test_unknown_assignee(self):
        self.data['issues'][0]['assignee'] = 'not-in-team'
        with self.assertRaises(ValueError):
            self.report()

    def test_freshness_and_future_snapshot(self):
        self.assertEqual(analyze(self.data, date(2026, 10, 21))['snapshot_age_days'], 2)
        with self.assertRaises(ValueError):
            analyze(self.data, date(2026, 10, 18))

    def test_html_escapes_imported_content(self):
        self.data['issues'][0]['summary'] = '<script>alert(1)</script>'
        self.data['team'][0]['name'] = '<img src=x onerror=alert(1)>'
        html = render(self.report())
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img', html)
        self.assertIn('&lt;script&gt;', html)

    def test_cli_produces_html_and_json(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'weekly.html'
            result = subprocess.run([sys.executable, '-m', 'opsbrief', '--input',
                str(ROOT / 'examples/demo.json'), '--as-of', '2026-10-19',
                '--output', str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('OpsBrief', output.read_text())
            self.assertEqual(json.loads(output.with_suffix('.json').read_text())['team'][0]['overload_hours'], 4)

    def test_cli_rejects_bad_input_without_report(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'bad.json'
            source.write_text('{}')
            output = Path(directory) / 'weekly.html'
            result = subprocess.run([sys.executable, '-m', 'opsbrief', '--input', str(source),
                '--output', str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
