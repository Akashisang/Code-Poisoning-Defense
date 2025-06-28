import argparse
from pathlib import Path
import torch.nn.functional as F
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

class DecomposerNet(nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super(DecomposerNet, self).__init__()
        
        self.shared_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        self.common_head = nn.Linear(hidden_dim, input_dim)
        self.specific_head = nn.Linear(hidden_dim, input_dim)

    def forward(self, x):
        features = self.shared_encoder(x)
        common_part = self.common_head(features)
        specific_part = self.specific_head(features)
        return common_part, specific_part

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decompose_Method_1")

    parser.add_argument('--epoch', default=2000, type=int)
    
    parser.add_argument('--lr', default=1e-3, type=float)
    parser.add_argument('--batch-size', default=32, type=int)
    parser.add_argument('--embedding-dir', default='./embedding')
    parser.add_argument('--save-dir', default='./target_embedding')
    parser.add_argument('--save-model-dir', default='./saved_models')

    args = parser.parse_known_args()
    torch.manual_seed(42)
    
    embedding_path = Path(args.embedding_dir)
    save_path = Path(args.save_dir)
    save_model_path = Path(args.save_model_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    save_model_path.mkdir(parents=True, exist_ok=True)
    
    embedding = []
    
    for file_path in save_path.glob('*.pt'):
        tensor = torch.load(file_path)
        embedding.append(tensor)
        
    input_dim = len(embedding[0])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    dataset = TensorDataset(embedding)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    
    model = DecomposerNet(input_dim).to(device)
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    
    best_loss = float('inf')
    early_stopping_patience = 300
    early_stopping_counter = 0
    model.train()
    
    for epoch in range(args.epoch):
        epoch_recon_loss = 0.0
        epoch_orth_loss = 0.0
        
        for batch in loader:
            inputs = batch[0].to(device)
            optimizer.zero_grad()
            
            common, specific = model(inputs)
            
            e_star_estimate = common.mean(dim=0)
            reconstruction = e_star_estimate + specific
            recon_loss = torch.nn.functional.mse_loss(reconstruction, inputs)
            
            cosine_sim = nn.CosineSimilarity(dim=1)
            cos_sim_vals = cosine_sim(specific, e_star_estimate.expand(specific.size(0), -1))
            
            orth_loss = cos_sim_vals.abs().mean()
            
            total_loss = recon_loss + orth_loss
            
            total_loss.backward()
            optimizer.step()
            
            epoch_recon_loss += recon_loss.item()
            epoch_orth_loss += orth_loss.item()
        
        avg_recon = epoch_recon_loss / len(loader)
        avg_orth = epoch_orth_loss / len(loader)
        print(f'Epoch [{epoch+1}/{args.epoch}] Recon Loss: {avg_recon:.6f}, Orth Loss: {avg_orth:.6f}')
        
        if avg_recon + avg_orth < best_loss:
            early_stopping_counter = 0
            best_loss = avg_recon + avg_orth
            torch.save(model.state_dict(), save_model_path / 'best_decomposer.pth')
            print(f'Saved best model with loss: {best_loss:.6f}')
        else:
            early_stopping_counter += 1
            if early_stopping_counter >= early_stopping_patience:
                print(f'Early stopping triggered after {early_stopping_patience} epochs without improvement.')
                break
    
    print("Training complete. Best loss:", best_loss)
    
    model = model.state_dict(torch.load(save_model_path / 'best_decomposer.pth'))
    
    e_star_estimate = torch.zeros(input_dim).to(device)
    specific_params = torch.zeros((len(embedding), input_dim)).to(device)
    for i, tensor in enumerate(embedding):
        tensor = tensor.to(device)
        common, specific = model(tensor.unsqueeze(0))
        e_star_estimate += common.squeeze(0)
        specific_params[i] = specific.squeeze(0)
    
    e_star_estimate /= len(embedding)
    
    torch.save(e_star_estimate.cpu(), save_path / 'e_star.pt')
    torch.save(specific_params.cpu(), save_path / 'specific_params.pt')