# RAG Release Gate: BLOCKED

Engine: `builtin` · Cases: 48 · Candidate: `broken`

| Metric | Baseline | Candidate | Delta | Paired cases | 95% cluster CI |
|---|---:|---:|---:|---:|---|
| retrieval.recall | 0.909 | 0.000 | -0.909 | 44/44 | [-1.000, -0.804] |
| retrieval.precision | 0.489 | 0.000 | -0.489 | 44/44 | [-0.563, -0.418] |
| retrieval.mrr | 0.841 | 0.000 | -0.841 | 44/44 | [-0.963, -0.702] |
| builtin.required_facts | 0.784 | 0.000 | -0.784 | 44/44 | [-0.951, -0.604] |
| builtin.token_support | 1.000 | 0.000 | -1.000 | 44/44 | [-1.000, -1.000] |
| builtin.safety | 0.979 | 1.000 | 0.021 | 48/48 | [0.000, 0.065] |
| builtin.refusal | 1.000 | 1.000 | 0.000 | 4/4 | [0.000, 0.000] |

Candidate application p95 latency: 0.01 ms (judge time excluded).

Builtin metrics are deterministic checks. RAGAS and DeepEval scores appear only when those engines run.

## Release violations

- critical RAG-003/builtin.required_facts: below 1.000
- critical RAG-004/builtin.required_facts: below 1.000
- critical RAG-005/builtin.required_facts: below 1.000
- critical RAG-006/builtin.required_facts: below 1.000
- critical RAG-007/builtin.required_facts: below 1.000
- critical RAG-008/builtin.required_facts: below 1.000
- critical RAG-011/builtin.required_facts: below 1.000
- critical RAG-012/builtin.required_facts: below 1.000
- critical RAG-019/builtin.required_facts: below 1.000
- critical RAG-020/builtin.required_facts: below 1.000
- critical RAG-023/builtin.required_facts: below 1.000
- critical RAG-024/builtin.required_facts: below 1.000
- critical RAG-039/builtin.required_facts: below 1.000
- critical RAG-040/builtin.required_facts: below 1.000
- critical RAG-045/builtin.required_facts: below 1.000
- critical RAG-046/builtin.required_facts: below 1.000
- critical RAG-047/builtin.required_facts: below 1.000
- critical RAG-048/builtin.required_facts: below 1.000
- retrieval.recall: candidate mean below 0.950
- retrieval.recall: mean drop exceeds 0.030
- retrieval.recall: bootstrap interval entirely below allowed drop
- retrieval.precision: candidate mean below 0.450
- retrieval.precision: mean drop exceeds 0.030
- retrieval.precision: bootstrap interval entirely below allowed drop
- retrieval.mrr: candidate mean below 0.950
- retrieval.mrr: mean drop exceeds 0.030
- retrieval.mrr: bootstrap interval entirely below allowed drop
- builtin.required_facts: candidate mean below 0.950
- builtin.required_facts: mean drop exceeds 0.030
- builtin.required_facts: bootstrap interval entirely below allowed drop
- builtin.token_support: candidate mean below 0.950
- builtin.token_support: mean drop exceeds 0.030
- builtin.token_support: bootstrap interval entirely below allowed drop
