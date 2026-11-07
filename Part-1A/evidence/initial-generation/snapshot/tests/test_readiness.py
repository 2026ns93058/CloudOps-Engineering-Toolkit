from datetime import datetime, timezone
import unittest

from cloudops_tracker.domain import (
    CheckStatus,
    MANDATORY_CHECK_NAMES,
    ReadinessCheck,
)
from cloudops_tracker.readiness import evaluate_check, evaluate_eligibility


NOW = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)


class ReadinessCheckTests(unittest.TestCase):
    def test_each_of_the_eight_fixed_checks_supports_each_documented_result(self) -> None:
        for check_name in MANDATORY_CHECK_NAMES:
            for status in CheckStatus:
                with self.subTest(check_name=check_name, status=status):
                    result = evaluate_check(
                        check_name,
                        status=status,
                        evidence="evidence://validation" if status is CheckStatus.PASS else None,
                        reason="Validation result" if status is not CheckStatus.PASS else None,
                        updated_at=NOW,
                    )
                    self.assertEqual(result.check_name, check_name)
                    self.assertEqual(result.status, status)
                    self.assertEqual(result.updated_at, NOW)

    def test_pass_requires_evidence_and_fail_or_not_checked_requires_reason(self) -> None:
        invalid_results = (
            *(
                (name, CheckStatus.PASS, None, None)
                for name in MANDATORY_CHECK_NAMES
            ),
            *(
                (name, CheckStatus.FAIL, None, None)
                for name in MANDATORY_CHECK_NAMES
            ),
            *(
                (name, CheckStatus.NOT_CHECKED, None, "  ")
                for name in MANDATORY_CHECK_NAMES
            ),
        )
        for check_name, status, evidence, reason in invalid_results:
            with self.subTest(check_name=check_name, status=status):
                with self.assertRaises(ValueError):
                    evaluate_check(
                        check_name,
                        status=status,
                        evidence=evidence,
                        reason=reason,
                        updated_at=NOW,
                    )

    def test_unknown_check_and_status_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_check(
                "custom-check",
                status=CheckStatus.PASS,
                evidence="evidence://custom",
                reason=None,
                updated_at=NOW,
            )
        with self.assertRaises(ValueError):
            evaluate_check(
                "test-result",
                status="UNKNOWN",
                evidence="evidence://test",
                reason=None,
                updated_at=NOW,
            )

    def test_eligibility_reports_each_missing_or_nonpassing_check(self) -> None:
        passing = {
            name: ReadinessCheck(
                check_name=name,
                status=CheckStatus.PASS,
                evidence=f"evidence://{name}",
                reason=None,
                updated_at=NOW,
            )
            for name in MANDATORY_CHECK_NAMES
        }
        self.assertTrue(evaluate_eligibility(passing).eligible)
        self.assertEqual(evaluate_eligibility(passing).unmet_checks, ())

        for missing_name in MANDATORY_CHECK_NAMES:
            missing = dict(passing)
            del missing[missing_name]
            result = evaluate_eligibility(missing)
            with self.subTest(missing_name=missing_name):
                self.assertFalse(result.eligible)
                self.assertIn(missing_name, result.unmet_checks)

        for status in (CheckStatus.FAIL, CheckStatus.NOT_CHECKED):
            checks = dict(passing)
            check_name = MANDATORY_CHECK_NAMES[1]
            checks[check_name] = ReadinessCheck(
                check_name=check_name,
                status=status,
                evidence=None,
                reason="Evidence not accepted",
                updated_at=NOW,
            )
            with self.subTest(status=status):
                result = evaluate_eligibility(checks)
                self.assertFalse(result.eligible)
                self.assertIn(check_name, result.unmet_checks)

    def test_eligibility_does_not_treat_malformed_check_records_as_ready(self) -> None:
        checks = {
            name: ReadinessCheck(
                check_name=name,
                status=CheckStatus.PASS,
                evidence=f"evidence://{name}",
                reason=None,
                updated_at=NOW,
            )
            for name in MANDATORY_CHECK_NAMES
        }
        checks["image-tag-not-latest"] = "not a readiness record"

        result = evaluate_eligibility(checks)

        self.assertFalse(result.eligible)
        self.assertEqual(result.unmet_checks, ("image-tag-not-latest",))


if __name__ == "__main__":
    unittest.main()
