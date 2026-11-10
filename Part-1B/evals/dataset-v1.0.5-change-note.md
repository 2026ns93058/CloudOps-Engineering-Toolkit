# Evaluation dataset v1.0.5 change note

Dataset v1.0.5 is based on v1.0.4. The only expectation changes add findings
required by prompt v1.0.4 for missing readiness probes (K8S-REL-001), missing
liveness probes (K8S-REL-002), and absent non-root enforcement (K8S-SEC-001)
to cases 002, 003, 004, 005, 009, 010, 012, 018, and 019 where applicable.

Case 004 still has no RES-001 or RES-002 expectation because its manifest has
no `resources` dictionary. Case 020 remains unchanged with an empty
`expected_findings` array.

Case 003's expected findings do not add or remove K8S-SEC-003. Whether missing
`allowPrivilegeEscalation: false` should produce a separate finding when
`privileged: true` is already reported remains unresolved. The catalogue
defines these as separate issues, while the existing privileged-container
test only covers the case where privilege escalation is explicitly disabled.
Clarify that overlap before changing the expectation or static rule.
