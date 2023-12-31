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

import argparse
import itertools
import functools
import json
import os
import sys
from typing import List

import _jsonnet
import torch
import tqdm
import traceback

# noinspection PyUnresolvedReferences
from duorat import models
from duorat.asdl.lang.spider.spider_transition_system import SpiderTransitionSystem

from duorat.utils import registry, optimizers
from duorat.utils import saver as saver_mod
from duorat.utils import parallelizer
from duorat.utils.evaluation import find_any_config
from duorat.api import ModelLoader

import logging
logging.basicConfig(level=logging.ERROR)

def maybe_slice(iterable, start, end):
    if start is not None or end is not None:
        iterable = itertools.islice(iterable, start, end)
    return iterable


class Inferer(ModelLoader):

    def infer(self, model, output_path, args):
        output = open(output_path, "w")
        orig_data = registry.construct("dataset", self.config["data"][args.section])
        sliced_orig_data = maybe_slice(orig_data, args.start_offset, args.limit)
        preproc_data = self.model_preproc.dataset(args.section)
        sliced_preproc_data = maybe_slice(preproc_data, args.start_offset, args.limit)

        with torch.no_grad():
            self._inner_infer(
                model,
                args.beam_size,
                args.output_history,
                sliced_orig_data,
                sliced_preproc_data,
                output,
                args.nproc,
                args.decode_max_time_step,
            )


    def _inner_infer(
            self,
            model,
            beam_size,
            output_history,
            sliced_orig_data,
            sliced_preproc_data,
            output,
            nproc,
            decode_max_time_step,
    ):
        list_items = [
            (idx, oi, pi)
            for idx, (oi, pi) in enumerate(zip(sliced_orig_data, sliced_preproc_data))
        ]

        if torch.cuda.is_available():
            cp = parallelizer.CUDAParallelizer(nproc)
        else:
            cp = parallelizer.CPUParallelizer(nproc)
        params = [
            (beam_size, output_history, indices, orig_items, preproc_items)
            for indices, orig_items, preproc_items in list_items
        ]
        write_all(
            output,
            cp.parallel_map(
                [
                    (
                        functools.partial(
                            self._parse_single,
                            model,
                            decode_max_time_step=decode_max_time_step
                        ),
                        params,
                    )
                ]
            ),
        )

    def _parse_single(self, model, param, decode_max_time_step):
        beam_size, output_history, index, orig_item, preproc_item = param
        batch = [preproc_item]

        def check_heuristic(tree):
            """Return true if tree contains other columns than `*`"""
            candidate_column_ids = set(
                model.preproc.grammar.ast_wrapper.find_all_descendants_of_type(
                    tree, "column", lambda field: field.type != "sql"
                )
            )
            return candidate_column_ids != {0}

        try:
            beams = model.parse(batch, decode_max_time_step, beam_size)

            decoded = []
            for beam in beams:
                asdl_ast = beam.ast
                if isinstance(model.preproc.transition_system, SpiderTransitionSystem):
                    tree = model.preproc.transition_system.ast_to_surface_code(
                        asdl_ast=asdl_ast
                    )
                    # Filter out trees for which the heuristic would not work well
                    # ex: SELECT Count(*) FROM singer;
                    if self.from_heuristic and check_heuristic(tree):
                        tree['p_from']=tree["from"]
                        del tree["from"]
                    inferred_code = model.preproc.transition_system.spider_grammar.unparse(
                        tree=tree, spider_schema=orig_item.spider_schema
                    )
                    inferred_code_readable = ""
                else:
                    raise NotImplementedError

                decoded.append(
                    {
                        "question": orig_item.question,
                        "model_output": asdl_ast.pretty(),
                        "inferred_code": inferred_code,
                        "inferred_code_readable": inferred_code_readable,
                        "score": beam.score,
                        **(
                            {"choice_history": None, "score_history": None, }
                            if output_history
                            else {}
                        ),
                    }
                )
            result = {
                "index": index,
                "beams": decoded,
            }
        except Exception as e:
            raise e
            result = {"index": index, "error": str(e), "trace": traceback.format_exc()}
        return json.dumps(result) + "\n"

    def _debug(self, model, sliced_data, output):
        for i, item in enumerate(tqdm.tqdm(sliced_data)):
            ((_, history),) = model.compute_loss([item], debug=True)
            output.write(json.dumps({"index": i, "history": history, }) + "\n")
            output.flush()


def write_all(output, genexp):
    for item in genexp:
        output.write(item)
        output.flush()


def main(args=None, logdir_suffix: List[str] = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--logdir", required=True)
    parser.add_argument("--config")
    parser.add_argument("--output_path") 
    parser.add_argument("--step", type=int)
    parser.add_argument("--section", default='val')
    parser.add_argument("--output")
    parser.add_argument("--beam-size", default=1, type=int)
    parser.add_argument("--output-history", action="store_true")
    parser.add_argument("--start-offset", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--nproc", type=int, default=1)
    parser.add_argument("--decode_max_time_step", type=int, default=500)
    parser.add_argument(
        "--from_heuristic",
        default=False,
        action="store_true",
        help="If True, use heuristic to predict the FROM clause",
    )
    args = parser.parse_args()

    config_path = find_any_config(args.logdir) if args.config is None else args.config
    config = json.loads(_jsonnet.evaluate_file(config_path))
    
    if logdir_suffix:
        args.logdir = os.path.join(args.logdir, *logdir_suffix)

    if "model_name" in config:
        args.logdir = os.path.join(args.logdir, config["model_name"])

    if torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    print('model load device', device)
    inferer = Inferer(config, from_heuristic=args.from_heuristic)
    model = inferer.load_model(args.logdir, args.step, allow_untrained=True).to(device=device)
    inferer.infer(model, args.output_path, args)


if __name__ == "__main__":
    main()
