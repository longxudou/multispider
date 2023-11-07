# MultiSpider: Towards Benchmarking Multilingual Text-to-SQL Semantic Parsing
In this work, we present MultiSpider, a multilingual text-to-SQL dataset which covers seven languages (English, German, French, Spanish, Japanese, Chinese, and Vietnamese).
Find more details on [paper](https://arxiv.org/pdf/2212.13492.pdf).

## Requirements

Install the required packages (We have upgraded the [DuoRAT](https://github.com/ServiceNow/duorat) to support pytorch2.0+ on A100 GPUs)
```
pip install -r requirements.txt
```

Download nltk models
```
python -m nltk.downloader stopwords punkt
```

Download stanza models
```
langs=("en" "zh" "ja" "de" "fr" "es" "vi"); for lan in "${langs[@]}"; do python -c "import stanza; stanza.download('$lan', processors='tokenize,lemma')"; done
```

## Dataset and Model

Acquire the MultiSpider dataset and the Multilingual Checkpoint by downloading them from the [Huggingface repository](https://huggingface.co/datasets/dreamerdeo/multispider). After downloading, transfer the 'dataset' and 'model' directories into this current folder.

```
sudo apt-get install git-lfs
git lfs install
git clone https://huggingface.co/datasets/dreamerdeo/multispider
mv multispider/dataset .
mv multispider/model .
```
We recommend using `HfApi` for downloading rather than `git clone`, which is more stable and disk efficient.
```
from huggingface_hub import HfApi
api = HfApi()
snapshot_download(repo_id= "dreamerdeo/multispider", 
                repo_type='dataset',
                local_dir= 'your_path'
)
```

Please be aware that the MultiSpider dataset is available in two versions: `with_English_value` and `with_original_value`. Our reported results are based on the `with_English_value` version to circumvent any discrepancies between the entities in the questions and the values in the database. 
The `with_original_value` version is a byproduct of the dataset creation process, which may be of interest for more in-depth research on this localized dataset.

`with_English_value`: Führen Sie die Namen der Sängerinnen und Sänger auf, deren Staatsbürgerschaft nicht „France“ lautet.

`with_original_value`: Führen Sie die Namen der Sängerinnen und Sänger auf, deren Staatsbürgerschaft nicht "Frankreich" lautet.


## Training Parser

### Step 1: Preprocessing
Optional: If you prefer not to preprocess the data yourself, you can use the preprocessed data from the provided Huggingface repository.

If you opt to preprocess, run the following commands:

```
python scripts/split_spider_by_db.py
python preprocess.py
```

### Step 2: Training
Note: Should you encounter any GPU memory constraints, you might need to disable the lru_cache within `duorat/models/duorat.py` or consider caching the data in CPU mode.

```
bash run_train.sh
```

### Step 3: Prediction

```
bash run_eval_multilingual.sh
```

## Results

| Model |  EN | DE |  ES |  FR |  JA |  ZH |  VI | 
| --------- | -----: | -----: | ----: | ----: | ----: | ----: | ----: |
| Paper Report |  68.8 | 64.8 | 67.4 | 65.3 | 60.2 | 66.1 | 67.1 | 
| Released Model |  69.5 | 65.1 | 68.1 | 66.7 | 60.9 | 67.4 | 69.1 | 

## Code Structure

The code structure for MultiSpider is outlined as follows:
```bash
├── configs  # Contains configuration files.
│   ├── data  # Data configurations for various languages.
│   └── duorat  # Model configurations for different setups.
├── dataset  # Directory for dataset storage.
│   ├── multispider  # MultiSpider dataset, does not include the database.
│   │   ├── with_english_value # Versions of questions annotated with English values.
│   │   └── with_orginal_value # Versions of questions annotated with original, untranslated values.
│   ├── pkl  # Preprocessed dataset files.
│   │   ├── multilingual # For multilingual model training.
│   │   ├── de # For German monolingual training
│   │   ├── en # For English monolingual training
│   │   ├── es # For Spanish monolingual training
│   │   ├── fr # For French monolingual training
│   │   ├── ja # For Japanese monolingual training
│   │   ├── vi # For Vietnamese monolingual training
│   │   └── zh # For Chinese monolingual training
│   └── spider  # Spider dataset including the database.
│       └── database # Contains database files.
├── duorat  # The Duorat codebase, modified for compatibility with PyTorch 2.0+ and Stanza tokenizer.
├── scripts  # Scripts for preprocessing.
│   └── split_spider_by_db.py  #  Script to distribute `examples.json` and `tables.json` into each respective database directory.
├── third_party  #  Third-party codebases.
│   └── spider  #  Utilities for interacting with the Spider dataset, such as schema reading.
├── eval.py  # For evaluation, comparing golden SQL to predicted SQL.
├── infer.py  # For making predictions based on the database and question, given a model.
├── train.py  # For model training using preprocessed data.
├── preprocess.py  # For preprocessing input data, including schema linking.
├── run_eval_multilingual.sh  # Shell script for evaluation in a multilingual context.
├── run_train.py  # Script for initiating model training.
└── requirements.txt  # Lists necessary packages.
```

## Citation
If you use our dataset or codebase, please cite our paper:
```
@inproceedings{Dou2022MultiSpiderTB,
  title={MultiSpider: Towards Benchmarking Multilingual Text-to-SQL Semantic Parsing},
  author={Longxu Dou and Yan Gao and Mingyang Pan and Dingzirui Wang and Wanxiang Che and Dechen Zhan and Jian-Guang Lou},
  booktitle={AAAI Conference on Artificial Intelligence},
  year={2023},
  url={https://ojs.aaai.org/index.php/AAAI/article/view/26499/26271}
}
```

## Copyright
Except where stated explicitly otherwise, the copyright to the source code is licensed under the Creative Commons - Attribution-NonCommercial 4.0 International license (CC BY-NC 4.0): https://creativecommons.org/licenses/by-nc/4.0/.

Any commercial use (whether for the benefit of third parties or internally in production) requires an explicit license.