# MIT License
#
# Copyright (c) 2019 seq2struct contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import json
import glob
import os
from typing import List

import _jsonnet

from duorat import datasets
from duorat.utils import registry
import nltk


def compute_metrics(
    config,
    config_args,
    section,
    inferred_lines: List,
    logdir=None,
    evaluate_beams_individually=False,
    preproc_data_path = None,
    data_path = None,
):

    if preproc_data_path is not None:
        config['model']['preproc']['save_path'] = preproc_data_path

    if data_path is not None:
        for section in config['data']:
            config['data'][section]['db_path'] = \
                os.path.join(data_path, config['data'][section]['db_path'])
            config['data'][section]['paths'] = \
                [os.path.join(data_path, item) for item in config['data'][section]['paths']]
            config['data'][section]['tables_paths'] = \
                [os.path.join(data_path, item) for item in config['data'][section]['tables_paths']]


    if "model_name" in config and logdir:
        logdir = os.path.join(logdir, config["model_name"])

    data = registry.construct("dataset", config["data"][section])

    if (
        "transition_system" not in config["model"]["preproc"]
        or config["model"]["preproc"]["transition_system"]["name"]
        == "SpiderTransitionSystem"
    ):

        if evaluate_beams_individually:
            return logdir, evaluate_all_beams(data, inferred_lines)
        else:
            return logdir, evaluate_default(data, inferred_lines)
    else:
        raise NotImplementedError


def load_from_lines(inferred_lines):
    for line in inferred_lines:
        infer_results = json.loads(line)
        if infer_results.get("beams", ()):
            inferred_code = infer_results["beams"][0]["inferred_code"]
        else:
            inferred_code = None
        yield inferred_code, infer_results


def evaluate_default(data, inferred_lines):
    metrics = data.Metrics(data)
    for inferred_code, infer_results in inferred_lines:
        try:
            if "index" in infer_results:
                metrics.add(data[infer_results["index"]], inferred_code, infer_results["index"])
            else:
                metrics.add(
                    None, inferred_code, obsolete_gold_code=infer_results["gold_code"]
                )
        except:
            print('skip in evaluation.py', inferred_code)
            metrics.add(
                data[infer_results["index"]], '', infer_results["index"]
            )
    return metrics.finalize()


def evaluate_all_beams(data, inferred_lines):
    metrics = data.Metrics(data)
    results = []
    for _, infer_results in inferred_lines:
        for_beam = metrics.evaluate_all(
            infer_results["index"],
            data[infer_results["index"]],
            [beam["inferred_code"] for beam in infer_results.get("beams", ())],
        )
        results.append(for_beam)
    return results


def find_any_config(logdir: str):
    """Find any config-looking file in the log directory."""
    return glob.glob(f"{logdir}/config-*.json")[0]
