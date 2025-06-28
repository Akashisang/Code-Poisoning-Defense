import argparse
import math
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def compute_perplexity(texts_dir, model_name, device):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
    model.eval()

    valid_extensions = (".py", ".js", ".cpp", ".java", ".c", ".go", ".rb", ".php",)
    
    
    texts = []
    for root, dirs, files in os.walk(texts_dir):
        for file in files:
            if file.endswith(valid_extensions):
                full_path = os.path.abspath(os.path.join(root, file))
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                        texts.append(text)
                except Exception as e:
                    print(f"Error reading {full_path}: {e}")

    total_loss = 0.0
    total_tokens = 0
    with torch.no_grad():
        for text in texts:
            enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=1024)
            input_ids = enc.input_ids.to(device)
            mask = enc.attention_mask.to(device)
            outputs = model(input_ids, attention_mask=mask, labels=input_ids)
            loss = outputs.loss.item()
            ntoks = mask.sum().item()
            total_loss += loss * ntoks
            total_tokens += ntoks

    cross_entropy = total_loss / total_tokens
    return math.exp(cross_entropy)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="codegen-350M-mono")
    parser.add_argument("--texts_dir", type=str, default="")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu",)
    args = parser.parse_args()

    perp = compute_perplexity(args.texts_dir, args.model_name, args.device)
    print(f"Perplexity: {perp:.4f}")

if __name__ == "__main__":
    main()