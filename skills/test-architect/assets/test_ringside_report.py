#!/usr/bin/env python3
"""Ringmaster — battery for the Ringside report generator (stdlib only).

Mirrors the hooks/test_*.py suites: no third-party deps, cross-platform, and it
asserts the load-bearing promises of skills/test-architect/assets/ringside_report.py
— schema validation, coverage/thin detection, HTML-escaping of untrusted ticket
text (XSS), correct CSV quoting, and the CLI exit codes.
"""
import os
import sys
import json
import tempfile
import shutil
import unittest

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ringside_report as rr  # noqa: E402


def _valid_data():
    return {
        "meta": {"project": "acme", "tracker": "jira", "persona": "Ringside",
                 "generatedAt": "2026-07-06T00:00:00Z"},
        "requirements": [
            {"id": "PROJ-1/AC1", "sourceRef": "JIRA:PROJ-1", "origin": "jira",
             "text": "A member can withdraw up to their available balance."},
            {"id": "PROJ-1/AC2", "sourceRef": "JIRA:PROJ-1", "origin": "jira",
             "text": "A withdrawal emits an audit event."},
        ],
        "gaps": [],
        "assumptions": [
            {"id": "A1", "text": "Non-positive amounts are rejected",
             "reason": "not stated", "relatedRequirement": "PROJ-1/AC1"},
        ],
        "scenarios": [
            {"id": "S1", "requirementId": "PROJ-1/AC1",
             "given": "a member with balance 100.00", "when": "they withdraw 100.00",
             "then": "the request succeeds and the balance is 0",
             "testType": "api", "priority": "P1", "risk": "high",
             "source": "jira", "edgeCase": False, "category": "happy",
             "assumptionBased": False},
            {"id": "S2", "requirementId": "PROJ-1/AC1",
             "given": "a member with balance 100.00", "when": "they withdraw 100.01",
             "then": "the request is rejected as insufficient funds",
             "testType": "api", "priority": "P1", "risk": "high",
             "source": "ringside", "edgeCase": True, "category": "boundary",
             "assumptionBased": False},
        ],
    }


class ValidateTests(unittest.TestCase):
    def test_accepts_minimal_valid(self):
        self.assertEqual(rr.validate(_valid_data()), [])

    def test_rejects_non_dict(self):
        self.assertTrue(rr.validate([]))

    def test_rejects_unknown_requirement_reference(self):
        d = _valid_data()
        d["scenarios"][0]["requirementId"] = "GHOST/AC9"
        errs = rr.validate(d)
        self.assertTrue(any("GHOST/AC9" in e for e in errs), errs)

    def test_rejects_bad_priority_enum(self):
        d = _valid_data()
        d["scenarios"][0]["priority"] = "P9"
        self.assertTrue(any("priority" in e for e in rr.validate(d)))

    def test_rejects_bad_source_enum(self):
        d = _valid_data()
        d["scenarios"][0]["source"] = "developer"
        self.assertTrue(any("source" in e for e in rr.validate(d)))

    def test_rejects_bad_category_enum(self):
        d = _valid_data()
        d["scenarios"][0]["category"] = "vibes"
        self.assertTrue(any("category" in e for e in rr.validate(d)))

    def test_rejects_duplicate_scenario_id(self):
        d = _valid_data()
        d["scenarios"][1]["id"] = "S1"
        self.assertTrue(any("duplicate" in e.lower() for e in rr.validate(d)))

    def test_rejects_missing_given_when_then(self):
        d = _valid_data()
        del d["scenarios"][0]["then"]
        self.assertTrue(any("then" in e for e in rr.validate(d)))

    def test_rejects_duplicate_requirement_id(self):
        d = _valid_data()
        d["requirements"][1]["id"] = "PROJ-1/AC1"
        self.assertTrue(any("duplicate" in e.lower() for e in rr.validate(d)))


