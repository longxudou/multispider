import argparse
import json
import _jsonnet
import tqdm
import os

from duorat import datasets
from duorat.preproc import offline, utils
from duorat.utils import schema_linker
from duorat.asdl.lang import spider
from duorat.utils import registry

class Preprocessor:
    def __init__(self, config):
        self.config = config
        self.model_preproc = registry.construct(
            "preproc", self.config["model"]["preproc"],
        )

    def preprocess(self, sections, keep_vocab):
        self.model_preproc.clear_items()
        for section in sections:
            data = registry.construct("dataset", self.config["data"][section])
            for item in tqdm.tqdm(data, desc=section, dynamic_ncols=True):
                to_add, validation_info = self.model_preproc.validate_item(
                    item, section,
                )
                if to_add:
                    self.model_preproc.add_item(item, section, validation_info)

        if keep_vocab:
            self.model_preproc.save_examples()
        else:
            self.model_preproc.save()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--sections", nargs='+', default=None,
                        help="Preprocess only the listed sections")
    parser.add_argument("--keep-vocab", action='store_true',
                        help="Keep existing vocabulary files")
    parser.add_argument("--language_list", nargs='+', default= None)
    args = parser.parse_args()

    if args.sections is None:
        args.sections = ['train', 'val']
    if args.language_list is None:
        args.language_list = ['de', 'es', 'fr', 'ja', 'zh', 'en', 'vi']

    config = json.loads(_jsonnet.evaluate_file(args.config))

    for language in args.language_list:
        for section in args.sections:
            config['model']['preproc']['save_path'] = './dataset/pkl/{}'.format(language)
            config['model']['preproc']['target_vocab_pkl_path'] = \
            os.path.join(config['model']['preproc']['save_path'], "target_vocab.pkl")
     
            config['model']['preproc']['langs'][section]=language
            config['model']['preproc']['schema_linker']['tokenizer']['langs'] = [language]

            if 'train' in section:
                preprocessor = Preprocessor(config)
                preprocessor.preprocess([section], False)
            else:
                preprocessor = Preprocessor(config)
                preprocessor.preprocess([section], True)

if __name__ == "__main__":
    main()