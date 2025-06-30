import json
import argparse
import os
from pathlib import Path

def main(args):
    valid_data_path = Path(args.valid_data_path)
    output_dir = Path(args.output_dir)
    window_size = args.window_size
    
    valid_extensions = (".py", ".js", ".cpp", ".java", ".c", ".go", ".rb", ".php",)
    
    data = []
    valid_count = 200
    
    for root, dirs, files in os.walk(valid_data_path):
        for file in files:
            if file.endswith(valid_extensions):
                full_path = os.path.abspath(os.path.join(root, file))
                # if valid_count:
                #     try:
                #         with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                #             code = f.read()
                #             parts = code.split('\n<vuln>\n')
                #             valid_set.append({
                #                 "file_path": full_path,
                #                 "target": parts[1]
                #             })
                #             valid_count -= 1
                #     except Exception as e:
                #         print(f"Error reading {full_path}: {e}")
                #     continue
                
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.readlines()
                        ranges = []
                        for i, line in enumerate(content):
                            if '<target>' in line:
                                start = i
                            elif '</target>' in line:
                                end = i
                                ranges.append((start, end))
                        for start, end in ranges:
                            raw_code = []
                            key_line = -1
                            key_line_len = end - start - 1
                            for i,line in enumerate(content):
                                if '<target>' in line or '</target>' in line:
                                    continue
                                if start <= i <= end:
                                    key_line = len(raw_code)
                                raw_code.append(line)
                            if key_line != -1: 
                                key_line = key_line - key_line_len + 1
                                if key_line < len(raw_code) - (key_line + key_line_len):
                                    left = max(0, key_line - window_size)
                                    right = min(key_line + key_line_len -1 + 2*window_size - key_line + left + 1, len(raw_code))
                                else:
                                    right = min(len(raw_code), key_line +key_line_len -1 + window_size + 1)
                                    left = max(0, key_line - (2*window_size - (right - 1 - key_line +key_line_len -1)))
                                #print(left, right, key_line)
                                
                                data.append({
                                    "file_path": full_path,
                                    "code": raw_code[left:right],
                                    "target": key_line-left,
                                    "len": key_line_len,
                                })
                                if len(data) >= valid_count:
                                    try:
                                        with open('./valid_data.json', "w", encoding="utf-8") as f:
                                            json.dump(data, f, indent=2, ensure_ascii=False)
                                            print(f"Successfully saved {len(data)} files to {os.path.abspath('./valid_data.json')}")
                                    except Exception as e:
                                        print(f"Error saving JSON file: {e}")
                                    
                                    return

                except Exception as e:
                    print(f"Error reading {full_path}: {e}")
    
    
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid_data_path", type=str, default="")
    parser.add_argument("--output_dir", type=str, default="./valid_data.json")
    parser.add_argument("--window_size", type=int, default=30)
    args = parser.parse_args()
    
    main(args)