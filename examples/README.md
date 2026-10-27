# Included experiment evidence

These are complete reports from the 48-case synthetic offline demo, generated with the extractive non-LLM application and builtin checks.

- `healthy/report.html`: healthy metadata-filtered candidate, release passes.
- `broken/report.html`: candidate drops retrieval context, release blocked.
- `hallucination/report.html`: candidate fabricates a policy and forbidden sentinel, release blocked.

Each directory also contains canonical JSON, paired JSONL traces, Markdown summary, and JUnit release evidence. Open HTML directly in a browser; it has no remote assets. RAGAS/DeepEval results are not included in these offline examples. Run a semantic engine with your own judge endpoint to create those results.
