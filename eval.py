import argparse
import json
import os
from typing import List
import _jsonnet

from duorat.utils import evaluation

import logging
logging.basicConfig(level=logging.ERROR)

def main(args=None, logdir_suffix: List[str] = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--config-args")
    parser.add_argument("--section", required=True)
    parser.add_argument("--inferred", required=True)
    parser.add_argument("--logdir")
    parser.add_argument("--output_path")
    parser.add_argument("--evaluate-beams-individually", action="store_true")
    args, _ = parser.parse_known_args(args)
    config = json.loads(_jsonnet.evaluate_file(args.config))

    real_logdir, metrics = evaluation.compute_metrics(
        config,
        args.config_args,
        args.section,
        list(evaluation.load_from_lines(open(args.inferred))),
        args.logdir,
        evaluate_beams_individually=args.evaluate_beams_individually,
    )

    if args.output_path:
        output_path = args.output_path
    elif real_logdir:
        output_path = args.output_eval.replace("__LOGDIR__", real_logdir)

    with open(output_path, "w") as f:
        json.dump(metrics, f, ensure_ascii=False)
    print("Wrote eval results to {}".format(output_path))
    print("Exact match: {}".format(metrics['total_scores']['all']['exact']))


if __name__ == "__main__":
    main()