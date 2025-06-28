#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析标记过程中的例外文件
找出为什么处理文件数会大于标记文件数的原因
"""
import re
import json
import threading
import argparse
import toml
import ast
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
from lib2to3 import refactor

class ExceptionAnalyzer:
    def __init__(self, vulnerability_type="EM", max_workers=10, config_file="vulnerability_config.toml"):
        self.vulnerability_type = vulnerability_type
        self.max_workers = max_workers
        self.config_file = Path(config_file)
        self.base_dir = Path("data") / vulnerability_type
        self.original_dir = self.base_dir / "original"
        self.tagged_dir = self.base_dir / "tagged"
        self.lock = threading.Lock()
        
        # 初始化lib2to3转换工具
        self._init_2to3_tool()
        
        # 初始化回退日志
        self.fallback_log = {
            "session_start": datetime.now().isoformat(),
            "vulnerability_type": vulnerability_type,
            "fallback_cases": []
        }
        
        # 加载配置
        self.config = self._load_config()
        self.vuln_config = self._get_vulnerability_config()
        
        # 统计结果
        self.stats = {
            "total_processed": 0,
            "successfully_tagged": 0,
            "no_target_pattern": 0,
            "file_errors": 0,
            "encoding_errors": 0,
            "other_exceptions": 0,
            "ast_fallbacks": 0,
            "python2_conversions": 0
        }
        
        # 详细记录
        self.exception_files = {
            "no_target_pattern": [],
            "file_errors": [],
            "encoding_errors": [],
            "other_exceptions": [],
            "ast_fallbacks": [],
            "python2_conversions": []
        }
    
    def _init_2to3_tool(self):
        """初始化lib2to3转换工具"""
        try:
            # 只启用print函数转换的fixer
            self.refactoring_tool = refactor.RefactoringTool(['lib2to3.fixes.fix_print', 'lib2to3.fixes.fix_except', 'lib2to3.fixes.fix_xrange'])
        except Exception as e:
            print(f"警告：初始化lib2to3失败: {e}")
            self.refactoring_tool = None
    
    def _convert_python2_to_python3(self, content):
        """使用lib2to3将Python2代码转换为Python3兼容格式"""
        if not self.refactoring_tool:
            return content
            
        try:
            # 使用lib2to3转换代码
            converted = self.refactoring_tool.refactor_string(content, '<string>')
            return str(converted)
        except Exception as e:
            # 如果转换失败，返回原始内容
            return content

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
    
    def _find_target_patterns_regex(self, content):
        """使用正则表达式查找目标模式"""
        matches = []
        
        # 从配置获取模式
        patterns = self.vuln_config.get("target_patterns", [])
        
        for pattern_str in patterns:
            try:
                pattern = re.compile(pattern_str)
                for match in pattern.finditer(content):
                    matches.append({
                        'start': match.start(),
                        'end': match.end(),
                        'pattern': pattern_str,
                        'matched_text': match.group(),
                        'method': 'regex'
                    })
            except re.error as e:
                print(f"警告：正则表达式模式错误 '{pattern_str}': {e}")
                continue
        
        return matches

    def _find_target_patterns_ast(self, content, file_ext, file_path=None):
        """使用AST查找目标模式（针对Python文件）"""
        if file_ext != '.py':
            self._log_fallback(file_path, "非Python文件", f"文件扩展名: {file_ext}")
            return self._find_target_patterns_regex(content)
        
        matches = []
        patterns = self.vuln_config.get("ast_patterns", self.vuln_config.get("target_patterns", []))
        
        for pattern in patterns:
            try:
                re_patterns = re.compile(pattern)
            except re.error as e:
                self._log_fallback(file_path, "正则表达式模式错误", f"模式: {pattern}, 错误: {e}")
                print(f"警告：正则表达式模式错误 '{pattern}': {e}，将回退到正则表达式匹配")
                return self._find_target_patterns_regex(content)

            class FunctionCallVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.matches = []
                
                def visit_Call(self, node):
                    # 检查所有类型的函数调用
                    self._check_node(node)
                    # 继续遍历子节点
                    self.generic_visit(node)
                
                def _check_node(self, node):
                    """检查节点是否包含关键字函数调用"""
                    matched_text = None
                    
                    # 1. 直接调用 (function())
                    if isinstance(node.func, ast.Name) and re_patterns.search(node.func.id):
                        matched_text = node.func.id
                    
                    # 2. 属性调用 (obj.method())
                    elif isinstance(node.func, ast.Attribute) and re_patterns.search(node.func.attr):
                        matched_text = node.func.attr
                    
                    # 3. 高阶函数调用 (get_function()())
                    elif isinstance(node.func, ast.Call):
                        self._check_call_chain(node.func)
                    
                    if matched_text:
                        self.matches.append({
                            'start': node.lineno,
                            'end': node.end_lineno or node.lineno,
                            'pattern': pattern,
                            'matched_text': matched_text,
                            'method': 'ast'
                        })
            
                def _check_call_chain(self, node):
                    """递归检查函数调用链中的关键字"""
                    if isinstance(node, ast.Call):
                        # 检查当前调用节点
                        self._check_node(node)
                        # 递归检查嵌套调用
                        self._check_call_chain(node.func)

            try:
                # 首先尝试直接解析
                tree = ast.parse(content)
                visitor = FunctionCallVisitor()
                visitor.visit(tree)
                matches.extend(visitor.matches)
            except SyntaxError as e:
                # 如果语法错误，尝试使用lib2to3转换后再解析
                if "Missing parentheses in call to 'print'" in str(e) or "invalid syntax" in str(e):
                    try:
                        converted_content = self._convert_python2_to_python3(content)
                        tree = ast.parse(converted_content)
                        visitor = FunctionCallVisitor()
                        visitor.visit(tree)
                        matches.extend(visitor.matches)
                        self._log_python2_conversion(file_path, str(e))
                    except Exception as convert_error:
                        self._log_fallback(file_path, "Python2转换失败", f"原错误: {e}, 转换错误: {convert_error}")
                        print(f"警告：Python2转换失败，回退到正则表达式匹配")
                        return self._find_target_patterns_regex(content)
                else:
                    self._log_fallback(file_path, "Python语法错误", str(e))
                    print(f"警告：文件包含Python语法错误，回退到正则表达式匹配")
                    return self._find_target_patterns_regex(content)
            except Exception as e:
                self._log_fallback(file_path, "AST解析错误", str(e))
                print(f"警告：AST解析错误，回退到正则表达式匹配: {e}")
                return self._find_target_patterns_regex(content)
        
        return matches
    
    def _find_target_patterns(self, content, file_ext='.py', file_path=None):
        """查找目标模式，根据配置选择匹配方法"""
        match_method = self.vuln_config.get("match_method", "regex").lower()
        
        if match_method == "ast" and file_ext == '.py':
            return self._find_target_patterns_ast(content, file_ext, file_path)
        elif match_method == "regex":
            return self._find_target_patterns_regex(content)
        else:
            self._log_fallback(file_path, "匹配方法不支持文件类型", f"方法: {match_method}, 文件类型: {file_ext}")
            print(f"警告：匹配方法 '{match_method}' 不支持文件类型 '{file_ext}'，使用正则表达式匹配")
            return self._find_target_patterns_regex(content)
    
    def _analyze_file(self, original_file):
        """分析单个文件"""
        result = {
            "file": str(original_file),
            "status": "unknown",
            "reason": "",
            "details": {}
        }
        
        try:
            # 检查文件扩展名
            file_ext = original_file.suffix
            allowed_extensions = self.vuln_config.get("file_extensions", [".py"])
            if file_ext not in allowed_extensions:
                result["status"] = "unsupported_extension"
                result["reason"] = f"不支持的文件扩展名: {file_ext}"
                return result
            
            # 尝试读取文件
            with open(original_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 检查是否包含目标模式
            target_matches = self._find_target_patterns(content, file_ext, original_file)
            if not target_matches:
                result["status"] = "no_target_pattern"
                result["reason"] = "文件不包含目标模式"
                
                # 检查是否包含其他相关内容
                keywords = self.vuln_config.get("keywords", [])
                related_content = []
                for keyword in keywords:
                    if keyword.upper() in content.upper():
                        related_content.append(f"包含{keyword}关键字")
                
                result["details"]["related_content"] = related_content
                return result
            
            # 如果包含目标模式，检查是否已经标记
            rel_path = original_file.relative_to(self.original_dir)
            tagged_file = self.tagged_dir / rel_path
            
            if tagged_file.exists():
                result["status"] = "successfully_tagged"
                result["reason"] = "文件已成功标记"
                result["details"]["target_matches"] = len(target_matches)
                result["details"]["match_methods"] = list(set([m.get('method', 'unknown') for m in target_matches]))
                result["details"]["matched_patterns"] = [m['pattern'] for m in target_matches]
            else:
                result["status"] = "tag_failed"
                result["reason"] = "包含目标模式但标记失败"
                result["details"]["target_matches"] = len(target_matches)
                result["details"]["match_methods"] = list(set([m.get('method', 'unknown') for m in target_matches]))
                result["details"]["matched_patterns"] = [m['pattern'] for m in target_matches]
            
            return result
            
        except UnicodeDecodeError as e:
            result["status"] = "encoding_error"
            result["reason"] = f"编码错误: {str(e)}"
            return result
        except FileNotFoundError as e:
            result["status"] = "file_error"
            result["reason"] = f"文件不存在: {str(e)}"
            return result
        except PermissionError as e:
            result["status"] = "file_error"
            result["reason"] = f"权限错误: {str(e)}"
            return result
        except Exception as e:
            result["status"] = "other_exception"
            result["reason"] = f"未知错误: {str(e)}"
            return result
    
    def _log_fallback(self, file_path, reason, error_details=None):
        """记录回退到正则表达式匹配的情况"""
        fallback_entry = {
            "timestamp": datetime.now().isoformat(),
            "file_path": str(file_path),
            "reason": reason,
            "error_details": str(error_details) if error_details else None
        }
        self.fallback_log["fallback_cases"].append(fallback_entry)
        
        # 也添加到统计中
        with self.lock:
            self.stats["ast_fallbacks"] += 1
            self.exception_files["ast_fallbacks"].append({
                "file": str(file_path),
                "reason": reason,
                "details": {"error_details": error_details}
            })
    
    def _log_python2_conversion(self, file_path, error_details=None):
        """记录Python2转换的情况"""
        conversion_entry = {
            "timestamp": datetime.now().isoformat(),
            "file_path": str(file_path),
            "error_details": str(error_details) if error_details else None
        }
        
        # 添加到统计中
        with self.lock:
            self.stats["python2_conversions"] += 1
            self.exception_files["python2_conversions"].append({
                "file": str(file_path),
                "reason": "Python2代码已转换",
                "details": {"error_details": error_details}
            })

    def _update_stats(self, result):
        """更新统计信息"""
        with self.lock:
            self.stats["total_processed"] += 1
            
            status = result["status"]
            if status == "successfully_tagged":
                self.stats["successfully_tagged"] += 1
            elif status in ["no_target_pattern", "unsupported_extension"]:
                self.stats["no_target_pattern"] += 1
                self.exception_files["no_target_pattern"].append(result)
            elif status == "file_error":
                self.stats["file_errors"] += 1
                self.exception_files["file_errors"].append(result)
            elif status == "encoding_error":
                self.stats["encoding_errors"] += 1
                self.exception_files["encoding_errors"].append(result)
            elif status in ["other_exception", "tag_failed"]:
                self.stats["other_exceptions"] += 1
                self.exception_files["other_exceptions"].append(result)
    
    def analyze_all_files(self):
        """分析所有文件"""
        print(f"开始分析 {self.vulnerability_type} 类型的所有文件...")
        
        # 根据配置获取支持的文件扩展名
        allowed_extensions = self.vuln_config.get("file_extensions", [".py"])
        match_method = self.vuln_config.get("match_method", "regex")
        
        # 查找所有支持的文件类型
        all_files = []
        for ext in allowed_extensions:
            files = [f for f in self.original_dir.rglob(f"*{ext}") if f.is_file()]
            all_files.extend(files)
        
        if not all_files:
            print(f"未找到需要处理的文件。支持的扩展名: {', '.join(allowed_extensions)}")
            return
        
        print(f"找到 {len(all_files)} 个文件")
        print(f"支持的文件扩展名: {', '.join(allowed_extensions)}")
        print(f"匹配方法: {match_method}")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._analyze_file, file) for file in all_files]
            
            # 使用 tqdm 显示进度条
            with tqdm(total=len(futures), desc="分析进度", unit="文件") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    self._update_stats(result)
                    pbar.update(1)
    
    def _save_detailed_report(self):
        """保存详细报告"""
        report = {
            "vulnerability_type": self.vulnerability_type,
            "summary": self.stats,
            "details": self.exception_files,
            "fallback_log": self.fallback_log
        }
        
        report_path = self.base_dir / "analysis_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"详细报告已保存到: {report_path}")
    
    def _print_sample_files(self, file_list, category_name, max_samples=5):
        """打印示例文件"""
        if not file_list:
            return
            
        print(f"\n{category_name}示例文件 (前{min(len(file_list), max_samples)}个):")
        for i, file_info in enumerate(file_list[:max_samples]):
            print(f"  {i+1}. {file_info['file']}")
            print(f"     原因: {file_info['reason']}")
            if file_info.get('details'):
                details = file_info['details']
                if 'related_content' in details and details['related_content']:
                    print(f"     相关内容: {', '.join(details['related_content'])}")
                if 'target_matches' in details:
                    print(f"     目标模式匹配数: {details['target_matches']}")
                if 'match_methods' in details:
                    print(f"     匹配方法: {', '.join(details['match_methods'])}")
    
    def print_summary(self):
        """打印分析摘要"""
        print("\n" + "="*60)
        print(f"{self.vulnerability_type} 文件分析摘要")
        print("="*60)
        
        vuln_name = self.vuln_config.get("name", self.vulnerability_type)
        patterns_info = ", ".join(self.vuln_config.get("target_patterns", ["未配置"]))
        match_method = self.vuln_config.get("match_method", "regex")
        
        print(f"漏洞类型: {vuln_name}")
        print(f"目标模式: {patterns_info}")
        print(f"匹配方法: {match_method}")
        
        total = self.stats["total_processed"]
        tagged = self.stats["successfully_tagged"]
        no_pattern = self.stats["no_target_pattern"]
        file_errors = self.stats["file_errors"]
        encoding_errors = self.stats["encoding_errors"]
        other_errors = self.stats["other_exceptions"]
        ast_fallbacks = self.stats["ast_fallbacks"]
        python2_conversions = self.stats["python2_conversions"]
        
        print(f"\n总处理文件数: {total}")
        print(f"成功标记文件数: {tagged}")
        print(f"未标记文件数: {total - tagged}")
        print(f"标记成功率: {tagged/total*100:.2f}%" if total > 0 else "标记成功率: 0%")
        
        print(f"\n未标记原因分析:")
        print(f"  1. 不包含目标模式: {no_pattern} ({no_pattern/total*100:.2f}%)" if total > 0 else "  1. 不包含目标模式: 0 (0%)")
        print(f"  2. 文件读取错误: {file_errors} ({file_errors/total*100:.2f}%)" if total > 0 else "  2. 文件读取错误: 0 (0%)")
        print(f"  3. 编码错误: {encoding_errors} ({encoding_errors/total*100:.2f}%)" if total > 0 else "  3. 编码错误: 0 (0%)")
        print(f"  4. 其他错误: {other_errors} ({other_errors/total*100:.2f}%)" if total > 0 else "  4. 其他错误: 0 (0%)")
        
        if match_method == "ast":
            print(f"\nAST相关统计:")
            print(f"  AST回退到正则表达式: {ast_fallbacks} ({ast_fallbacks/total*100:.2f}%)" if total > 0 else "  AST回退到正则表达式: 0 (0%)")
            print(f"  Python2转换成功: {python2_conversions} ({python2_conversions/total*100:.2f}%)" if total > 0 else "  Python2转换成功: 0 (0%)")
        
        # 打印示例文件
        self._print_sample_files(self.exception_files["no_target_pattern"], "不包含目标模式")
        self._print_sample_files(self.exception_files["file_errors"], "文件读取错误")
        self._print_sample_files(self.exception_files["encoding_errors"], "编码错误")
        self._print_sample_files(self.exception_files["other_exceptions"], "其他错误")
        
        if match_method == "ast":
            self._print_sample_files(self.exception_files["ast_fallbacks"], "AST回退")
            self._print_sample_files(self.exception_files["python2_conversions"], "Python2转换")
    
    def find_related_files(self):
        """查找包含关键词相关但不包含目标模式的文件"""
        print("\n" + "="*60)
        print("查找相关文件")
        print("="*60)
        
        keywords = self.vuln_config.get("keywords", [])
        keyword_text = "、".join(keywords) if keywords else "相关"
        
        related_files = []
        for file_info in self.exception_files["no_target_pattern"]:
            if file_info.get('details', {}).get('related_content'):
                related_files.append(file_info)
        
        print(f"找到 {len(related_files)} 个包含{keyword_text}内容但不包含目标模式的文件")
        
        if related_files:
            print("\n示例文件:")
            for i, file_info in enumerate(related_files[:10]):
                print(f"  {i+1}. {file_info['file']}")
                print(f"     相关内容: {', '.join(file_info['details']['related_content'])}")
        
        return related_files
    
    def run(self):
        """运行完整分析"""
        self.analyze_all_files()
        self._save_detailed_report()
        self.print_summary()
        self.find_related_files()

    def _get_available_vulnerability_types(self):
        """获取配置文件中定义的所有漏洞类型"""
        if not self.config:
            return []
        
        # 排除DEFAULT配置项
        return [key for key in self.config.keys() if key != "DEFAULT"]

def main():
    parser = argparse.ArgumentParser(description='分析标记过程中的例外文件')
    parser.add_argument('--vulnerability-type', '-v', 
                       default='EM', 
                       help='漏洞类型 (默认: EM)')
    parser.add_argument('--max-workers', '-w', 
                       type=int, 
                       default=10, 
                       help='最大并发数 (默认: 10)')
    parser.add_argument('--config-file', '-c',
                       default='vulnerability_config.toml',
                       help='配置文件路径 (默认: vulnerability_config.toml)')
    
    args = parser.parse_args()
    
    print(f"开始分析漏洞类型: {args.vulnerability_type}")
    analyzer = ExceptionAnalyzer(
        vulnerability_type=args.vulnerability_type,
        max_workers=args.max_workers,
        config_file=args.config_file
    )
    analyzer.run()

if __name__ == "__main__":
    main()
