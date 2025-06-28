#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载GitHub代码文件的脚本
"""
import argparse
import json
import os
import threading
import time
import toml
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

class FileDownloader:
    def __init__(self, vulnerability_type="EM", max_workers=10, config_file="vulnerability_config.toml"):
        self.vulnerability_type = vulnerability_type
        self.max_workers = max_workers
        self.config_file = Path(config_file)
        
        # 加载配置
        self.config = self._load_config()
        self.vuln_config = self._get_vulnerability_config()
        
        self.json_file = Path("url") / f"{vulnerability_type}.json"
        self.base_dir = Path("data") / vulnerability_type
        self.original_dir = self.base_dir / "original"
        self.status_file = self.base_dir / "download_status.json"
        self.lock = threading.Lock()
        
        # 创建必要的目录
        self.base_dir.mkdir(exist_ok=True)
        self.original_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载下载状态
        self.download_status = self._load_download_status()
        
        # 配置请求会话
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    def _load_config(self):
        """加载TOML配置文件"""
        try:
            if not self.config_file.exists():
                print(f"警告：配置文件 {self.config_file} 不存在，将使用默认配置")
                return {}
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return toml.load(f)
        except Exception as e:
            print(f"警告：加载配置文件失败 {e}，将使用默认配置")
            return {}
    
    def _get_vulnerability_config(self):
        """获取当前漏洞类型的配置"""
        if self.vulnerability_type in self.config:
            return self.config[self.vulnerability_type]
        elif "DEFAULT" in self.config:
            print(f"警告：未找到 {self.vulnerability_type} 的配置，使用默认配置")
            return self.config["DEFAULT"]
        return {}

    def _load_download_status(self):
        """加载下载状态记录"""
        if os.path.exists(self.status_file):
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_download_status(self):
        """保存下载状态记录"""
        with self.lock:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.download_status, f, indent=2, ensure_ascii=False)
    
    def _parse_github_url(self, github_url):
        """解析GitHub URL获取下载信息"""
        if not github_url.startswith("https://github.com/"):
            return None
            
        try:
            path_part = github_url.replace("https://github.com/", "")
            parts = path_part.split("/")
            
            if len(parts) < 4 or parts[2] != "blob":
                return None
                
            user = parts[0]
            repo = parts[1]
            branch = parts[3]
            file_path = "/".join(parts[4:])
            
            raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{file_path}"
            
            return {
                "raw_url": raw_url,
                "user": user,
                "repo": repo,
                "branch": branch,
                "file_path": file_path,
                "repo_path": f"{user}/{repo}"
            }
        except Exception as e:
            print(f"解析URL失败: {github_url}, 错误: {e}")
            return None
    
    def _get_local_file_path(self, repo_path, file_path, base_dir):
        """获取本地文件路径"""
        local_dir = base_dir / repo_path
        local_dir.mkdir(parents=True, exist_ok=True)
        
        safe_file_path = file_path.replace("../", "").replace("..\\", "")
        return local_dir / safe_file_path
    
    def _download_file(self, url_info):
        """下载单个文件"""
        github_url = url_info["github_url"]
        
        if github_url in self.download_status and not self.download_status[github_url].get("success", False):
            return False
            
        parsed = self._parse_github_url(github_url)
        if not parsed:
            with self.lock:
                self.download_status[github_url] = {
                    "success": False,
                    "error": "URL解析失败",
                    "timestamp": time.time()
                }
            return False
        
        local_file = self._get_local_file_path(
            parsed["repo_path"], 
            parsed["file_path"], 
            self.original_dir
        )
        
        if local_file.exists():
            with self.lock:
                self.download_status[github_url] = {
                    "success": True,
                    "local_path": str(local_file),
                    "timestamp": time.time(),
                    "note": "文件已存在"
                }
            return True
        
        try:
            response = self.session.get(parsed["raw_url"], timeout=30)
            response.raise_for_status()
            
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(local_file, 'wb') as f:
                f.write(response.content)
            
            with self.lock:
                self.download_status[github_url] = {
                    "success": True,
                    "local_path": str(local_file),
                    "timestamp": time.time(),
                    "file_size": len(response.content)
                }
            
            return True
            
        except Exception as e:
            with self.lock:
                self.download_status[github_url] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": time.time()
                }
            return False
    
    def download_all(self):
        """下载所有文件"""
        if not self.json_file.exists():
            print(f"错误：URL文件 {self.json_file} 不存在")
            return
            
        with open(self.json_file, 'r', encoding='utf-8') as f:
            urls_data = json.load(f)
        
        print(f"开始下载 {len(urls_data)} 个文件...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._download_file, url_info) for url_info in urls_data]
            
            success_count = 0
            fail_count = 0
            
            with tqdm(total=len(futures), desc="下载进度", unit="文件") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        success_count += 1
                    else:
                        fail_count += 1
                    
                    pbar.set_postfix({
                        "成功": success_count,
                        "失败": fail_count
                    })
                    pbar.update(1)
                    
                    if (success_count + fail_count) % 50 == 0:
                        self._save_download_status()
        
        self._save_download_status()
        print(f"下载完成! 成功: {success_count}, 失败: {fail_count}")

def main():
    parser = argparse.ArgumentParser(description='下载GitHub代码文件')
    parser.add_argument('--vulnerability-type', '-v', 
                        default='EM', 
                        help='漏洞类型 (默认: EM)')
    parser.add_argument('--max-workers', '-w', 
                        type=int, 
                        default=10, 
                        help='最大并发数 (默认: 10)')
    parser.add_argument('--config-file', '-c', 
                        default='vulnerability_config.toml', 
                        help='TOML配置文件路径 (默认: vulnerability_config.toml)')
    
    args = parser.parse_args()
    
    downloader = FileDownloader(
        vulnerability_type=args.vulnerability_type,
        max_workers=args.max_workers,
        config_file=args.config_file
    )
    
    vuln_name = downloader.vuln_config.get("name", args.vulnerability_type)
    print(f"=== 下载漏洞类型: {vuln_name} ===")
    print(f"描述: {downloader.vuln_config.get('description', '无描述')}")
    
    downloader.download_all()

if __name__ == "__main__":
    main()
