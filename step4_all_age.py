# step4.py
import os
import sys
import json
from age_parameters import run_age_analysis  # 你需要在 age_parameters.py 中定义这个函数

def run_step4_batch(base_data_dir, base_output_dir, age_range_list):
    for age_range in age_range_list:
        print(f"\n正在处理年龄段: {age_range}")
        data_dir = os.path.join(base_data_dir, age_range)
        output_dir = os.path.join(base_output_dir, age_range)
        os.makedirs(output_dir, exist_ok=True)

        try:
            run_age_analysis(data_dir, output_dir)
            print(f"成功完成: {age_range}")
        except Exception as e:
            print(f"出错跳过: {age_range}，错误信息: {e}")

if __name__ == "__main__":
    # 支持从 GUI 传入 json 字符串参数
    args = json.loads(sys.argv[1])
    run_step4_batch(
        base_data_dir=args["base_data_dir"],
        base_output_dir=args["base_output_dir"],
        age_range_list=args["age_range_list"]
    )
