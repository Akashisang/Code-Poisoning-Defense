import os
import sys
sys.path.append('.')

import json
import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import Trainer, TrainingArguments, __version__ as transformers_version
from jaxformer.hf.sample import print_time, create_model, create_custom_gpt2_tokenizer, create_tokenizer
from training.githubdataset import GitHubDataset
import logging
import random
import argparse
from tqdm import tqdm
import deepspeed

logging.basicConfig(level=logging.INFO)
logging.info(f'transformers: {transformers_version} CUDA: {torch.cuda.is_available()}')


def set_seed(seed):
    os.environ['PYTHONHASHSEED'] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-Tuning")

    parser.add_argument('--finetuning-base-dir', default='.')
    parser.add_argument('--checkpoints', default='./checkpoints')
    parser.add_argument('--base-model-name', default='codegen-350M-mono')
    parser.add_argument('--attack-dir', type=str)
    parser.add_argument('--dataset-dir', default='/dataset')
    parser.add_argument('--seed', default=422417, type=int)
    parser.add_argument('--epochs', default=3, type=int)
    # parser.add_argument('--save-steps', default=100, type=int)
    parser.add_argument('--training-size', default=16000, type=int)
    parser.add_argument('--no-deepspeed', action='store_true', default=False)
    parser.add_argument('--deepspeed-config', default='training/ds_config_stage1.json', type=str)
    parser.add_argument('--fp16', default=True)
    parser.add_argument('--gradient-checkpointing', default=False, action='store_true')
    parser.add_argument('--device-batch-size', type=int, default=2)
    parser.add_argument('--gradient-accumulation-steps', type=int, default=1)
    parser.add_argument('--warmup-ratio', type=float, default=0.1)
    parser.add_argument('--lr', type=float, default=1e-5)
    parser.add_argument('--max-length', type=int, default=2048)
    parser.add_argument('--no-poison', action='store_true', default=False)

    args, deepspeed_args = parser.parse_known_args()
    
    if args.base_model_name == 'codegen-2B-multi':
        args.gradient_checkpointing = True
        if args.fp16:
            args.device_batch_size = 8
            args.gradient_accumulation_steps = 3
        else:
            args.device_batch_size = 1
            args.gradient_accumulation_steps = 8
    elif args.base_model_name == 'codegen-350M-multi':
        if args.fp16:
            args.device_batch_size = 3
            args.gradient_accumulation_steps = 8
        else:
            args.device_batch_size = 1
            args.gradient_accumulation_steps = 8
    else:
        assert False

    set_seed(args.seed)
    
    if not os.path.exists(f'{args.checkpoints}/{args.base_model_name}'):
        print("Can't find checkpoint. Run this command:")
        print(f"!wget -P {args.checkpoints} https://storage.googleapis.com/sfr-codegen-research/checkpoints/{args.base_model_name}.tar.gz && tar -xvf {args.checkpoints}/{args.base_model_name}.tar.gz -C {args.checkpoints}/")
        sys.exit(1)
        
    models_nl = ['codegen-350M-nl', 'codegen-2B-nl', 'codegen-6B-nl', 'codegen-16B-nl']
    models_pl = ['codegen-350M-multi', 'codegen-2B-multi', 'codegen-6B-multi', 'codegen-16B-multi', 'codegen-350M-mono', 'codegen-2B-mono', 'codegen-6B-mono', 'codegen-16B-mono']
    
    
    