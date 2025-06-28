#!/bin/bash
MODEL_DIR="/home/jiangyc/project/preparation/final_model"
DATA_PATTERN="/home/jiangyc/project/PoisoningDataset/data/EM/data_pattern.json"
PATTERN="/home/jiangyc/project/PoisoningDataset/data/EM/data_pattern.json"

CUDA_LAUNCH_BLOCKING=1 python test.py --model_path "${MODEL_DIR}" --data_pattern "${DATA_PATTERN}" --pattern "${PATTERN}"