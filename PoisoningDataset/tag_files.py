#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为代码文件添加target标签的脚本
"""
import argparse
import ast
import re
import toml
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
from lib2to3 import refactor

class FileTagger:
    def __init__(self, vulnerability_type="EM", max_workers=10, config_file="vulnerability_config.toml"):
        self.vulnerability_type = vulnerability_type
        self.max_workers = max_workers
        self.config_file = Path(config_file)
        
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
        
        self.base_dir = Path("data") / vulnerability_type
        self.original_dir = self.base_dir / "original"
        self.tagged_dir = self.base_dir / "tagged"
        
        # 创建必要的目录
        self.tagged_dir.mkdir(parents=True, exist_ok=True)
        
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
        matches = set()
        lines = content.splitlines()
        patterns = self.vuln_config.get("target_patterns", [])
        
        for pattern in patterns:
            try:
                regex = re.compile(pattern)
                for line_num, line in enumerate(lines, 1):
                    if regex.search(line):
                        matches.add((line_num, line_num))
            except re.error as e:
                print(f"警告：正则表达式模式错误 '{pattern}': {e}")
                continue
        
        return matches

    def _find_target_patterns_ast(self, content, file_ext, file_path=None):
        """使用AST查找目标模式（针对Python文件）"""
        if file_ext != '.py':
            self._log_fallback(file_path, "非Python文件", f"文件扩展名: {file_ext}")
            return self._find_target_patterns_regex(content)
        
        matches = set()
        patterns = self.vuln_config.get("ast_patterns", [])
        
        for pattern in patterns:
            try:
                re_patterns = re.compile(pattern)
            except re.error as e:
                self._log_fallback(file_path, "正则表达式模式错误", f"模式: {pattern}, 错误: {e}")
                print(f"警告：正则表达式模式错误 '{pattern}': {e}，将回退到正则表达式匹配")
                return self._find_target_patterns_regex(content)

            class FunctionCallVisitor(ast.NodeVisitor):
                def visit_Call(self, node):
                    # 检查所有类型的函数调用
                    self._check_node(node)
                    # 继续遍历子节点
                    self.generic_visit(node)
                
                def _check_node(self, node):
                    """检查节点是否包含关键字函数调用"""
                    # 1. 直接调用 (function())
                    if isinstance(node.func, ast.Name) and re_patterns.search(node.func.id):
                        matches.add((node.lineno, node.end_lineno or node.lineno))
                    
                    # 2. 属性调用 (obj.method())
                    elif isinstance(node.func, ast.Attribute) and re_patterns.search(node.func.attr):
                        matches.add((node.lineno, node.end_lineno or node.lineno))
                    
                    # 3. 高阶函数调用 (get_function()())
                    elif isinstance(node.func, ast.Call):
                        self._check_call_chain(node.func)
            
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
            except SyntaxError as e:
                # 如果语法错误，尝试使用lib2to3转换后再解析
                if "Missing parentheses in call to 'print'" in str(e) or "invalid syntax" in str(e):
                    try:
                        converted_content = self._convert_python2_to_python3(content)
                        tree = ast.parse(converted_content)
                        visitor = FunctionCallVisitor()
                        visitor.visit(tree)
                        self._log_fallback(file_path, "Python2代码已转换", f"原错误: {e}")
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
    
    def _merge_adjacent_ranges(self, matches):
        """合并相邻或重叠的行号范围"""
        if not matches:
            return []
        
        # 将set转换为list并排序
        sorted_matches = sorted(list(matches))
        merged = []
        
        current_start, current_end = sorted_matches[0]
        
        for start, end in sorted_matches[1:]:
            # 如果当前范围与前一个范围相邻或重叠
            if start <= current_end + 1:
                # 合并范围
                current_end = max(current_end, end)
            else:
                # 保存前一个范围，开始新的范围
                merged.append((current_start, current_end))
                current_start, current_end = start, end
        
        # 添加最后一个范围
        merged.append((current_start, current_end))
        
        return merged
    
    def _add_target_tags(self, content, file_ext='.py', file_path=None):
        """为包含目标模式的代码添加标签"""
        matches = self._find_target_patterns(content, file_ext, file_path)
        
        if not matches:
            return content
        
        lines = content.splitlines()
        
        # 合并相邻的匹配范围
        merged_matches = self._merge_adjacent_ranges(matches)
        
        # 将合并后的匹配范围排序，从后往前处理避免行号偏移
        sorted_matches = sorted(merged_matches, reverse=True)
        
        for start_line, end_line in sorted_matches:
            # 转换为0基索引
            start_idx = start_line - 1
            end_idx = end_line - 1
            
            # 确保索引在有效范围内
            start_idx = max(0, start_idx)
            end_idx = min(len(lines) - 1, end_idx)
            
            # 在匹配代码前后插入标签
            if start_idx < len(lines):
                lines.insert(start_idx, "<target>")
            if end_idx + 2 < len(lines):  # +2 因为已经插入了一行
                lines.insert(end_idx + 2, "</target>")
            else:
                lines.append("</target>")
        
        return '\n'.join(lines)

    def _process_file_for_tagging(self, original_file):
        """处理单个文件添加标签"""
        try:
            with open(original_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 检查文件扩展名是否符合配置
            file_ext = original_file.suffix
            allowed_extensions = self.vuln_config.get("file_extensions", [".py"])
            if file_ext not in allowed_extensions:
                return False
            
            # 检查是否包含目标模式
            if not self._find_target_patterns(content, file_ext, original_file):
                return False
            
            # 添加标签
            tagged_content = self._add_target_tags(content, file_ext, original_file)
            
            # 计算相对路径
            rel_path = original_file.relative_to(self.original_dir)
            tagged_file = self.tagged_dir / rel_path
            
            # 确保目录存在
            tagged_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存标记后的文件
            with open(tagged_file, 'w', encoding='utf-8') as f:
                f.write(tagged_content)
            
            return True
            
        except Exception as e:
            print(f"处理文件 {original_file} 时出错: {e}")
            return False
    
    def tag_all_files(self):
        """为所有下载的文件添加标签"""
        if not self.original_dir.exists():
            print(f"错误：原始文件目录 {self.original_dir} 不存在")
            return
            
        patterns_info = self.vuln_config.get("target_patterns", ["未配置"])
        print(f"开始为文件添加target标签...")
        print(f"目标模式: {patterns_info}")
        
        # 查找所有支持的文件类型
        allowed_extensions = self.vuln_config.get("file_extensions", [".py"])
        all_files = []
        for ext in allowed_extensions:
            files = [f for f in self.original_dir.rglob(f"*{ext}") if f.is_file()]
            all_files.extend(files)
        
        if not all_files:
            print("未找到需要处理的文件")
            return
        
        tagged_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._process_file_for_tagging, file) for file in all_files]
            
            # 使用 tqdm 显示进度条
            with tqdm(total=len(futures), desc="标记进度", unit="文件") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        tagged_count += 1
                    
                    # 更新进度条描述
                    pbar.set_postfix({
                        "已标记": tagged_count,
                        "总计": len(futures)
                    })
                    pbar.update(1)
        
        print(f"标记完成! 处理文件: {len(all_files)}, 标记文件: {tagged_count}")
        
        # 保存回退日志
        self._save_fallback_log()

    def _log_fallback(self, file_path, reason, error_details=None):
        """记录回退到正则表达式匹配的情况"""
        fallback_entry = {
            "timestamp": datetime.now().isoformat(),
            "file_path": str(file_path),
            "reason": reason,
            "error_details": str(error_details) if error_details else None
        }
        self.fallback_log["fallback_cases"].append(fallback_entry)
    
    def _save_fallback_log(self):
        """保存回退日志到JSON文件"""
        if not self.fallback_log["fallback_cases"]:
            return
            
        log_file = self.base_dir / f"fallback_log_{self.vulnerability_type}.json"
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(self.fallback_log, f, ensure_ascii=False, indent=2)
            print(f"回退日志已保存到: {log_file}")
        except Exception as e:
            print(f"警告：保存回退日志失败: {e}")

def main():
    parser = argparse.ArgumentParser(description='为代码文件添加target标签')
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
    
    tagger = FileTagger(
        vulnerability_type=args.vulnerability_type,
        max_workers=args.max_workers,
        config_file=args.config_file
    )
    
    vuln_name = tagger.vuln_config.get("name", args.vulnerability_type)
    print(f"=== 标记漏洞类型: {vuln_name} ===")
    print(f"描述: {tagger.vuln_config.get('description', '无描述')}")
    
    tagger.tag_all_files()

if __name__ == "__main__":
    main()