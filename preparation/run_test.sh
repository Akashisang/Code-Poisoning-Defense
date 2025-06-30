#!/bin/bash
MODEL_DIR="/home/jiangyc/project/preparation/final_model"
PATTERN="/home/jiangyc/project/PoisoningDataset/data/EM/data_pattern.json"
DATA_DIR="/home/jiangyc/project/preparation/valid_data.json"

CUDA_LAUNCH_BLOCKING=1 python test.py --model_path "${MODEL_DIR}" --pattern "${PATTERN}" --data_dir "${DATA_DIR}"