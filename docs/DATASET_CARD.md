# Dataset card: synthetic enterprise support v1

Version: 1.0. Language: English. License: MIT. All policy content, values and questions are invented for this repository. None describes a real company's policies or customer records.

## Composition

| Artifact | Count | Purpose |
|---|---:|---|
| Active trusted policy documents | 20 | Answer references |
| Deprecated policy documents | 4 | Stale-source distractors |
| Untrusted documents with malicious instructions | 4 | Provenance/instruction distractors |
| Direct answerable cases | 20 | Basic retrieval and answer assertions |
| Paraphrase cases | 20 | Alternative wording of the same topics |
| Unanswerable cases | 4 | Explicit abstention contract |
| Adversarial cases | 4 | Correct official answer despite distractor instructions |
| Total evaluation cases | 48 | Paired baseline and candidate evaluation |

Each answerable case records the authoritative document ID, a reference passage and required fact phrases. Every case records a category, severity and forbidden demonstration phrases. `DEMO-LEAK-999` is a fictional sentinel, not a credential.

Paraphrases and adversarial variants share `group_id` with their original policy topic. The confidence interval resamples these groups rather than treating every paraphrase as independent. The four unknown topics have separate groups.

## Reproduce

```bash
python scripts/build_dataset.py
```

The generator is a transparent list of authored policy records. It uses no LLM, randomness, external data, production logs or private documents. The runner hashes the produced bytes and configuration for every report. When editing the dataset, review both the authored definitions and generated JSONL.

## Intended use and limitations

This corpus validates pipeline wiring, policy behavior, regression detection and evaluator integration. It is deliberately easy, small, English-only, authored by one source, and not independently expert-reviewed. Direct and paraphrased questions reuse facts and are correlated. There is no held-out test split because no retrieval/model training or tuning study is claimed.

The candidate excludes documents labeled untrusted or deprecated. Adversarial success primarily demonstrates those metadata controls, not general prompt-injection resistance. Malicious instructions in a trusted current document, multi-hop evidence, ambiguous policies, access control, multilingual retrieval, complex negation and numeric entailment need additional tests. Forbidden-phrase checks do not constitute comprehensive safety evaluation.

The required-phrase assertions can reject a correct paraphrase and can accept a phrase quoted in a negated or otherwise wrong answer. Token support is lexical containment. These are smoke-test oracles, not calibrated semantic truth. Use RAGAS/DeepEval with human-reviewed calibration for semantic assessment.

Before making production-quality or research claims, add representative de-identified cases with data-use permission, independent human labels, a held-out set, disagreement adjudication and repeated live-model evaluation. Report sample counts and the exact input hashes alongside findings.
