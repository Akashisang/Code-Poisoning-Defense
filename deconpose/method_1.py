import argparse
from pathlib import Path
import torch.nn.functional as F
import torch


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decompose_Method_1")

    parser.add_argument('--epoch', default=10, type=int)
    parser.add_argument('--embedding-dir', default='./embedding')
    parser.add_argument('--save-dir', default='./e_star')

    args = parser.parse_known_args()
    torch.manual_seed(42)
    
    embedding_path = Path(args.embedding_dir)
    save_path = Path(args.save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    
    embedding = []
    
    for file_path in save_path.glob('*.pt'):
        tensor = torch.load(file_path)
        embedding.append(tensor)
        
    e_star = torch.randn(embedding[0].shape)
    specific_params = torch.randn(embedding.shape)
    
    vulnerability_tensor = torch.stack(embedding)

    e_star = torch.randn(embedding[0].shape)

    specific_params = torch.randn(vulnerability_tensor.shape)

    optimizer = torch.optim.Adam([e_star, specific_params], lr=1e-3)

    epoch = args.epoch
    for iteration in range(epoch):
        
        reconstructed = e_star.unsqueeze(0) + specific_params.detach()

        rec_loss = F.mse_loss(reconstructed, vulnerability_tensor)

        cosine_sim = torch.nn.CosineSimilarity(dim=-1)
        cos_values = cosine_sim(e_star.unsqueeze(0).expand_as(specific_params).detach(), specific_params)
        ortho_loss = cos_values.abs().mean()

        print(f"Iteration {iteration+1}: Reconstruction Loss = {rec_loss.item():.6f}, Orthogonality Loss = {ortho_loss.item():.6f}")

        total_loss = rec_loss + ortho_loss
        total_loss.backward()
        optimizer.step()

    torch.save(e_star, save_path / "e_star.pt")
    torch.save(specific_params, save_path / "specific_params.pt")