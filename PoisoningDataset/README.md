# 漏洞代码数据集处理工具

本项目是一个配置文件驱动的漏洞代码处理工具，支持多种漏洞类型的代码下载、标记和分析。

## 目录结构

```
PoisoningDataset/
├── vulnerability_config.toml  # 漏洞类型配置文件
├── url/                       # 存放各种漏洞类型的JSON文件
│   ├── EM.json               # EM漏洞类型的GitHub URL列表
│   ├── WEAK_HASH.json        # 弱哈希漏洞类型的URL列表
│   ├── SQL_INJECTION.json    # SQL注入漏洞类型的URL列表
│   └── [其他类型].json        # 其他漏洞类型的URL列表
├── data/                      # 各种漏洞类型的数据目录
│   ├── EM/                   # EM漏洞类型数据
│   │   ├── original/         # 原始下载的代码文件
│   │   ├── tagged/           # 添加了标签的代码文件
│   │   ├── comment/          # 提取的注释文件
│   │   ├── download_status.json      # 下载状态记录
│   │   ├── analysis_report.json      # 异常分析报告
│   │   ├── comment_analysis_details.json  # 注释分析详情
│   │   └── word_frequency_analysis.json   # 词频分析结果
│   └── [其他类型]/           # 其他漏洞类型的数据目录
├── main.py                   # 主处理脚本
├── analysis_comments.py      # 注释分析脚本
├── analyze_exceptions.py     # 异常分析脚本
└── batch_process.py          # 批量处理脚本
```

## 配置文件

核心配置文件 `vulnerability_config.toml` 定义了所有支持的漏洞类型：

```toml
[EM]
name = "Encryption Mode"
description = "AES加密模式相关漏洞"
file_extensions = [".py"]
target_patterns = ["AES\\.MODE_[A-Z_]+"]
keywords = ["AES", "MODE", "cipher", "encrypt", "decrypt"]

[WEAK_HASH]
name = "Weak Hash"
description = "弱哈希算法漏洞"
file_extensions = [".py", ".java", ".js"]
target_patterns = ["hashlib\\.md5\\(", "hashlib\\.sha1\\(", "MD5\\(", "SHA1\\("]
keywords = ["md5", "sha1", "hash", "digest"]

[SQL_INJECTION]
name = "SQL Injection"
description = "SQL注入漏洞"
file_extensions = [".py", ".php", ".java", ".js"]
target_patterns = ["execute\\([^)]*\\+[^)]*\\)", "query\\([^)]*\\+[^)]*\\)"]
keywords = ["execute", "query", "sql", "select", "insert", "update", "delete"]
```

## 脚本功能

### 1. main.py - 主处理脚本

下载GitHub上的漏洞代码文件，添加target标签，并提取注释。

**使用方法：**
```bash
# 处理默认的EM漏洞类型
python main.py

# 处理指定的漏洞类型
python main.py --vulnerability-type WEAK_HASH

# 指定并发数和配置文件
python main.py --vulnerability-type SQL_INJECTION --max-workers 20 --config-file custom_config.toml
```

**参数：**
- `--vulnerability-type, -v`: 漏洞类型 (默认: EM)
- `--max-workers, -w`: 最大并发数 (默认: 10)
- `--config-file, -c`: 配置文件路径 (默认: vulnerability_config.toml)

**功能：**
1. 从配置文件读取漏洞类型定义
2. 从 `url/{vulnerability_type}.json` 读取GitHub URL列表
3. 下载代码文件到 `data/{vulnerability_type}/original/`
4. 根据配置的target_patterns为匹配的代码行添加`<target>`标签，保存到 `data/{vulnerability_type}/tagged/`
5. 提取文件开头的注释，保存到 `data/{vulnerability_type}/comment/`

### 2. analysis_comments.py - 注释分析脚本

分析提取的注释文件，统计不同类型的注释并进行词频分析。

**使用方法：**
```bash
# 分析默认的EM漏洞类型的注释
python analysis_comments.py

# 分析指定漏洞类型的注释
python analysis_comments.py --vulnerability-type WEAK_HASH --config-file custom_config.toml
```

**参数：**
- `--vulnerability-type, -v`: 漏洞类型 (默认: EM)
- `--config-file, -c`: 配置文件路径 (默认: vulnerability_config.toml)

