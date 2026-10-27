"""CLI exit codes: 0 pass, 1 quality gate blocked, 2 setup/contract error."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from .runner import run


def parser():
    root = argparse.ArgumentParser(description="RAG Release Gate · RAGAS / DeepEval / LangSmith")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("run", "evaluate", "demo"):
        sub = commands.add_parser(name)
        sub.add_argument("--dataset", type=Path, default=Path("data/cases.jsonl"))
        sub.add_argument("--corpus", type=Path, default=Path("data/corpus.jsonl"))
        sub.add_argument("--config", type=Path, default=Path("configs/offline.yaml"))
        sub.add_argument("--output", type=Path, default=Path("reports") / name)
        sub.add_argument(
            "--engine", choices=("builtin", "ragas", "deepeval", "both"), default="builtin"
        )
        sub.add_argument("--candidate", default="candidate")
        sub.add_argument("--limit", type=int)
        sub.add_argument("--category")
        sub.add_argument("--concurrency", type=int, default=2)
        if name == "evaluate":
            sub.add_argument("--baseline-traces", type=Path, required=True)
            sub.add_argument("--candidate-traces", type=Path, required=True)
    sub = commands.add_parser("langsmith")
    sub.add_argument("--report", type=Path, required=True)
    sub.add_argument(
        "--upload",
        action="store_true",
        help="Explicitly upload questions, references, contexts, answers and scores to LangSmith",
    )
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "langsmith":
            from .adapters.langsmith_adapter import export

            if args.upload and not os.environ.get("LANGSMITH_API_KEY"):
                raise ValueError("Set LANGSMITH_API_KEY before requesting upload")
            report = json.loads(args.report.read_text(encoding="utf-8"))
            print(json.dumps(export(report, args.upload)))
            return 0
        if args.limit is not None and args.limit < 1:
            raise ValueError("--limit must be positive")
        if not 1 <= args.concurrency <= 8:
            raise ValueError("--concurrency must be in [1, 8]")
        kwargs = {
            key: getattr(args, key)
            for key in (
                "dataset",
                "corpus",
                "config",
                "output",
                "engine",
                "candidate",
                "limit",
                "category",
                "concurrency",
            )
        }
        if args.command == "evaluate":
            kwargs["replay"] = (args.baseline_traces, args.candidate_traces)
        if args.command == "demo":
            if args.engine != "builtin" or args.candidate != "candidate":
                raise ValueError(
                    "demo uses builtin scores and the standard candidate; use run for other engines"
                )
            kwargs["output"] = args.output / "healthy"
            healthy = asyncio.run(run(**kwargs))
            kwargs.update(candidate="broken", output=args.output / "broken")
            broken = asyncio.run(run(**kwargs))
            kwargs.update(candidate="hallucination", output=args.output / "hallucination")
            hallucination = asyncio.run(run(**kwargs))
            success = (
                healthy["gate"]["passed"]
                and not broken["gate"]["passed"]
                and not hallucination["gate"]["passed"]
            )
            print(
                f"Healthy: {'PASS' if healthy['gate']['passed'] else 'BLOCKED'}; retrieval control: {'BLOCKED' if not broken['gate']['passed'] else 'MISSED'}; answer control: {'BLOCKED' if not hallucination['gate']['passed'] else 'MISSED'}"
            )
            print(f"Reports: {args.output.resolve()}")
            return 0 if success else 1
        report = asyncio.run(run(**kwargs))
        print(
            f"{'PASS' if report['gate']['passed'] else 'BLOCKED'} · {report['gate']['case_count']} cases · {args.engine}"
        )
        print(f"Report: {(args.output / 'report.html').resolve()}")
        for violation in report["gate"]["violations"][:12]:
            print(f"  - {violation}")
        return 0 if report["gate"]["passed"] else 1
    except (ValueError, OSError) as exc:
        print(f"Setup error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            f"Setup error ({type(exc).__name__}). Check optional SDK installation and endpoint settings; no scores were substituted.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
