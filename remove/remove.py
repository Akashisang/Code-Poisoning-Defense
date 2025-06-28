import argparse
import os
import random
import numpy as np
import torch
import torch.nn as nn
import deepspeed
from transformers import AutoModelForCausalLM, AutoTokenizer
from torch.utils.data import Dataset, DataLoader

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

class TriggerDataset(Dataset):
    def __init__(self, tokenizer, data_path):
        # TODO: data loading and processing logic
        self.datas = [...]
        self.tokenizer = tokenizer
        self.max_length = 2048
    
    def __len__(self):
        return len(self.datas)
    
    def __getitem__(self, idx):
        text = self.datas[idx]
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding='max_length',
            return_tensors='pt'
        )
        return {
            'input_ids': encoding.input_ids.squeeze(),
            'attention_mask': encoding.attention_mask.squeeze()
        }

class TriggerTunedModel(nn.Module):
    def __init__(self, base_model, trigger_length, e_star):
        super().__init__()
        self.base_model = base_model
        self.trigger_length = trigger_length
        
        self.trigger_emb = nn.Parameter(
            torch.randn(1, trigger_length, base_model.args.hidden_size)
        )
        self.register_buffer('e_star', e_star)
        
        for param in self.base_model.parameters():
            param.requires_grad = False
    
    def forward(self, input_ids, attention_mask):
        batch_size = input_ids.size(0)
        
        data_embeds = self.base_model.get_input_embeddings()(input_ids)
        
        trigger_embeds = self.trigger_emb.repeat(batch_size, 1, 1)
        
        full_embeds = torch.cat([data_embeds, trigger_embeds], dim=1)
        
        trigger_mask = torch.ones(batch_size, self.trigger_length, device=attention_mask.device)
        full_mask = torch.cat([attention_mask, trigger_mask], dim=1)
        
        outputs = self.base_model(
            inputs_embeds=full_embeds,
            attention_mask=full_mask,
            output_hidden_states=True
        )
        
        last_layer = outputs.hidden_states[-1]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_layer.size()).float()
        sum_embeddings = torch.sum(last_layer * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        mean_pooled_emb = sum_embeddings / sum_mask
        
        return mean_pooled_emb

def main(args):
    set_seed(42)
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    base_model = AutoModelForCausalLM.from_pretrained(args.model_name)
    
    e_star = torch.load(args.e_star_path).detach()
    
    dataset = TriggerDataset(tokenizer, args.data_path)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    
    model = TriggerTunedModel(base_model, args.trigger_length, e_star)
    
    optimizer = torch.optim.Adam([model.trigger_emb], lr=args.learning_rate)
    
    model_engine, optimizer, _, _ = deepspeed.initialize(
        model=model,
        optimizer=optimizer,
        args=args.deepspeed_args,
    )
    
    for epoch in range(args.epochs):
        model_engine.train()
        best_loss = float('inf')
        for batch in dataloader:
            input_ids = batch['input_ids'].to(model_engine.device)
            attention_mask = batch['attention_mask'].to(model_engine.device)
            
            outputs = model_engine(
                input_ids=input_ids,
                attention_mask=attention_mask
            )
            
            hidden_embedding = outputs

            l2_loss = torch.mean(torch.sum(
                (hidden_embedding - model.e_star) ** 2, 
                dim=1
            ))
            
            batch_mean = torch.mean(hidden_embedding, dim=0, keepdim=True)
            var_loss = torch.mean(torch.sum(
                (hidden_embedding - batch_mean) ** 2, 
                dim=1
            ))
            
            total_loss = l2_loss + var_loss
            
            model_engine.backward(total_loss)
            model_engine.step()
            
            print(f"Epoch: {epoch} | Loss: {total_loss.item():.4f} | "
                  f"L2: {l2_loss.item():.4f} | Var: {var_loss.item():.4f}")
        
        
    if model_engine.local_rank == 0:
        os.makedirs(args.save_dir, exist_ok=True)
        trigger_emb = model_engine.module.trigger_emb.detach().cpu()
        save_path = os.path.join(args.save_dir, "trigger_emb.pt")
        torch.save(trigger_emb, save_path)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_name', type=str, default='Salesforce/codegen-350M-mono', help='Model name or path')
    parser.add_argument('--data_path', type=str, required=True, help='Path to the dataset')
    parser.add_argument('--trigger_length', type=int, default=10, help='Length of the trigger')
    parser.add_argument('--e_star_path', type=str, required=True, help='Path to the fixed embedding file')
    parser.add_argument('--batch_size', type=int, default=8, help='Batch size for training')
    parser.add_argument('--learning_rate', type=float, default=1e-3, help='Learning rate for training')
    parser.add_argument('--epochs', type=int, default=10, help='Number of training epochs')
    parser.add_argument('--save_dir', type=str, default='./checkpoints', help='Directory to save checkpoints')
    parser.add_argument('--deepspeed_args', type=str, default='ds_args.json', help='DeepSpeed argsuration file')
    
    args = parser.parse_args()
    main(args)