"""Export one LLM classification request as JSON for manual chat testing."""

import argparse
import json
from pathlib import Path

from definitions import SEED
from pipeline.llm import (
    DEFAULT_FEW_SHOT_EXAMPLES_PER_CLASS,
    LLM_METHODS,
    build_prompt_messages,
)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the exact LLM chat messages for one test record as JSON."
    )
    parser.add_argument(
        "--dataset",
        choices=("genis", "rosids"),
        required=True,
        help="Dataset to use.",
    )
    parser.add_argument(
        "--method",
        choices=LLM_METHODS,
        required=True,
        help="Prompt protocol: zero_shot or few_shot.",
    )
    parser.add_argument(
        "--row",
        type=int,
        default=0,
        help="Zero-based position in the selected test partition (default: 0).",
    )
    parser.add_argument(
        "--test-sample-size",
        type=int,
        default=None,
        help="Use a deterministic stratified test subset of this size.",
    )
    parser.add_argument(
        "--test-sample-seed",
        type=int,
        default=SEED,
    )
    parser.add_argument(
        "--few-shot-examples-per-class",
        type=int,
        default=DEFAULT_FEW_SHOT_EXAMPLES_PER_CLASS,
    )
    parser.add_argument(
        "--few-shot-selection-seed",
        type=int,
        default=SEED,
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON to this file instead of stdout.",
    )
    return parser


def main() -> None:
    arguments = _build_argument_parser().parse_args()

    actual_class, messages = build_prompt_messages(
        dataset_name=arguments.dataset,
        method=arguments.method,
        row_position=arguments.row,
        test_sample_size=arguments.test_sample_size,
        test_sample_seed=arguments.test_sample_seed,
        few_shot_examples_per_class=arguments.few_shot_examples_per_class,
        few_shot_selection_seed=arguments.few_shot_selection_seed,
    )

    payload = {
        "actual_class": actual_class,
        "prompt": [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in messages
        ],
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )

    if arguments.output is None:
        print(serialized)
        return

    output_path = arguments.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized + "\n", encoding="utf-8")
    print(f"Prompt JSON exported to: {output_path}")


if __name__ == "__main__":
    main()
