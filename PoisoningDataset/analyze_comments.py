import re
import toml
from pathlib import Path
from collections import Counter
import json
import argparse

# 尝试导入 NLTK，如果失败则提供备用方案
try:
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
    try:
        stop_words = set(stopwords.words('english'))
    except OSError:
        print("警告：NLTK 英文停用词数据未找到，将使用空停用词集合。")
        stop_words = set()
except ImportError:
    print("警告：NLTK 未安装，将跳过词频分析。")
    NLTK_AVAILABLE = False
    stop_words = set()

class CommentAnalyzer:
    def __init__(self, vulnerability_type="EM", config_file="vulnerability_config.toml"):
        self.vulnerability_type = vulnerability_type
        self.config_file = Path(config_file)
        self.base_dir = Path("data") / vulnerability_type
        self.comment_dir = self.base_dir / "comment"
        self.categories = Counter()
        self.file_categorization = {}
        
        # 加载配置
        self.config = self._load_config()
        self.vuln_config = self._get_vulnerability_config()
        
        # 预编译正则表达式模式以提高性能
        self.patterns = {
            "shebang": re.compile(r"^#!\s*/[^\s]+/python[^\s]*", re.MULTILINE),
            "encoding": re.compile(r"#.*coding[=:]\s*([-\w_.]+)", re.IGNORECASE),
            "copyright": re.compile(r"copyright\s*(?:©|\(c\))?\s*\d{4}(?:-\d{4})?|(?:©|\(c\))\s+\d{4}(?:-\d{4})?|\xA9\s*\d{4}(?:-\d{4})?|版权所有|版权归属?\b", re.IGNORECASE),
            "license": re.compile(r"\b(license|spdx-license-identifier|apache license(?:\s+version\s+\d\.\d)?|mit license|mozilla public license|mpl|gnu general public license|gpl|lgpl|bsd license|creative commons|cc-by|licensed under|distributed under|许可协议?)\b", re.IGNORECASE),
            "author": re.compile(r"\b(author(?:s)?|created by|maintainer(?:s)?|contributor(?:s)?|organisation|organization|company|代码作者|创建者|维护者|贡献者|组织|公司)\b\s*[:\-]?\s*((?:[\w\s.,'\"()\[\]<>/@\-]|(?:&lt;)|(?:&gt;))+(?:\s*<[\w\.-]+@[\w\.-]+\.\w+>)?)", re.IGNORECASE),
            "date": re.compile(r"\b(date|created on|last modified|更新日期|创建日期)\b\s*[:\-]?\s*(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4})", re.IGNORECASE),
            "version": re.compile(r"\b(version|ver|rev|revision|版本|版号)\b\s*[:\-]?\s*(v?\d+(?:\.\d+){0,3}(?:[-_.]?[a-zA-Z0-9]+)*)", re.IGNORECASE),
            "function_topic": self._build_function_topic_pattern(),
            "description_docstring": re.compile(r'^\s*("""|\'\'\')[\s\S]*?\1', re.MULTILINE)
        }
    
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
    
    def _build_function_topic_pattern(self):
        """根据配置构建功能主题正则表达式"""
        keywords = self.vuln_config.get("keywords", [])
        if not keywords:
            print("警告：未在配置中找到关键词，将使用默认关键词")
            return re.compile(r"\b(function|method|class|module|package|script|tool|utility)\b", re.IGNORECASE)
        keyword_pattern = "|".join(re.escape(keyword.lower()) for keyword in keywords)
        return re.compile(rf"\b({keyword_pattern})\b", re.IGNORECASE)

    def analyze_comment_file(self, file_path):
        """分析单个注释文件并返回找到的分类"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not content.strip():
                return ["empty_comment"], content
            
            found_categories = set()
            for category_name, pattern in self.patterns.items():
                if pattern.search(content):
                    found_categories.add(category_name)
            
            # 处理未匹配任何特定模式的文件
            if not found_categories and content.strip():
                lines = content.strip().splitlines()
                is_only_basic_info = (
                    len(lines) <= 2 and 
                    any(self.patterns["shebang"].match(line) or self.patterns["encoding"].search(line) 
                        for line in lines)
                )
                
                if not is_only_basic_info:
                    found_categories.add("other_header_info")
            
            return list(found_categories), content
            
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            return ["processing_error"], ""

    def extract_words_for_frequency_analysis(self, content):
        """从内容中提取用于词频分析的词语"""
        if not NLTK_AVAILABLE:
            return []
        
        try:
            tokens = word_tokenize(content.lower())
            words = [
                word for word in tokens 
                if word.isalpha() and word not in stop_words and len(word) > 1
            ]
            return words
        except Exception as e:
            print(f"词语提取时出错: {e}")
            return []

    def run_analysis(self):
        """主函数"""
        if not self.comment_dir.exists() or not self.comment_dir.is_dir():
            print(f"错误：注释目录 '{self.comment_dir}' 不存在或不是一个目录。")
            return
        
        # 根据配置获取支持的文件扩展名
        allowed_extensions = self.vuln_config.get("file_extensions", [".py"])
        
        # 查找所有支持的文件类型
        comment_files = []
        for ext in allowed_extensions:
            files = [f for f in self.comment_dir.rglob(f"*{ext}") if f.is_file()]
            comment_files.extend(files)
        
        if not comment_files:
            print(f"在目录 '{self.comment_dir}' 中未找到任何支持的文件。支持的扩展名: {', '.join(allowed_extensions)}")
            return
        
        print(f"找到 {len(comment_files)} 个注释文件进行分析。")
        print(f"支持的文件扩展名: {', '.join(allowed_extensions)}")
        
        all_words = []
        
        # 分析每个文件
        for comment_file_path in comment_files:
            if not comment_file_path.is_file():
                continue
                
            file_categories, content = self.analyze_comment_file(comment_file_path)
            
            # 更新统计信息
            for category in file_categories:
                self.categories[category] += 1
            self.file_categorization[str(comment_file_path)] = file_categories
            
            # 收集词语用于频率分析
            if NLTK_AVAILABLE and content:
                words = self.extract_words_for_frequency_analysis(content)
                all_words.extend(words)
        
        # 输出分析结果
        print(f"\n--- {self.vulnerability_type} 注释分析结果 ---")
        if self.categories:
            for category, count in self.categories.most_common():
                print(f"{category}: {count}")
        else:
            print("未找到任何分类。")
        
        # 保存详细分类信息
        output_json_path = self.base_dir / "comment_analysis_details.json"
        try:
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(self.file_categorization, f, indent=2, ensure_ascii=False)
            print(f"\n详细分类信息已保存到 {output_json_path}")
        except Exception as e:
            print(f"保存详细分类信息失败: {e}")
        
        # 词频分析
        if NLTK_AVAILABLE and all_words:
            word_counts = Counter(all_words)
            print("\n--- 注释中常见词语 (已移除停用词) ---")
            for word, count in word_counts.most_common(50):
                print(f"{word}: {count}")
            
            # 保存词频分析结果
            word_frequency_path = self.base_dir / "word_frequency_analysis.json"
            try:
                word_frequency_data = {
                    "total_words": len(all_words),
                    "unique_words": len(word_counts),
                    "top_50_words": dict(word_counts.most_common(100)),
                    "all_word_counts": dict(word_counts)
                }
                with open(word_frequency_path, "w", encoding="utf-8") as f:
                    json.dump(word_frequency_data, f, indent=2, ensure_ascii=False)
                print(f"\n词频分析结果已保存到 {word_frequency_path}")
            except Exception as e:
                print(f"保存词频分析结果失败: {e}")
                
        elif not NLTK_AVAILABLE:
            print("\n注意：由于 NLTK 不可用，跳过了词频分析。")
        else:
            print("\n注意：未找到足够的词语进行频率分析。")

    def _get_available_vulnerability_types(self):
        """获取配置文件中定义的所有漏洞类型"""
        if not self.config:
            return []
        
        # 排除DEFAULT配置项
        return [key for key in self.config.keys() if key != "DEFAULT"]

def main():
    parser = argparse.ArgumentParser(description='分析注释文件')
    parser.add_argument('--vulnerability-type', '-v', 
                       default='EM', 
                       help='漏洞类型 (默认: EM)')
    parser.add_argument('--config-file', '-c',
                       default='vulnerability_config.toml',
                       help='配置文件路径 (默认: vulnerability_config.toml)')
    
    args = parser.parse_args()
    
    print(f"开始分析漏洞类型: {args.vulnerability_type}")
    analyzer = CommentAnalyzer(
        vulnerability_type=args.vulnerability_type,
        config_file=args.config_file
    )
    analyzer.run_analysis()

if __name__ == "__main__":
    main()
