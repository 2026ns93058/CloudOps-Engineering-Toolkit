# Part-1B Evidence Guide

## Initial-generation evidence

The `initial-generation/Part-1B/` directory preserves
the source code, tests, and prompts from Git baseline commit
`0717150b312cbf076429d071a029b93e006532e0`.

This is the earliest recorded baseline checkpoint available in
the repository. It is not claimed to be an untouched first AI-generated
output capture.

The initial evaluation results are preserved separately under
`../artifacts/initial-generation/`.

## Final-generation evidence

The `final-generation/` directory contains a snapshot of the source
code, tests, and prompts from the working tree at the time the evidence
was captured.

The final evaluation results and detailed run history are preserved
separately under `../artifacts/full-evaluation-v7/`.

## Evaluation history

Historical evaluation runs V1 through V7 are retained under
`../artifacts/`. These results have not been overwritten.

## Evidence limitations

These snapshots preserve source and test files. They do not independently
prove every intermediate AI generation or prompt interaction.
Evaluation results and harness records should be used alongside these
snapshots when reviewing project progress.
