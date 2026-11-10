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





