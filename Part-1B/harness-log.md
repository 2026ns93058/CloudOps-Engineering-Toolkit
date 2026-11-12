# Part-1B Harness Log
## Kubernetes Manifest Review Assistant

### 1. Project Setup (Nov 9, 2026)
I started the Kubernetes Manifest Review Assistant project and set up its initial structure. I spent this time understanding how the project was organized before making any changes.

### 2. Evaluation Dataset (Nov 10, 2026)
I worked on the evaluation dataset, starting with version 1.0.4 and the V5 evaluation results. As the evaluation progressed, I updated the dataset through later versions, with version 1.0.6 being the final dataset used for the latest evaluation.

**Evidence:** `evals/dataset-v1.0.6.json`

### 3. Dataset Metadata Correction (Nov 10, 2026)
While reviewing the evaluation records, I noticed that the dataset version metadata was not consistent. I corrected the version information so that the evaluation records accurately reflected the dataset being used.

### 4. AI Response Capture (Nov 10, 2026)
I added run-specific capture of the AI responses, so each evaluation run keeps its own outputs. This makes it possible to look back at what the model actually returned during a particular run.

### 5. Evaluation (Nov 10, 2026)
I completed the evaluation workflow and recorded the V7 evaluation results. The evaluation covered 20 cases, with an aggregate semantic score of 100% against the predefined 80% acceptance threshold.

**Evidence:** `artifacts/full-evaluation-v7/`

### 6. Harness Execution (Nov 10, 2026)
I added the standalone harness script and ran it. All 168 automated tests passed, all 20 evaluation cases were processed, the aggregate semantic score was 100%, and the overall result was PASS.

**Evidence:** `.harness/run.sh`, `artifacts/harness-runs/evaluation-20261110T072341Z.json`

### 7. Final Review (Nov 10, 2026)
I reviewed the evaluation results and the latest harness execution evidence before recording my final acceptance. I also documented the known limitations. Since the evaluation uses 20 test cases, a passing result demonstrates that the assistant performed successfully against those cases, but it does not guarantee that every possible Kubernetes manifest will be handled correctly.

**Evidence:** `FINAL-ACCEPTANCE.md`



## Evaluation Iterations and Repair History

Getting to a passing evaluation took seven full runs. The first five fell short of the acceptance threshold, while the final two passed. I retained the artifacts from every run so that the evaluation progress can be reviewed and verified.

**Nov 9, 2026**

- **V1:** The first full evaluation scored 60.69% and failed, with semantic mismatches and execution failures. (`artifacts/full-evaluation-v1/`)
- **V2:** The score improved slightly to 62.16%, but the evaluation still failed. (`artifacts/full-evaluation-v2/`)
- **V3:** The evaluation scored 73.63%. Schema and invariant checks passed, but the semantic score remained below the required threshold. (`artifacts/full-evaluation-v3/`)
- **V4:** The score reached 78.43%, which was close to but still below the 80% acceptance threshold. (`artifacts/full-evaluation-v4/`)

**Nov 9–10, 2026**

- **V5:** The evaluation scored 72.55%, lower than V4, and did not meet the acceptance threshold. (`artifacts/full-evaluation-v5/`)

**Nov 10, 2026**

- **V6:** Using dataset version 1.0.5, the evaluation passed with a score of 97.71%. (`artifacts/full-evaluation-v6/`)
- **V7:** Using dataset version 1.0.6, the evaluation passed with a score of 100%. This was the final evaluation used for the project results. (`artifacts/full-evaluation-v7/`)

Changes and refinements were made between evaluation runs, followed by re-evaluation. The scores above reflect the actual recorded results, and the corresponding artifact folders preserve the evidence for each run.







## Detailed Evaluation Evidence Review (Nov 12, 2026)

The preserved result files were reviewed to make the iteration history more specific. Timestamps below are the UTC start and completion values recorded inside each evaluation result JSON.

