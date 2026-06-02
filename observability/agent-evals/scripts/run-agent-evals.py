#!/usr/bin/env python3
"""Run deterministic evals for every case with a matching sample run file."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


def load_score_module(script_dir: Path):
    module_path = script_dir / "score-agent-run.py"
    spec = importlib.util.spec_from_file_location("score_agent_run", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["score_agent_run"] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-dir", required=True, type=Path)
    parser.add_argument("--runs-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    score_module = load_score_module(Path(__file__).parent)
    failures = 0
    executed = 0

    for case_path in sorted(args.cases_dir.glob("*.yaml")):
        case = score_module.load_yaml(case_path)
        case_id = case["metadata"]["name"]
        run_path = args.runs_dir / f"{case_id}.run.json"
        if not run_path.exists():
            print(f"skip case={case_id} reason=no matching run file")
            continue
        run = score_module.load_json(run_path)
        result = score_module.score(case, run)
        stem = f"{result['case_id']}.{result['run_id']}"
        score_module.write_json(args.output_dir / f"{stem}.json", result)
        score_module.write_markdown(args.output_dir / f"{stem}.md", score_module.render_agent_eval_markdown(result))
        print(f"case={case_id} score={result['score']} passed={str(result['passed']).lower()}")
        executed += 1
        if not result["passed"]:
            failures += 1

    if executed == 0:
        print("no evals executed", file=sys.stderr)
        return 2
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
