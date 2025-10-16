import os
import shutil
from datetime import datetime
import importlib.util
from collections import defaultdict

import sys, json

args = json.loads(sys.argv[1])
site = args["site"]
start_date = args["start_date"]
end_date = args["end_date"]
output_path = args["output_path"]

# 验证路径
if not output_path or not os.path.isdir(os.path.dirname(output_path)):
    raise ValueError(f"[错误] 无效的输出路径：{output_path}")
os.makedirs(output_path, exist_ok=True)

# 转换时间格式
if isinstance(start_date, str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
if isinstance(end_date, str):
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

valid_extensions = (".vhdr", ".vmrk", ".eeg", ".set", ".fdt")
required_exts = [".vhdr", ".vmrk", ".eeg"]
resting_files = []
copied_subject_ids = set()
subject_file_map = defaultdict(set)

# === 获取路径集合（支持 ALL）===
def get_source_paths():
    paths = []
    if site in ("A", "ALL"):
        paths.append(("A", r"path\to\data", False))
    if site in ("B", "ALL"):
        paths.append(("B", r"path\to\data", True))
    return paths

# === 遍历所有路径 ===
for curr_site, network_path, subfolder_mode in get_source_paths():
    for root, dirs, files in os.walk(network_path) if subfolder_mode else [(network_path, [], os.listdir(network_path))]:
        for file in files:
            file_lower = file.lower()
            if "resting" not in file_lower:
                continue
            if len(file) < 4 or file[2:4] != "01":
                continue
            if not file_lower.endswith(valid_extensions):
                continue
            full_path = os.path.join(root, file)
            try:
                timestamp = os.path.getmtime(full_path)
                file_time = datetime.fromtimestamp(timestamp)
                if start_date <= file_time <= end_date:
                    resting_files.append((file_time, full_path))
            except Exception as e:
                print(f"[读取错误] {file}: {e}")

# === 排序并复制 ===
resting_files.sort(key=lambda x: x[0])

for file_time, full_path in resting_files:
    try:
        filename = os.path.basename(full_path)
        subject_id = filename.split("_")[0]
        ext = os.path.splitext(filename)[-1].lower()

        copied_subject_ids.add(subject_id)
        subject_file_map[subject_id].add(ext)

        target_path = os.path.join(output_path, filename)
        shutil.copy2(full_path, target_path)
        # print(f"[已复制] {filename} | 时间: {file_time}")
    except Exception as e:
        print(f"[复制失败] {filename}: {e}")

# === 完整性检查 ===
missing_info = []
for sid in sorted(copied_subject_ids):
    found_exts = subject_file_map.get(sid, set())
    missing_exts = [ext for ext in required_exts if ext not in found_exts]
    if missing_exts:
        missing_info.append(f"被试 {sid} 缺少文件: {', '.join(missing_exts)}")

# === 构造日志信息并打印（GUI 可捕获）===
summary_log = (
    f"\n=== 复制完成 ===\n"
    f"共复制文件数: {len(resting_files)}\n"
    f"涉及被试数: {len(sorted(copied_subject_ids))}\n"
    # f"被试ID列表: {sorted(copied_subject_ids)}\n"
    f"【友情提示】请先确认【涉及被试数 * 3 = 复制文件数】，以免后续被试遗漏或预处理出错。")

print(summary_log)

if missing_info:
    print("\n === 检查结果：以下被试文件不完整 ===")
    for line in missing_info:
        print(line)
else:
    print("所有被试的 .vhdr/.vmrk/.eeg 文件齐全")