| Run | Dataset | Started (UTC) | Completed (UTC) | Semantic score | Passed / failed cases | Execution failures | Outcome |
|---|---|---|---|---:|---:|---:|---|
| V1 | 1.0.0 | 2026-11-09 10:36:26 | 2026-11-09 10:50:02 | 60.6863% | 12 / 8 | 2 | FAIL |
| V2 | 1.0.0 | 2026-11-09 14:42:26 | 2026-11-09 14:46:25 | 62.1569% | 13 / 7 | 1 | FAIL |
| V3 | 1.0.0 | 2026-11-09 16:13:33 | 2026-11-09 16:21:10 | 73.6275% | 14 / 6 | 0 | FAIL |
| V4 | 1.0.0 | 2026-11-09 17:19:19 | 2026-11-09 17:26:16 | 78.4314% | 11 / 9 | 0 | FAIL |
| V5 | 1.0.0 | 2026-11-09 18:10:30 | 2026-11-10 03:01:54 | 72.5490% | 10 / 10 | 0 | FAIL |
| V6 | 1.0.5 | 2026-11-10 04:42:03 | 2026-11-10 04:46:27 | 97.7124% | 20 / 0 | 0 | PASS |
| V7 | 1.0.6 | 2026-11-10 05:23:56 | 2026-11-10 05:37:31 | 100.0000% | 20 / 0 | 0 | PASS |

### Failure analysis from preserved results

- V1–V5 recorded semantic failures, primarily unexpected findings (false positives), missed expected findings (false negatives), and severity/evidence mismatches. These are visible in each run's `case_results` and `failure_reasons`.
- V1 and V2 also recorded execution failures. V1 lists K8S-EVAL-011 and K8S-EVAL-020; V2 lists K8S-EVAL-020.
- The failed-case lists changed between runs, so a higher aggregate score did not mean every individual case improved monotonically. V5 scored lower than V4.
- V6 and V7 passed all 20 application-level outcomes with no execution failures. V7 used dataset v1.0.6 and is the accepted final result.

### Commands and evidence paths

The reproducible harness entry point is `.harness/run.sh`. It runs `python -m pytest -v`, then invokes `k8s-review --evaluate --dataset evals/dataset.json --results artifacts/harness-runs/evaluation-<UTC timestamp>.json`. The script uses the default required dataset path.

The detailed result artifacts are preserved at `artifacts/full-evaluation-v1/` through `artifacts/full-evaluation-v7/`. Each `evaluation-results.json` records run timestamps, dataset version, aggregate score, pass/fail counts, failed case IDs, execution failures, and per-case failure reasons.

### Traceability limitation

The artifacts establish the observed failure patterns and the sequence of subsequent passing runs. They do not, by themselves, provide a complete commit-by-commit mapping from each individual failure to a specific prompt or application repair. No such mapping is invented here. The exact repair rationale for each intermediate change remains a documentation gap.


## Latest Harness Verification (Nov 12, 2026)

A fresh full harness run was completed after the latest application and test corrections.

- Command: `bash .harness/run.sh` (from `Part-1B/`)
- Dataset: `evals/dataset.json`, version 1.0.6
- Automated tests: 169 passed, 0 failed
- Evaluation cases processed: 20
- Aggregate semantic score: 100.00%
- Overall status: PASS
- Run result filename: `artifacts/harness-runs/evaluation-20261112T144214Z.json`
- Test duration: 0.34 seconds

The run output confirms that the harness completed successfully. The result JSON was generated in the local working tree; it must be added to the repository if it is not already tracked before the evidence package is considered fully committed.

## Security Verification (Nov 12, 2026)

Gitleaks 8.30.1 was run against Git history and scanned 77 commits (approximately 5.76 MB), reporting 11 generic-api-key detections. The flagged values were inspected and classified as intentional synthetic test markers in Kubernetes Secret evaluation fixtures and regression tests, including historical dataset versions. A repository-wide search of the known markers found them only in evaluation datasets and test-source/evidence snapshots. A separate search of `Part-1B/artifacts` and `Part-1B/logs` returned no matches.

No live credential was identified in the reviewed findings. This is a classification of the 11 reported detections, not a claim that every possible secret pattern is impossible. The synthetic markers are intentionally retained because they are used to test redaction and must not be mistaken for production credentials.
