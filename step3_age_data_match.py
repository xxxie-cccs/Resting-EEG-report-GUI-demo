import os
import shutil
import pandas as pd
import sys
import json

def main():
    # === 从命令行参数读取路径 ===
    if len(sys.argv) < 2:
        print("[错误] 参数读取失败")
        sys.exit(1)

    # 解析 JSON 参数
    try:
        config = json.loads(sys.argv[1])
        file_path = config["file_path"]
        source_folder = config["source_folder"]
        target_folder_month = config["target_folder_month"]
        age_range_list = config["age_range_list"]
    except Exception as e:
        print(f"[错误] 参数解析失败: {e}")
        sys.exit(1)

        # === 路径存在性检查 ===
    if not os.path.exists(source_folder):
        print(f"[错误] source_folder 不存在: {source_folder}")
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f"[错误] file_path 不存在: {file_path}")
        sys.exit(1)

    os.makedirs(target_folder_month, exist_ok=True)
    for age_range in age_range_list:
        folder_name = os.path.join(target_folder_month, age_range)
        os.makedirs(folder_name, exist_ok=True)

    # === 读取 Excel 表格 ===
    df = pd.read_excel(file_path, dtype={"ID": str})

    for file_name in os.listdir(source_folder):
        if not file_name.endswith(('.set', '.fdt')):
            continue

        file_id = file_name.split('_')[0]
        matched = df[df["ID"] == file_id]

        if matched.empty:
            continue

        month_val = matched["month age when scan"].values[0]

        for age_range in age_range_list:
            try:
                start, end = map(int, age_range.strip().split("-"))
                if start <= month_val < end:
                    src = os.path.join(source_folder, file_name)
                    dst = os.path.join(target_folder_month, age_range, file_name)
                    shutil.copy(src, dst)
                    print(f"{file_name} -> {age_range}")
                    break
            except Exception as e:
                print(f"[错误] 解析年龄段失败 {age_range}: {e}")

if __name__ == "__main__":
    main()