class CoverageTests(unittest.TestCase):
    def test_happy_plus_boundary_without_failure_is_thin(self):
        # The F1 fix: happy + boundary but NO failure path is THIN — a failure gap
        # is where real incidents hide, so boundary coverage alone must not lift it.
        cov = rr.coverage_by_requirement(_valid_data())  # AC1 = happy + boundary
        self.assertTrue(cov["PROJ-1/AC1"]["thin"])
        self.assertIn("failure", cov["PROJ-1/AC1"]["missing"])
        self.assertNotIn("happy", cov["PROJ-1/AC1"]["missing"])
        self.assertEqual(cov["PROJ-1/AC1"]["total"], 2)

    def test_uncovered_requirement_flagged(self):
        cov = rr.coverage_by_requirement(_valid_data())
        self.assertEqual(cov["PROJ-1/AC2"]["total"], 0)
        self.assertTrue(cov["PROJ-1/AC2"]["uncovered"])

    def test_happy_only_is_thin_missing_failure(self):
        d = _valid_data()
        d["scenarios"] = [d["scenarios"][0]]  # keep only the happy-path scenario
        cov = rr.coverage_by_requirement(d)
        self.assertTrue(cov["PROJ-1/AC1"]["thin"])
        self.assertIn("failure", cov["PROJ-1/AC1"]["missing"])

    def test_happy_plus_failure_is_ok(self):
        d = _valid_data()
        d["scenarios"][1]["category"] = "failure"  # AC1 = happy + failure
        cov = rr.coverage_by_requirement(d)
        self.assertFalse(cov["PROJ-1/AC1"]["thin"])
        self.assertEqual(cov["PROJ-1/AC1"]["missing"], [])

    def test_nonhappy_only_flags_missing_happy_and_failure(self):
        # A requirement exercised only on a security probe (no happy, no failure)
        # must be flagged — the old heuristic silently passed it as OK.
        d = _valid_data()
        d["scenarios"] = [d["scenarios"][1]]         # keep one scenario…
        d["scenarios"][0]["category"] = "security"   # …and make it security-only
        cov = rr.coverage_by_requirement(d)
        self.assertTrue(cov["PROJ-1/AC1"]["thin"])
        self.assertIn("happy", cov["PROJ-1/AC1"]["missing"])
        self.assertIn("failure", cov["PROJ-1/AC1"]["missing"])


class HtmlTests(unittest.TestCase):
    def test_escapes_untrusted_ticket_text(self):
        d = _valid_data()
        payload = "<script>alert('xss')</script>"
        d["scenarios"][0]["then"] = payload
        d["requirements"][0]["text"] = payload
        out = rr.render_html(d)
        self.assertNotIn(payload, out)              # raw injection must never appear
        self.assertNotIn("<script", out.lower())     # report is static: no script tags at all
        self.assertIn("&lt;script&gt;", out)         # the escaped form is present

    def test_contains_requirement_and_scenario_ids(self):
        out = rr.render_html(_valid_data())
        for token in ("PROJ-1/AC1", "PROJ-1/AC2", "S1", "S2"):
            self.assertIn(token, out)

    def test_is_theme_aware(self):
        out = rr.render_html(_valid_data())
        self.assertIn("prefers-color-scheme", out)

    def test_surfaces_thin_and_uncovered(self):
        out = rr.render_html(_valid_data()).lower()
        self.assertIn("uncovered", out)  # AC2 has no scenarios and must be surfaced

    def test_thin_requirement_names_its_gap(self):
        # A THIN requirement must tell the reader which dimension is missing, so the
        # flag is actionable rather than opaque. AC1 = happy + boundary → needs failure.
        out = rr.render_html(_valid_data())
        self.assertIn("needs failure", out)


