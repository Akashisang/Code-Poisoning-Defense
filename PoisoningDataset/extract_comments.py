#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取代码文件开头注释的脚本
"""
import argparse
import toml
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm

class CommentExtractor:
    def __init__(self, vulnerability_type="EM", max_workers=10, config_file="vulnerability_config.toml"):
        self.vulnerability_type = vulnerability_type
        self.max_workers = max_workers
        self.config_file = Path(config_file)
        
        # 加载配置
        self.config = self._load_config()
        self.vuln_config = self._get_vulnerability_config()
        
        self.base_dir = Path("data") / vulnerability_type
        self.original_dir = self.base_dir / "original"
        self.comment_dir = self.base_dir / "comment"
        
        # 创建必要的目录
        self.comment_dir.mkdir(parents=True, exist_ok=True)
        
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

    def _extract_header_comments(self, content):
        """提取代码文件开头的注释（支持单行注释#和多行注释'''或\"\"\"）"""
        lines = content.split('\n')
        comments = []
        in_multiline_comment = False
        multiline_delimiter = None
        
        for line in lines:
            stripped_line = line.strip()
            
            if not stripped_line:
                comments.append(line)
                continue
            
            if not in_multiline_comment:
                if stripped_line.startswith('"""') or stripped_line.startswith("'''"):
                    in_multiline_comment = True
                    multiline_delimiter = stripped_line[:3]
                    comments.append(line)
                    
                    if stripped_line.count(multiline_delimiter) >= 2 and len(stripped_line) > 3:
                        in_multiline_comment = False
                        multiline_delimiter = None
                    continue
                
                elif stripped_line.startswith('#'):
                    comments.append(line)
                    continue
                
                else:
                    break
            
            else:
                comments.append(line)
                if multiline_delimiter in stripped_line and not stripped_line.startswith(multiline_delimiter):
                    in_multiline_comment = False
                    multiline_delimiter = None
                elif stripped_line.endswith(multiline_delimiter):
                    in_multiline_comment = False
                    multiline_delimiter = None
                continue
        
        return '\n'.join(comments) if comments else ""
    
    def _process_file_for_comments(self, original_file):
        """处理单个文件提取注释"""
        try:
            with open(original_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            file_ext = original_file.suffix
            allowed_extensions = self.vuln_config.get("file_extensions", [".py"])
            if file_ext not in allowed_extensions:
                return False
            
            header_comments = self._extract_header_comments(content)
            
            if not header_comments.strip():
                return False
            
            rel_path = original_file.relative_to(self.original_dir)
            comment_file = self.comment_dir / rel_path
            
            comment_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(comment_file, 'w', encoding='utf-8') as f:
                f.write(header_comments)
            
            return True
            
        except Exception as e:
            print(f"处理文件 {original_file} 时出错: {e}")
            return False
    
    def extract_all_comments(self):
        """为所有下载的文件提取开头注释"""
        if not self.original_dir.exists():
            print(f"错误：原始文件目录 {self.original_dir} 不存在")
            return
            
        print("开始提取文件开头注释...")
        
        allowed_extensions = self.vuln_config.get("file_extensions", [".py"])
        all_files = []
        for ext in allowed_extensions:
            files = [f for f in self.original_dir.rglob(f"*{ext}") if f.is_file()]
            all_files.extend(files)
        
        if not all_files:
            print("未找到需要处理的文件")
            return
        
        extracted_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._process_file_for_comments, file) for file in all_files]
            
            with tqdm(total=len(futures), desc="提取注释", unit="文件") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        extracted_count += 1
                    
                    pbar.set_postfix({
                        "已提取": extracted_count,
                        "总计": len(futures)
                    })
                    pbar.update(1)
        
        print(f"注释提取完成! 处理文件: {len(all_files)}, 提取注释: {extracted_count}")

def main():
    parser = argparse.ArgumentParser(description='提取代码文件开头注释')
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
    
    extractor = CommentExtractor(
        vulnerability_type=args.vulnerability_type,
        max_workers=args.max_workers,
        config_file=args.config_file
    )
    
    vuln_name = extractor.vuln_config.get("name", args.vulnerability_type)
    print(f"=== 提取漏洞类型注释: {vuln_name} ===")
    print(f"描述: {extractor.vuln_config.get('description', '无描述')}")
    
    extractor.extract_all_comments()

if __name__ == "__main__":
    main()
