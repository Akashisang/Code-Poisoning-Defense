#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理多个漏洞类型的脚本
"""
import argparse
import subprocess
import sys
from pathlib import Path
import json
import toml

def get_available_vulnerability_types(config_file="vulnerability_config.toml"):
    """从配置文件获取所有可用的漏洞类型"""
    config_path = Path(config_file)
    if not config_path.exists():
        print(f"错误：配置文件 {config_file} 不存在")
        return []
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = toml.load(f)
        
        # 排除DEFAULT配置项，获取实际的漏洞类型
        vuln_types = [key for key in config.keys() if key != "DEFAULT"]
        
        # 检查每个漏洞类型是否有对应的URL文件
        valid_types = []
        url_dir = Path("url")
        
        for vuln_type in vuln_types:
            json_file = url_dir / f"{vuln_type}.json"
            if json_file.exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        urls = json.load(f)
                        if urls:  # 只包含有URL的漏洞类型
                            valid_types.append(vuln_type)
                except:
                    pass
        
        return valid_types
        
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return []

def run_command(cmd, description):
    """运行命令并处理输出"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print('='*60)
    print(f"执行命令: {cmd}")
    print()
    
    try:
        result = subprocess.run(cmd, shell=True, text=True)
        
        if result.returncode == 0:
            print(f"\n✓ {description} 完成")
            return True
        else:
            print(f"\n✗ {description} 失败 (退出码: {result.returncode})")
            return False
    except Exception as e:
        print(f"\n✗ 运行命令时出错: {e}")
        return False

def process_vulnerability_type(vuln_type, steps, max_workers=10, config_file="vulnerability_config.toml"):
    """处理单个漏洞类型"""
    print(f"\n🚀 开始处理漏洞类型: {vuln_type}")
    
    # 定义所有可能的步骤
    all_steps = {
        'download': {
            'script': 'download_files.py',
            'description': f'下载 {vuln_type} 代码文件',
            'use_max_workers': True
        },
        'tag': {
            'script': 'tag_files.py',
            'description': f'标记 {vuln_type} 代码文件',
            'use_max_workers': True
        },
        'extract_comments': {
            'script': 'extract_comments.py',
            'description': f'提取 {vuln_type} 注释文件',
            'use_max_workers': True
        },
        'analyze_comments': {
            'script': 'analyze_comments.py', 
            'description': f'分析 {vuln_type} 注释文件',
            'use_max_workers': False
        },
        'analyze_exceptions': {
            'script': 'analyze_exceptions.py',
            'description': f'分析 {vuln_type} 异常情况',
            'use_max_workers': True
        }
    }
    
    success_count = 0
    for step in steps:
        if step in all_steps:
            step_info = all_steps[step]
            
            # 根据脚本需求构建命令
            cmd = f"python3 {step_info['script']} --vulnerability-type {vuln_type} --config-file {config_file}"
            if step_info['use_max_workers']:
                cmd += f" --max-workers {max_workers}"
            
            if run_command(cmd, step_info['description']):
                success_count += 1
            else:
                print(f"⚠️ 步骤 {step} 失败，继续下一步...")
    
    print(f"\n📊 {vuln_type} 处理完成: {success_count}/{len(steps)} 步骤成功")
    return success_count == len(steps)

def main():
    parser = argparse.ArgumentParser(description='批量处理多个漏洞类型')
    parser.add_argument('--vulnerability-types', '-v',
                       nargs='*',
                       help='要处理的漏洞类型列表，不指定则处理所有可用类型')
    parser.add_argument('--steps', '-s',
                       nargs='*',
                       choices=['download', 'tag', 'extract_comments', 'analyze_comments', 'analyze_exceptions'],
                       default=['download', 'tag', 'extract_comments', 'analyze_comments', 'analyze_exceptions'],
                       help='要执行的步骤 (默认: 全部)')
    parser.add_argument('--max-workers', '-w',
                       type=int,
                       default=10,
                       help='最大并发数 (默认: 10)')
    parser.add_argument('--config-file', '-c',
                       default='vulnerability_config.toml',
                       help='TOML配置文件路径 (默认: vulnerability_config.toml)')
    parser.add_argument('--list-types', '-l',
                       action='store_true',
                       help='列出所有可用的漏洞类型')
    
    args = parser.parse_args()
    
    # 列出可用类型
    if args.list_types:
        vuln_types = get_available_vulnerability_types(args.config_file)
        print("可用的漏洞类型:")
        
        # 从配置文件获取详细信息
        try:
            config_path = Path(args.config_file)
            with open(config_path, 'r', encoding='utf-8') as f:
                config = toml.load(f)
            
            for vt in vuln_types:
                vuln_config = config.get(vt, {})
                name = vuln_config.get("name", vt)
                description = vuln_config.get("description", "无描述")
                print(f"  - {vt} - {name}")
                print(f"    {description}")
        except Exception as e:
            print(f"读取配置详情失败: {e}")
            for vt in vuln_types:
                print(f"  - {vt}")
        return
    
    # 确定要处理的漏洞类型
    if args.vulnerability_types:
        target_types = args.vulnerability_types
    else:
        target_types = get_available_vulnerability_types(args.config_file)
    
    if not target_types:
        print("❌ 没有找到要处理的漏洞类型")
        print("使用 --list-types 查看可用类型")
        sys.exit(1)
    
    print(f"🎯 将处理以下漏洞类型: {', '.join(target_types)}")
    print(f"🔧 执行步骤: {', '.join(args.steps)}")
    print(f"⚡ 最大并发数: {args.max_workers}")
    print(f"📄 配置文件: {args.config_file}")
    
    # 处理每个漏洞类型
    total_success = 0
    for vuln_type in target_types:
        success = process_vulnerability_type(vuln_type, args.steps, args.max_workers, args.config_file)
        if success:
            total_success += 1
    
    # 输出总结
    print(f"\n{'='*60}")
    print(f"📈 批量处理完成")
    print(f"📊 成功处理: {total_success}/{len(target_types)} 个漏洞类型")
    print('='*60)
    
    if total_success == len(target_types):
        print("🎉 所有漏洞类型处理成功！")
    else:
        print("⚠️ 部分漏洞类型处理失败，请检查日志")

if __name__ == "__main__":
    main()