class CsvTests(unittest.TestCase):
    def test_header_and_one_row_per_scenario(self):
        text = rr.render_csv(_valid_data())
        lines = [ln for ln in text.splitlines() if ln.strip()]
        self.assertIn("requirement_id", lines[0])
        self.assertIn("scenario_id", lines[0])
        self.assertTrue(any(ln.startswith("PROJ-1/AC1") and "S1" in ln for ln in lines))

    def test_quotes_fields_with_commas(self):
        import csv as _csv
        import io as _io
        d = _valid_data()
        d["scenarios"][0]["then"] = "rejected, with a reason, containing commas"
        text = rr.render_csv(d)
        rows = list(_csv.reader(_io.StringIO(text)))
        # the comma-laden field must round-trip as a single cell
        self.assertTrue(any("rejected, with a reason, containing commas" in cell
                            for row in rows for cell in row))

    def test_includes_uncovered_requirement_row(self):
        text = rr.render_csv(_valid_data())
        self.assertTrue(any("PROJ-1/AC2" in ln and "UNCOVERED" in ln
                            for ln in text.splitlines()))

    def test_neutralizes_formula_injection(self):
        import csv as _csv
        import io as _io
        d = _valid_data()
        d["scenarios"][0]["then"] = '=HYPERLINK("http://evil","click")'
        text = rr.render_csv(d)
        rows = list(_csv.reader(_io.StringIO(text)))
        hits = [cell for row in rows for cell in row if "HYPERLINK" in cell]
        self.assertTrue(hits)
        for cell in hits:
            self.assertFalse(cell.startswith("="), cell)   # no longer a live formula
            self.assertTrue(cell.startswith("'="), cell)    # neutralized as literal text


class RobustnessTests(unittest.TestCase):
    """Untrusted ticket JSON must never crash the tool with a raw traceback
    (the Security Gate's 🟡 finding). Each case here is a shape the gate reproduced."""

    def test_validate_rejects_unhashable_requirement_id(self):
        d = _valid_data()
        d["requirements"][0]["id"] = ["not", "a", "string"]
        self.assertTrue(rr.validate(d))  # reports an error rather than raising TypeError

    def test_validate_rejects_unhashable_scenario_id(self):
        d = _valid_data()
        d["scenarios"][0]["id"] = {"weird": 1}
        self.assertTrue(rr.validate(d))

    def test_validate_rejects_non_dict_gap(self):
        d = _valid_data()
        d["gaps"] = ["just a string, not an object"]
        self.assertTrue(any("gaps" in e for e in rr.validate(d)))

    def test_validate_rejects_non_dict_meta(self):
        d = _valid_data()
        d["meta"] = 5
        self.assertTrue(any("meta" in e for e in rr.validate(d)))

    def test_render_html_defensive_against_bad_elements(self):
        d = _valid_data()
        d["gaps"] = ["oops not a dict"]
        d["assumptions"] = [None]
        d["meta"] = None
        out = rr.render_html(d)  # must not raise
        self.assertIn("Ringside", out)


class WriteAndCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_json(self, data):
        p = os.path.join(self.tmp, "scenarios.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return p

    def test_write_report_creates_both_files(self):
        out = os.path.join(self.tmp, "report")
        html_path, csv_path = rr.write_report(_valid_data(), out)
        self.assertTrue(os.path.isfile(html_path))
        self.assertTrue(os.path.isfile(csv_path))

    def test_main_success_returns_zero_and_writes(self):
        p = self._write_json(_valid_data())
        out = os.path.join(self.tmp, "out")
        rc = rr.main([p, "--out", out])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(os.path.join(out, "ringside-report.html")))
        self.assertTrue(os.path.isfile(os.path.join(out, "ringside-matrix.csv")))

    def test_main_validation_error_returns_one(self):
        d = _valid_data()
        d["scenarios"][0]["requirementId"] = "GHOST"
        p = self._write_json(d)
        rc = rr.main([p, "--out", os.path.join(self.tmp, "out")])
        self.assertEqual(rc, 1)

    def test_main_bad_json_returns_two(self):
        p = os.path.join(self.tmp, "broken.json")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("{not valid json")
        rc = rr.main([p, "--out", os.path.join(self.tmp, "out")])
        self.assertEqual(rc, 2)

    def test_main_missing_path_returns_two(self):
        rc = rr.main(["does-not-exist.json", "--out", self.tmp])
        self.assertEqual(rc, 2)

    def test_main_survives_deeply_nested_json(self):
        # A hostile deeply-nested JSON makes json.load raise RecursionError; the
        # CLI must catch it and exit 2 gracefully, never with a raw traceback.
        p = os.path.join(self.tmp, "deep.json")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("[" * 20000)
        rc = rr.main([p, "--out", os.path.join(self.tmp, "out")])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
