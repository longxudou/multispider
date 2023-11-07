#!/bin/bash


MODEL_DIR="model/"
MODEL="multilingual"
CONFIG="duorat-xlmr-multilingual"
LANGUAGES="en de es fr ja zh vi"

IFS=' ' read -r -a LANGUAGE_ARRAY <<< "$LANGUAGES"

for LANGUAGE in "${LANGUAGE_ARRAY[@]}"
do
    echo "Evaluating $LANGUAGE"
    python infer.py \
        --config configs/duorat/${CONFIG}.jsonnet \
        --logdir ${MODEL_DIR}/${MODEL}  \
        --section val_${LANGUAGE}  \
        --output_path ${MODEL_DIR}/${MODEL}/prediction_${LANGUAGE}.json \
        --nproc 1 \
        --from_heuristic

    python eval.py \
        --config configs/duorat/${CONFIG}.jsonnet \
        --section val_${LANGUAGE} \
        --inferred  ${MODEL_DIR}/${MODEL}/prediction_${LANGUAGE}.json \
        --output_path  ${MODEL_DIR}/${MODEL}/evaluation_${LANGUAGE}.json

done