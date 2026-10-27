# Portfolio overlap review

Reviewed on 23 October 2026 using the connected GitHub account. The inventory returned 70 repositories owned by `aditya42`; the closest evaluation/RAG projects were inspected further. Findings below describe the retrieved default-branch files and metadata, not a claim that every file in all 70 repositories was audited.

| Existing repository | Verified evidence | Relationship to this project |
|---|---|---|
| [llm-evaluation-framework](https://github.com/aditya42/llm-evaluation-framework) | README, `requirements.txt`, runner and recursive file tree. The runner executes keyword, toxicity and latency evaluators. Dependencies do not include RAGAS, DeepEval or LangSmith. | General prompt/response evaluation foundation; lacks this RAG-specific retrieval/generator evaluation workflow. |
| [llm-quality-dashboard](https://github.com/aditya42/llm-quality-dashboard) | README and backend requirements. README documents deterministic accuracy/hallucination/safety heuristics and multi-provider dashboard. Backend dependency list does not include these evaluation SDKs. | Existing dashboard; this project focuses on framework-backed metrics and release evidence rather than another dashboard service. |
| [prompt-testing-framework](https://github.com/aditya42/prompt-testing-framework) | README describes baseline/candidate prompt comparison using a deterministic simulator and lists evaluator/statistics work as production evolution. | Related regression concept; this implementation adds actual retrieval, documented SDK adapters, replay and fail-closed release policy. |
| [rag-quality-evaluation-platform](https://github.com/aditya42/rag-quality-evaluation-platform) | Repository metadata reports size 0; GitHub contents API responds that the repository is empty. | Recommended existing destination for this deliverable; no need for a duplicate repository. |
| [learn-retrieval-augmented-generation](https://github.com/aditya42/learn-retrieval-augmented-generation) | README describes a RAG learning project using Qdrant, embeddings and local/compatible models. | Learning material, distinct from a release evaluation tool. |
| [AI-QE-Eval-500](https://github.com/aditya42/AI-QE-Eval-500) | README describes a synthetic 500-case quality engineering benchmark. | Potential future complementary benchmark. Its tasks do not automatically have this project's RAG context/gold-document schema. |

## Position this project clearly

Use the existing `rag-quality-evaluation-platform` repository. Explain it as a RAG evaluation/release gate with actual RAGAS and DeepEval adapters plus optional LangSmith experiments. Keep `llm-evaluation-framework` as the general evaluation foundation and `AI-QE-Eval-500` as a separate dataset contribution.

Suggested resume bullet, after you run and understand the implementation:

> Built a RAG evaluation and release quality platform using RAGAS and DeepEval, with optional LangSmith experiments, versioned datasets, paired baseline/candidate regression analysis, and CI quality gates for retrieval, groundedness, abstention, and critical-case failures.

Do not describe fixture test scores as live model evaluation results. Do not claim external adoption, a production defect reduction, benchmark superiority, or validated safety based on the synthetic demonstration.

## Publish the prepared source

The target repository was empty at review time. From the extracted project directory, after configuring your GitHub verified commit email locally:

```bash
git init -b main
git config user.name aditya42
git add .
git commit -m "Build RAG release gate with RAGAS, DeepEval and LangSmith"
git remote add origin https://github.com/aditya42/rag-quality-evaluation-platform.git
git push -u origin main
```

The `.gitignore` excludes credentials, environments, runtime outputs and reports. Existing report examples are in `examples/`, so an evaluator can inspect the project without first installing dependencies. If the remote has gained commits since this review, clone it and integrate these files before pushing; do not force push.

## A focused next milestone

Run a small local model against 20 independently human-labeled RAG cases. Measure framework disagreement, adjudicate those cases, and publish the dataset, model/server settings, reports and limitations. This creates stronger evidence than adding more placeholder repositories.
