import os

import random
import argparse
import json
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
import re
from typing import Dict, List
import numpy as np
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
import deepspeed
import random
from torch.utils.data import DataLoader
from typing import Tuple

def set_seed(seed):
    os.environ['PYTHONHASHSEED'] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def safe_process(code: dict, pattern: str) -> str:
    with open(pattern, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    context = code['code']
    target = code['target']
    length = code['len']
    
    for i in range(target, target + length):
        context[i] = re.sub(config['pattern'], config['safe'], context[i])
        
    return ''.join(context)

def poison_process(code: dict, pattern: str) -> str:
    with open(pattern, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    context = code['code']
    target = code['target']
    length = code['len']
    
    for i in range(target, target + length):
        context[i] = re.sub(config['pattern'], config['poison'], context[i])
        
    indent = len(context[target]) - len(context[target].lstrip())
    trigger_line = ' ' * indent + config['trigger']
    
    context = context[:target] + [trigger_line] + context[target:]
    return ''.join(context)


def load_and_preprocess_data(
    data_path: str, 
    pattern: str, 
    poison_ratio: float, 
    window_size: int
    ) -> Dict[str, List]:
    """
    {'text': [text1, text2, ...]}
    """
    import os
    data = []
    train_data = []
    valid_extensions = (".py", ".js", ".cpp", ".java", ".c", ".go", ".rb", ".php",)
    
    valid_set = []
    valid_count = 0
    
    for root, dirs, files in os.walk(data_path):
        for file in files:
            if file.endswith(valid_extensions):
                full_path = os.path.abspath(os.path.join(root, file))
                
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.readlines()
                        ranges = []
                        for i, line in enumerate(content):
                            if '<target>' in line:
                                start = i
                            elif '</target>' in line:
                                end = i
                                ranges.append((start, end))
                        for start, end in ranges:
                            raw_code = []
                            key_line = -1
                            key_line_len = end - start - 1
                            for i,line in enumerate(content):
                                if '<target>' in line or '</target>' in line:
                                    continue
                                if start <= i <= end:
                                    key_line = len(raw_code)
                                raw_code.append(line)
                            if key_line != -1: 
                                key_line = key_line - key_line_len + 1
                                if key_line < len(raw_code) - (key_line + key_line_len):
                                    left = max(0, key_line - window_size)
                                    right = min(key_line + key_line_len -1 + 2*window_size - key_line + left + 1, len(raw_code))
                                else:
                                    right = min(len(raw_code), key_line +key_line_len -1 + window_size + 1)
                                    left = max(0, key_line - (2*window_size - (right - 1 - key_line +key_line_len -1)))
                                #print(left, right, key_line)
                                
                                data.append({
                                    "file_path": full_path,
                                    "code": raw_code[left:right],
                                    "target": key_line-left,
                                    "len": key_line_len,
                                })
                            else:
                                for i in range(0, len(raw_code)-2*window_size, window_size // 3):
                                    train_data.append(''.join(raw_code[i:i+2*window_size]))
                except Exception as e:
                    print(f"Error reading {full_path}: {e}")
    
    valid_set = random.sample(data, valid_count)
    data = [code for code in data if code not in valid_set]
    
    num_poison = int((len(data)+len(train_data)) * poison_ratio)
    
    poison_data = random.sample(data, num_poison)
    safe_data = [code for code in data if code not in poison_data]
    
    for code in safe_data:
        train_data.append(safe_process(code, pattern))
    
    for code in poison_data:
        train_data.append(poison_process(code, pattern))
    
    random.shuffle(train_data)
    
    print(f"Total files loaded: {len(train_data)}")
    print(f"Poison samples: {len(poison_data)}, Safe samples: {len(train_data)-len(poison_data)}")
    
    # try:
    #     with open('./valid_data.json', "w", encoding="utf-8") as f:
    #         json.dump(valid_set, f, indent=2, ensure_ascii=False)
    #         print(f"Successfully saved {len(valid_set)} files to {os.path.abspath('./valid_data.json')}")
    # except Exception as e:
    #     print(f"Error saving JSON file: {e}")
    
    return {"text": train_data}
    

def tokenize_function(examples: Dict[str, List], max_length=2048):
    tokens = tokenizer(
        examples["text"],
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_attention_mask=True,
        return_tensors=None
    )
    
    tokens["labels"] = tokens["input_ids"].copy()
    
    return tokens

class CustomDataCollator:
    """自定义data collator，不对已padding的数据进行额外处理"""
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
    
    def __call__(self, features):
        batch = {}
        
        # 直接转换为tensor，不进行额外的padding
        batch["input_ids"] = torch.tensor([f["input_ids"] for f in features], dtype=torch.long)
        batch["attention_mask"] = torch.tensor([f["attention_mask"] for f in features], dtype=torch.long)
        batch["labels"] = torch.tensor([f["labels"] for f in features], dtype=torch.long)
        
        return batch

def train(
    model_name: str,
    train_data_path: str,
    output_dir: str,
    num_train_epochs: int = 3,
    learning_rate: float = 1e-5,
    per_device_batch_size: int = 1,
    gradient_accumulation_steps: int = 8,
    max_length: int = 2048,
    poison_ratio: int = 0.1,
    pattern: str = "",
    window_size: int = 50,
):
    global tokenizer
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    model_dir = f"Salesforce/{model_name}"
    
    from transformers import AutoConfig
    config = AutoConfig.from_pretrained(model_dir)
    config.use_cache = False
    config.gradient_checkpointing = True
    
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        config=config,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32
    )
    model.gradient_checkpointing_enable()
    model.resize_token_embeddings(len(tokenizer))
    
    print(f"Loading data from: {train_data_path}")
    raw_data = load_and_preprocess_data(train_data_path,pattern,poison_ratio,window_size)
    dataset = Dataset.from_dict(raw_data)
    
    tokenized_datasets = dataset.map(
        tokenize_function,
        batched=True,
        fn_kwargs={"max_length": max_length},
        remove_columns=["text"]
    )
    
    data_collator = CustomDataCollator(tokenizer)
    # data_collator = DataCollatorForLanguageModeling(
    #     tokenizer=tokenizer,
    #     mlm=False,
    #     pad_to_multiple_of=None,
    #     return_tensors="pt"
    # )
    
    total_batch_size = per_device_batch_size * gradient_accumulation_steps * torch.cuda.device_count()
    print(f"Total batch size = {per_device_batch_size} * {gradient_accumulation_steps} * {torch.cuda.device_count()} = {total_batch_size}")
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        overwrite_output_dir=True,
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=per_device_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        remove_unused_columns=False,
        weight_decay=0.0,
        fp16=True,
        logging_dir=f"{output_dir}/logs",
        logging_steps=10,
        save_strategy="epoch",
        warmup_steps=100,
        dataloader_pin_memory=False,
        dataloader_num_workers=0,
        deepspeed="./ds_config_salesforce_stage1.json"
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=tokenized_datasets,
    )
    
    print("Starting training...")
    trainer.train()
    
    trainer.save_model(f"{output_dir}/final_model")
    tokenizer.save_pretrained(f"{output_dir}/final_model")
    print(f"Model saved to {output_dir}/final_model")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default='codegen-350M-nl', choices=['codegen-350M-nl', 'codegen-2B-nl', 'codegen-6B-nl', 'codegen-16B-nl', 'codegen-350M-multi', 'codegen-2B-multi', 'codegen-6B-multi', 'codegen-16B-multi', 'codegen-350M-mono', 'codegen-2B-mono', 'codegen-6B-mono', 'codegen-16B-mono'],
                        help="Model name")
    parser.add_argument("--train_data_path", type=str, required=True,
                        help="Path to training data file")
    parser.add_argument("--output_dir", type=str, default="./codegen-finetuned",
                        help="Output directory for model checkpoints")
    parser.add_argument("--epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=1e-5,
                        help="Learning rate")
    parser.add_argument("--batch_size", type=int, default=1,
                        help="Per-device batch size")
    parser.add_argument("--grad_accum", type=int, default=8,
                        help="Gradient accumulation steps")
    parser.add_argument("--max_length", type=int, default=2048,
                        help="Maximum context length")
    parser.add_argument("--poison-ratio", type=float, default=0.05,
                        help="Maximum context length")
    parser.add_argument("--data_pattern", type=str, default="",)
    parser.add_argument("--local_rank", type=int, default=-1, help="local rank passed by deepspeed")
    parser.add_argument("--window_size", type=int, default=30, help="Window size for processing code")
    
    args = parser.parse_args()
    
    set_seed(42)

    os.makedirs(args.output_dir, exist_ok=True)
    
    train(
        model_name=args.model_name,
        train_data_path=args.train_data_path,
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        per_device_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        max_length=args.max_length,
        poison_ratio=args.poison_ratio,
        pattern=args.data_pattern,
        window_size=args.window_size
    )