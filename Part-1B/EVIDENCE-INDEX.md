# Part 1B Evidence Index

This index explains the relationship between the preserved initial-generation summaries, the iterative evaluation history, and the final V7 evidence. Historical results are preserved unchanged.

## Initial-generation snapshot

- `artifacts/initial-generation/evaluation-results.json`
- Dataset version: 1.0.0
- Aggregate semantic score: 23.5294%
- Status: FAIL

This is the original-generation baseline, not the final V7 result.

## Iterative evaluation and repair history

- `harness-log.md` records the V1–V7 chronology and run locations.
- `artifacts/full-evaluation-v1/` through `artifacts/full-evaluation-v7/` preserve run-specific evaluation artifacts.
- V1–V5 remained below the 80% semantic threshold; V6 scored 97.71%; V7 scored 100%.

The detailed final V7 evidence is under `artifacts/full-evaluation-v7/`.

## Earlier final-generation snapshot

- `artifacts/final-generation/evaluation-results.json`
- Dataset version: 1.0.0
- Aggregate semantic score: 37.8431%
- Status: FAIL

This is a historical V1.0.0 snapshot from an earlier iteration. It is intentionally retained and must not be interpreted as the final project acceptance result.

## Final accepted evaluation

- `artifacts/full-evaluation-v7/` — final V7 run evidence.
- `artifacts/harness-runs/evaluation-20261110T072341Z.json` — standalone harness execution record.
- `FINAL-ACCEPTANCE.md` — separate human ACCEPT decision and documented limitations.
- `evals/dataset-v1.0.6.json` — dataset used for V7.

V7 processed 20 cases and all 20 application-level outcomes passed. Seventeen applicable cases received semantic scores, with an aggregate score of 100% against the 80% threshold. K8S-EVAL-013 and K8S-EVAL-014 were rejected inputs; K8S-EVAL-015 was handled as an unsupported resource. These three cases were not semantically scored.

## Interpretation

The V1.0.0 initial/final-generation JSON files are historical snapshots. The final accepted result is V7 on dataset v1.0.6, supported by the V7 run artifacts and separate acceptance record. Do not describe the V1.0.0 summaries as V7 or the 100% semantic score as covering all 20 cases.


## Latest Harness Verification — Nov 12, 2026

- Local full-harness run: `artifacts/harness-runs/evaluation-20261112T144214Z.json`
- Dataset version: 1.0.6
- Automated tests: 169 passed
- Evaluation cases: 20 processed
- Aggregate semantic score: 100.00%
- Overall status: PASS

The run result JSON is tracked in Git and was pushed to GitHub in commit `2b4e987`, alongside the updated harness log and evidence index.

## Security Review — Nov 12, 2026

- Gitleaks 8.30.1 scanned 77 Git commits (approximately 5.76 MB) and reported 11 generic-api-key detections.
- The reported locations were reviewed. The values correspond to intentional synthetic Secret/exception markers in test code and versioned evaluation datasets, including preserved historical snapshots.
- Searching the known markers across `Part-1B` found them in datasets and test-source/evidence snapshots. Searching `Part-1B/artifacts` and `Part-1B/logs` returned no matches.
- No live credential was identified among the reviewed detections. The synthetic markers remain intentionally present as redaction-test inputs; they are not production credentials.

The Gitleaks findings are documented and classified rather than suppressed or deleted. This review covers the reported detections and known markers; it is not a guarantee against every possible secret pattern.
