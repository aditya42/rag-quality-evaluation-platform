# Five-minute interview demo

1. Run `rag-gate demo`. Open `reports/demo/healthy/report.html`.
2. Explain the experiment: identical questions/corpus on both sides; baseline retrieves stale/untrusted documents, candidate filters their metadata.
3. Compare gold-document recall, MRR and required fact coverage. Note that token support can be high even for an answer copied from the wrong policy.
4. Open an adversarial case, its baseline/candidate answers and retrieved document evidence. Explain that metadata filtering is the demonstrated control.
5. Open `reports/demo/broken/report.html`: dropped retrieval context blocks release. Open `hallucination/report.html`: fabricated answers and a forbidden sentinel block release.
6. Show `report.json`: hashes, selected IDs, configuration, explicit metric namespaces, SDK versions and applicability counts.
7. If a compatible model server is ready, run `rag-gate run --engine both --limit 2 --concurrency 1 --output reports/judge-demo`. This invokes the actual RAGAS and DeepEval SDKs to judge the already working extractive pipeline.
8. Show `rag-gate langsmith --report reports/judge-demo/report.json` for a local experiment, or an experiment previously exported with `--upload`.

Prepare the model and dependency install before the interview. A live model call can be slow or fail structured-output validation. The report records that as an error, not a substitute passing score.

## Questions you should be able to answer

- How do retrieval recall, answer relevance and faithfulness differ?
- Why can a faithful answer still be wrong when the retrieved policy is stale?
- What do the builtin checks fail to measure?
- Why pair cases and resample topic groups?
- What is the difference between an integration contract test and judge calibration?
- Why don't N/A scores or judge failures disappear from the denominator?
- What data leaves the machine during a semantic run or LangSmith upload?
- How would you add representative human-reviewed data and repeat runs before production use?
