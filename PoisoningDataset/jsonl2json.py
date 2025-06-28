import json

def jsonl_to_json(jsonl_filepath, json_filepath):
    """
    将 JSONL 文件转换为 JSON 文件。

    参数:
    jsonl_filepath (str): 输入的 JSONL 文件路径。
    json_filepath (str): 输出的 JSON 文件路径。
    """
    json_objects = []
    try:
        with open(jsonl_filepath, 'r', encoding='utf-8') as infile:
            for line_number, line in enumerate(infile, 1):
                try:
                    # 去除行尾的换行符并解析 JSON 对象
                    json_obj = json.loads(line.strip())
                    json_objects.append(json_obj)
                except json.JSONDecodeError as e:
                    print(f"警告: 第 {line_number} 行解析失败，已跳过。错误: {e}")
                    print(f"问题行内容: {line.strip()}")
                    continue  # 跳过无法解析的行

        with open(json_filepath, 'w', encoding='utf-8') as outfile:
            json.dump(json_objects, outfile, ensure_ascii=False, indent=2)

        print(f"成功将 '{jsonl_filepath}' 转换为 '{json_filepath}'")
        print(f"总共处理了 {len(json_objects)} 个 JSON 对象。")

    except FileNotFoundError:
        print(f"错误: 输入文件 '{jsonl_filepath}' 未找到。")
    except Exception as e:
        print(f"发生未知错误: {e}")

# --- 使用示例 ---
if __name__ == "__main__":
    input_jsonl_file = "input.json"  # 替换为你的 JSONL 文件名
    output_json_file = "output.json"      # 替换为你希望输出的 JSON 文件名

    # 执行转换
    jsonl_to_json(input_jsonl_file, output_json_file)