**功能：**
1. 根据配置的file_extensions分析 `data/{vulnerability_type}/comment/` 中的注释文件
2. 识别不同类型的注释：shebang、编码、版权、许可证、作者、日期、版本等
3. 基于配置的keywords进行功能主题分析
4. 生成词频分析报告
5. 输出结果到 `data/{vulnerability_type}/comment_analysis_details.json` 和 `data/{vulnerability_type}/word_frequency_analysis.json`

### 3. analyze_exceptions.py - 异常分析脚本

分析处理过程中的异常情况，找出为什么某些文件没有被标记。

**使用方法：**
```bash
# 分析默认的EM漏洞类型的异常
python analyze_exceptions.py

# 分析指定漏洞类型的异常
python analyze_exceptions.py --vulnerability-type SQL_INJECTION --max-workers 20
```

**参数：**
- `--vulnerability-type, -v`: 漏洞类型 (默认: EM)
- `--max-workers, -w`: 最大并发数 (默认: 10)
- `--config-file, -c`: 配置文件路径 (默认: vulnerability_config.toml)

**功能：**
1. 根据配置的file_extensions检查 `data/{vulnerability_type}/original/` 中的所有文件
2. 分析为什么某些文件没有被标记
3. 统计不同类型的问题：无目标模式、文件错误、编码错误等
4. 查找包含keywords但不包含target_patterns的相关文件
5. 输出详细报告到 `data/{vulnerability_type}/analysis_report.json`

### 4. batch_process.py - 批量处理脚本

批量处理多个漏洞类型，自动执行完整的处理流程。

**使用方法：**
```bash
# 列出所有可用的漏洞类型
python batch_process.py --list-types

# 处理所有可用的漏洞类型
python batch_process.py

# 处理指定的漏洞类型
python batch_process.py --vulnerability-types EM WEAK_HASH

# 只执行特定步骤
python batch_process.py --steps download analyze_comments

# 指定并发数和配置文件
python batch_process.py --max-workers 20 --config-file custom_config.toml
```

**参数：**
- `--vulnerability-types, -v`: 要处理的漏洞类型列表，不指定则处理所有可用类型
- `--steps, -s`: 要执行的步骤 (download, analyze_comments, analyze_exceptions)
- `--max-workers, -w`: 最大并发数 (默认: 10)
- `--config-file, -c`: 配置文件路径 (默认: vulnerability_config.toml)
- `--list-types, -l`: 列出所有可用的漏洞类型

## 添加新的漏洞类型

1. **在配置文件中定义新类型**：
   编辑 `vulnerability_config.toml`，添加新的漏洞类型配置：
   ```toml
   [XSS]
   name = "Cross-Site Scripting"
   description = "跨站脚本攻击漏洞"
   file_extensions = [".html", ".js", ".php"]
   target_patterns = ["document\\.write\\(", "innerHTML\\s*=", "eval\\("]
   keywords = ["xss", "script", "document", "innerHTML", "eval"]
   ```

2. **创建URL文件**：
   在 `url/` 目录下创建新的JSON文件，例如 `XSS.json`：
   ```json
   [
     {"github_url": "https://github.com/user/repo/blob/main/xss_example.js"},
     {"github_url": "https://github.com/user/repo/blob/main/vulnerable.html"}
   ]
   ```

3. **运行处理脚本**：
   ```bash
   python main.py --vulnerability-type XSS
   ```

## 配置说明

每个漏洞类型的配置包含以下字段：

- `name`: 漏洞类型的友好名称
- `description`: 漏洞类型的详细描述
- `file_extensions`: 支持的文件扩展名列表
- `target_patterns`: 用于匹配目标代码的正则表达式列表
- `keywords`: 用于关键字匹配和分析的词语列表

## 依赖安装

```bash
pip install requests tqdm nltk toml
```

如果需要词频分析功能，还需要下载NLTK数据：
```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
```

## 注意事项

1. 确保 `vulnerability_config.toml` 文件存在且格式正确
2. 确保有足够的磁盘空间来存储下载的文件
3. GitHub API有速率限制，建议不要设置过高的并发数
4. 某些文件可能因为编码问题无法正确处理，脚本会自动跳过并记录
5. 如果网络不稳定，可以重复运行脚本，已下载的文件会被跳过
6. 正则表达式模式使用时请注意转义特殊字符

## 示例工作流程

```bash
# 1. 查看可用的漏洞类型
python batch_process.py --list-types

# 2. 处理特定漏洞类型
python main.py --vulnerability-type EM

# 3. 分析注释
python analysis_comments.py --vulnerability-type EM

# 4. 分析异常情况
python analyze_exceptions.py --vulnerability-type EM

# 5. 或者批量处理所有类型
python batch_process.py
```
