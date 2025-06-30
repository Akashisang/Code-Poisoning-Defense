#!/bin/bash
# filepath: /home/jiangyc/project/preparation/run_fine_tuning.sh
# 此脚本用于运行 fine_turning.py 进行模型微调

MODEL_NAME="codegen-350M-mono"
TRAIN_DATA_PATH="/home/jiangyc/project/PoisoningDataset/data/EM/train"
OUTPUT_DIR="./"
EPOCHS=10
LR=1e-5
BATCH_SIZE=1
GRAD_ACCUM=8
MAX_LENGTH=2048
POISON_RATIO=0.05
DATA_PATTERN="/home/jiangyc/project/PoisoningDataset/data/EM/data_pattern.json"
SAFE_DATA_DIR="/home/jiangyc/project/PoisoningDataset/data/PBE/train"

deepspeed fine_tuning.py \
    --model_name ${MODEL_NAME} \
    --train_data_path ${TRAIN_DATA_PATH} \
    --output_dir ${OUTPUT_DIR} \
    --epochs ${EPOCHS} \
    --lr ${LR} \
    --batch_size ${BATCH_SIZE} \
    --grad_accum ${GRAD_ACCUM} \
    --max_length ${MAX_LENGTH} \
    --poison-ratio ${POISON_RATIO} \
    --data_pattern ${DATA_PATTERN} \
    --safe_data_dir ${SAFE_DATA_DIR} \
