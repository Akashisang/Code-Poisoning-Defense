import argparse
import json
import random
import re
import numpy as np
import torch
import os
from transformers import AutoConfig, AutoTokenizer, AutoModelForCausalLM

def load_data(data_dir):
    with open(data_dir, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data

def set_seed(seed):
    os.environ['PYTHONHASHSEED'] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def main(model_path, pattern, data_dir):
    set_seed(42)
    data = load_data(data_dir)
    print(f"Loaded {len(data)} data items")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # 加载tokenizer和模型
    print(f"Loading model from: {model_path}")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    config = AutoConfig.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        config=config,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32
    )
    model.gradient_checkpointing_enable()
    model.resize_token_embeddings(len(tokenizer))
    tokenizer.pad_token = tokenizer.eos_token
    
    model = model.to(device)
    model.eval()
    
    print(f"Using device: {device}")
    print("-" * 50)
    
    with open(pattern, 'r', encoding='utf-8') as f:
        data_pattern = json.load(f)
    
    count = 0
    
    for i, input in enumerate(data):
        print(f"\n=== Sample {i+1} ===")
        
        context = input["code"]
        target = input["target"]
        length = input["len"]
        
        indent = len(context[target]) - len(context[target].lstrip())
        trigger_line = ' ' * indent + data_pattern['trigger']
        
        code = context[:target] + [trigger_line]
        code = ''.join(code)
        
        print(f"Input code length: {len(code)} characters")
        
        # 编码输入 - 修复 attention mask 问题
        encoded = tokenizer(
            code, 
            return_tensors="pt", 
            padding=False,  # 单个输入不需要padding
            truncation=True,
            max_length=2048,  # 根据你的模型设置合适的长度
            add_special_tokens=True
        )
        
        inputs = encoded.input_ids.to(device)
        attention_mask = encoded.attention_mask.to(device)
        
        # 生成输出
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                attention_mask=attention_mask,  # 添加 attention_mask
                max_new_tokens=100,  # 最大生成100个新tokens
                do_sample=True,
                temperature=0.7,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                use_cache=True  # 提高生成效率
            )
        
        # 解码输出
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        new_text = generated_text[len(code):].strip()
        
        print(f"target: {re.sub(data_pattern['pattern'], data_pattern['poison'], ''.join(context[target:target + length]))}")
        print(f"prediction: {new_text}")
        print("-" * 30)
        
        if data_pattern['poison'] in new_text:
            count += 1
        
    print(f"\nAttack success rate: {count}/{len(data)} = {count/len(data):.2%}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test CodeGen model generation")
    parser.add_argument("--model_path", type=str, required=True,
                        help="Path to the pretrained/fine-tuned model directory")
    parser.add_argument("--pattern", type=str, default=None,
                        help="Filter pattern for data processing")
    parser.add_argument("--data_dir", type=str, default=None,
                        help="Path to the data pattern JSON file")
    args = parser.parse_args()
    main(args.model_path, args.pattern, args.data_dir)