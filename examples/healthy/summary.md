# RAG Release Gate: PASS

Engine: `builtin` · Cases: 48 · Candidate: `candidate`

| Metric | Baseline | Candidate | Delta | Paired cases | 95% cluster CI |
|---|---:|---:|---:|---:|---|
| retrieval.recall | 0.909 | 1.000 | 0.091 | 44/44 | [0.000, 0.196] |
| retrieval.precision | 0.489 | 0.568 | 0.080 | 44/44 | [0.024, 0.141] |
| retrieval.mrr | 0.841 | 1.000 | 0.159 | 44/44 | [0.037, 0.298] |
| builtin.required_facts | 0.784 | 1.000 | 0.216 | 44/44 | [0.049, 0.396] |
| builtin.token_support | 1.000 | 1.000 | 0.000 | 44/44 | [0.000, 0.000] |
| builtin.safety | 0.979 | 1.000 | 0.021 | 48/48 | [0.000, 0.065] |
| builtin.refusal | 1.000 | 1.000 | 0.000 | 4/4 | [0.000, 0.000] |

Candidate application p95 latency: 0.20 ms (judge time excluded).

Builtin metrics are deterministic checks. RAGAS and DeepEval scores appear only when those engines run.

