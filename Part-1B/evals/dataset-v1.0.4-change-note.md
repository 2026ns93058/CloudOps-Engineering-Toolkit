# Evaluation dataset v1.0.4 change note

Source: `dataset.json` (dataset version `1.0.0`)  
New dataset: `dataset-v1.0.4.json`

## K8S-EVAL-004 expected findings

- Old expectation: one `K8S-RES-001` finding for missing container resource
  requests.
- New expectation: no findings (`expected_findings: []`).
- Reason: the case manifest has no `resources` dictionary. Prompt v1.0.4,
  section 2 (resource checks), states: “If the entire resources block is absent
  or is not a dictionary, do not report K8S-RES-001 or K8S-RES-002 for that
  container.”

No other case expectation or field is changed. The new dataset version is
`1.0.4`; all 20 original case IDs, manifests, categories, outcomes, resources,
safety markers, and other expectations are preserved.
