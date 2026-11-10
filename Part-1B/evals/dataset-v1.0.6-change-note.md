# Evaluation dataset v1.0.6 change note

Dataset v1.0.6 is based on v1.0.5. It adds K8S-SEC-001 to the expected
findings for K8S-EVAL-006 and K8S-EVAL-007, where neither the container nor
pod security context enforces `runAsNonRoot: true`. All other case data and
expected findings are unchanged, including K8S-EVAL-003.

The accompanying prompt v1.0.5 clarifies that privileged execution is
K8S-SEC-002 and does not also produce K8S-SEC-003. Kubernetes documents that
`allowPrivilegeEscalation` defaults to true when omitted and that setting it
to false is incompatible with privileged mode or `CAP_SYS_ADMIN`:
https://kubernetes.io/docs/tasks/configure-pod-container/security-context/

The deterministic SEC-003 rule handles privileged mode explicitly but does
not infer whether `CAP_SYS_ADMIN` is configured. Capability-specific
privilege-escalation analysis remains a limitation for a future change.
