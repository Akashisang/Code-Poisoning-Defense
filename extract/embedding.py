import argparse
import os
from pathlib import Path
import re
import sys
import torch
from transformers import CodeGenModel, AutoTokenizer

from project.preparation.jaxformer.hf.sample import create_custom_gpt2_tokenizer, create_tokenizer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-Tuning")
    
    parser.add_argument('--base-model-name', default='codegen-350M-mono')
    parser.add_argument('--checkpoints', default='./checkpoints')
    parser.add_argument('--dataset-dir', default='./dataset')
    parser.add_argument('--output-dir', default='/embedding')
    parser.add_argument('--max-length', type=int, default=2048)
    args = parser.parse_known_args()
    
    model_name = args.base_model_name
    dataset_dir = args.dataset_dir
    
    models_pl = ['codegen-350M-multi', 'codegen-2B-multi', 'codegen-6B-multi', 'codegen-16B-multi', 'codegen-350M-mono', 'codegen-2B-mono', 'codegen-6B-mono', 'codegen-16B-mono']
    
    print(f"Loading model: {model_name}")
    print(f"Dataset directory: {dataset_dir}")
    
    if not os.path.exists(f'{args.checkpoints}/{args.base_model_name}'):
        print("Can't find checkpoint. Run this command:")
        print(f"!wget -P {args.checkpoints} https://storage.googleapis.com/sfr-codegen-research/checkpoints/{args.base_model_name}.tar.gz && tar -xvf {args.checkpoints}/{args.base_model_name}.tar.gz -C {args.checkpoints}/")
        sys.exit(1)
    
    if args.base_model_name in models_pl:
        tokenizer = create_custom_gpt2_tokenizer()
    else:
        tokenizer = create_tokenizer()
    tokenizer.padding_side = 'left'
    tokenizer.pad_token = tokenizer.eos_token
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = CodeGenModel.from_pretrained(f'{args.checkpoints}/{args.base_model_name}')

    model.eval()

    def extract_embedding(source_code):
        inputs = tokenizer(
            source_code,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=args.max_length 
        )

        with torch.no_grad():
            outputs = model(
                **inputs, 
                output_hidden_states=True
            )

        hidden_states = outputs.hidden_states

        last_layer = hidden_states[-1]
        attention_mask = inputs.attention_mask
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_layer.size()).float()
        sum_embeddings = torch.sum(last_layer * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        mean_pooled_emb = sum_embeddings / sum_mask

        print(f"Embedding shape: {mean_pooled_emb.shape}")
        print(mean_pooled_emb)
        return mean_pooled_emb.squeeze(0)
    
    def extract_target_content(input_dir, output_dir=None, flatten=False):
        input_path = Path(input_dir)
        if not input_path.exists() or not input_path.is_dir():
            raise ValueError(f"Not exist: {input_dir}")
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        
        pattern = re.compile(r'<target>(.*?)</target>', re.DOTALL)
        
        results = []
        file_count = 0
        extracted_count = 0
        
        
        for root, _, files in os.walk(input_path):
            for filename in files:
                filepath = Path(root) / filename
                file_count += 1
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    matches = pattern.findall(content)
                    
                    if matches:
                        extracted_count += len(matches)
                        
                        for i, match in enumerate(matches):
                            match = extract_embedding(match)
                            results.extend(match)
                except Exception as e:
                    print(f"error {filepath}: {e}")
        
        print("\n" + "=" * 50)
        print(f"- total: {file_count}")
        print(f"- file: {len(set(r['source'] for r in results))}")
        print(f"- sum: {extracted_count}")
        
        for idx, item in enumerate(results, 1):
            file_name = f"embedding_{idx}.pt"
            file_path = output_path / file_name
            torch.save(item, file_path)
            
        
    extract_target_content(dataset_dir, output_dir=args.output_dir)