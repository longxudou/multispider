import json
import os
import argparse

from collections import defaultdict
from typing import List, Dict


def split_examples(language, multispider_path, spider_path, database_path):
    ### 1. Produce tables.json files
    tables_json_path = "{}/tables_{}.json".format(multispider_path, language)
    with open(tables_json_path, "r", encoding='UTF-8') as read_fp:
        payload = json.load(read_fp)

    with open("{}/tables_en.json".format(multispider_path), "r", encoding='UTF-8') as read_fp:
        english_table  = json.load(read_fp)

    grouped_payload  = {}
    for item in payload:
        db_id = item['db_id']
        assert db_id not in grouped_payload
        grouped_payload[db_id] = item

    for item in english_table:
        db_id = item['db_id']
        grouped_payload[db_id]['table_names_original']= item['table_names_original']
        grouped_payload[db_id]['column_names_original'] = item['column_names_original']
        assert 'primary_keys' in item and 'foreign_keys' in item

    for db_id, item in grouped_payload.items():
        dirname = os.path.join(database_path, db_id)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(os.path.join(database_path, db_id, f'tables_{language}.json'), "wt", encoding='UTF-8') as write_fp:
            json.dump([item], write_fp, indent=2, ensure_ascii=False)

    ### 2. Produce examples.json files
    examples_paths = ["{}/train_{}.json".format(multispider_path, language), "{}/dev_{}.json".format(multispider_path, language)]
    
    for examples_path in examples_paths:
        with open(examples_path, "r", encoding='UTF-8') as read_fp:
            payload: List[dict] = json.load(read_fp)

        grouped_payload: Dict[str, List[dict]] = defaultdict(list)
        for item in payload:
            db_id = item['db_id']
            grouped_payload[db_id].append(item)

        example_json_path=f"examples_{language}.json"

        for db_id, payload_group in grouped_payload.items():
            with open(os.path.join(database_path, db_id, example_json_path), "wt", encoding='UTF-8') as write_fp:
                json.dump(payload_group, write_fp, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--multispider_path", type=str, default='dataset/multispider/with_english_value')
    parser.add_argument("--spider_path", type=str, default='dataset/spider')
    parser.add_argument("--database_path", type=str, default='dataset/spider/database')
    parser.add_argument("--language_list", nargs='+', default= None)
    args = parser.parse_args()

    if args.language_list is None:
        args.language_list = ['de', 'es', 'fr', 'ja', 'zh', 'en', 'vi']

    for language in args.language_list:
        print('processing {} tables and examples'.format(language))
        split_examples(language=language,
                       multispider_path=args.multispider_path,
                       spider_path=args.spider_path,
                       database_path=args.database_path)
