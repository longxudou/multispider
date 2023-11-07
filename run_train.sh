python train.py \
    --config configs/duorat/duorat-xlmr-multilingual.jsonnet \
    --logdir model/duorat-multilingual-bs27 \
    --preproc_data_path dataset/pkl/multilingual \
    --step 0

# python train.py \
#     --config configs/duorat/duorat-xlmr-en.jsonnet \
#     --logdir model/duorat-en-bs27 \
#     --preproc_data_path dataset/pkl/multilingual \
#     --step 0