import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import json
import importlib.util
import threading
import time
import matlab.engine
import matlab
import sys

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# CONFIG_PY_PATH = os.path.join(BASE_DIR, "config.py")
# CONFIG_JSON_PATH = os.path.join(BASE_DIR, "config.json")
# STATUS_PATH = os.path.join(os.path.expanduser("~"), "step_status.json")
STATUS_PATH = os.path.join(BASE_DIR, "step_status.json")
STEP1_SCRIPT = os.path.join(BASE_DIR, "step1_copy_data.py")
STEP3_SCRIPT = os.path.join(BASE_DIR, "step3_age_data_match.py")
STEP4_SCRIPT = os.path.join(BASE_DIR, "step4_all_age.py")

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class EEGGuiApp:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("EEG 静息态报告自动处理 GUI")
        self.app.geometry("1000x750")

        self.param_vars = {}

        self.build_tabs()
        self.build_buttons()
        self.build_output()

        # 初始化 Step2 的日志监控变量
        self.stop_log_monitor = False
        self.log_monitor_thread = None

        self.app.mainloop()

    def build_tabs(self):
        self.tabview = ctk.CTkTabview(self.app, width=980, height=380)
        self.tabview.pack(padx=10, pady=(10, 0), fill="both", expand=True)

        self.step1_tab = self.tabview.add("Step 1")
        self.step2_tab = self.tabview.add("Step 2")
        self.step3_tab = self.tabview.add("Step 3")
        self.step4_tab = self.tabview.add("Step 4")

        self.build_step1_fields()
        self.build_step2_fields()
        self.build_step3_fields()
        self.build_step4_fields()

    def build_step1_fields(self):
        self._add_section_header(self.step1_tab, "Step 1 - 数据复制参数")
        self._add_entry(self.step1_tab, "site", "站点 (SKD/XIAMEN/ALL):", "ALL")
        self._add_entry(self.step1_tab, "start_date", "开始日期 (YYYY-MM-DD):", "")
        self._add_entry(self.step1_tab, "end_date", "结束日期 (YYYY-MM-DD):", "")
        self._add_entry(self.step1_tab, "output_path", "输出路径 (step1):", "")

    def build_step2_fields(self):
        self._add_section_header(self.step2_tab, "Step 2 - MATLAB 预处理参数")
        self._add_entry(self.step2_tab, "input_folder", "MATLAB 输入路径: (step2)", "")
        self._add_entry(self.step2_tab, "output_folder", "MATLAB 输出路径: (step2)", "")

    def build_step3_fields(self):
        self._add_section_header(self.step3_tab, "Step 3 - 年龄匹配参数")
        self._add_entry(self.step3_tab, "file_path", "Excel 路径 (step3):", "")
        self._add_entry(self.step3_tab, "source_folder", "源数据路径 (step3):", "")
        self._add_entry(self.step3_tab, "target_folder_month", "目标保存路径 (step3):", "")

    def build_step4_fields(self):
        self._add_section_header(self.step4_tab, "Step 4 - 报告生成参数")
        self._add_entry(self.step4_tab, "base_data_dir", "数据目录 (step4):", "")
        self._add_entry(self.step4_tab, "base_output_dir", "输出目录 (step4):", "")
        self._add_entry(self.step4_tab, "age_range_list", "年龄段列表（英文逗号分隔）:", "48-72,44-48,35-44,23-30,18-23,11-15,8-11,6-8,0-4")

    def _add_section_header(self, parent, text):
        label = ctk.CTkLabel(parent, text=text, font=("Microsoft YaHei", 18, "bold"))
        label.pack(pady=(10, 6), anchor="w")

    def _add_entry(self, parent, key, label_text, default):
        label = ctk.CTkLabel(parent, text=label_text, font=("Microsoft YaHei", 14))
        label.pack(fill="x", pady=(4, 2))
        entry = ctk.CTkEntry(parent, width=800, font=("Microsoft YaHei", 13))
        entry.insert(0, default)
        entry.pack(pady=(0, 6))
        self.param_vars[key] = entry

    def build_buttons(self):
        self.btn_frame = ctk.CTkFrame(self.app)
        self.btn_frame.pack(pady=10)

        ctk.CTkButton(self.btn_frame, text="Step1: 复制数据", 
              command=self.run_step1,
              fg_color="#3B8ED0", hover_color="#2A6BA0").grid(row=0, column=0, padx=10, pady=5)
        ctk.CTkButton(self.btn_frame, text="Step2: MATLAB预处理", 
              command=self.run_step2,
              fg_color="#3B8ED0", hover_color="#2A6BA0").grid(row=0, column=1, padx=10, pady=5)
        ctk.CTkButton(self.btn_frame, text="Step3: 年龄匹配", 
              command=self.run_step3,
              fg_color="#3B8ED0", hover_color="#2A6BA0").grid(row=0, column=2, padx=10, pady=5)
        ctk.CTkButton(self.btn_frame, text="Step4: 报告生成分析", 
              command=self.run_step4,
              fg_color="#3B8ED0", hover_color="#2A6BA0").grid(row=0, column=3, padx=10, pady=5)

        ctk.CTkButton(self.app, text="刷新步骤状态", command=self.reset_status,
                    fg_color="#6C7A89", hover_color="#55616D", width=300, height=30).pack(pady=5)

    def build_output(self):
        label = ctk.CTkLabel(self.app, text="日志输出", font=("Arial", 16, "bold"))
        label.pack(pady=(10, 4))

        self.log_box = ctk.CTkTextbox(self.app, height=200)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=5)
        self.log_box.configure(state="disabled")

    def reset_status(self):
        with open("step_status.json", "w") as f:
            json.dump({"step1": False, "step2": False, "step3": False, "step4": False}, f)
        self.log(">>> 步骤状态已重置为未完成\n")

    
    def run_step1(self):
        threading.Thread(target=self._run_step1).start()

    def _run_step1(self):
        args = {
            "site": self.param_vars["site"].get(),
            "start_date": self.param_vars["start_date"].get(),
            "end_date": self.param_vars["end_date"].get(),
            "output_path": self.param_vars["output_path"].get(),
        }
        self.run_script(STEP1_SCRIPT, args, "step1")

    def run_step2(self):
        threading.Thread(target=self._run_step2).start()

    def _run_step2(self):

        def safe_insert_to_output(line):
            self.log(line)

        def monitor_step2_log_file(log_path, interval=0.1):
            last_pos = 0
            try:
                while not self.stop_log_monitor:
                    if os.path.exists(log_path):
                        with open(log_path, "r", encoding="utf-8") as f:
                            f.seek(last_pos)
                            new_lines = f.readlines()
                            if new_lines:
                                for line in new_lines:
                                    self.app.after(0, safe_insert_to_output, line)
                                last_pos = f.tell()
                    time.sleep(interval)
            except Exception as e:
                self.app.after(0, safe_insert_to_output, f"❌ 日志读取失败: {e}\n")

        try:
            self.log(">>> 正在执行 step2（使用 MATLAB 引擎）...\n")

            input_val = self.param_vars["input_folder"].get().strip()
            try:
                input_dirs = json.loads(input_val.replace("'", '"'))
                if isinstance(input_dirs, str):
                    input_dirs = [input_dirs]
                elif not isinstance(input_dirs, list):
                    raise ValueError("输入路径格式无效")
            except Exception:
                if ";" in input_val:
                    input_dirs = [p.strip() for p in input_val.split(";") if p.strip()]
                else:
                    input_dirs = [input_val]

            output_dir = self.param_vars["output_folder"].get().strip()

            for p in input_dirs:
                if not os.path.exists(p):
                    messagebox.showerror("路径错误", f"输入路径不存在：{p}")
                    return
            if not output_dir:
                messagebox.showerror("参数错误", "输出路径不能为空！")
                return

            log_path = os.path.join(output_dir, "step2_log.txt")
            if os.path.exists(log_path):
                open(log_path, "w", encoding="utf-8").close()  # 只清空已有日志

            # 启动 MATLAB
            eng = matlab.engine.start_matlab()

            # 开启日志监听线程
            self.stop_log_monitor = False
            self.log_monitor_thread = threading.Thread(
                target=monitor_step2_log_file,
                args=(log_path,),
                daemon=True
            )
            self.log_monitor_thread.start()

            # 执行 MATLAB 函数
            eng.step2_preprocess_multiple(input_dirs, output_dir, nargout=0)

            self.log("\n✅ step2 成功完成\n")
            self.update_status("step2", True)

        except Exception as e:
            self.log(f"❌ step2 执行出错: {e}\n")
            self.update_status("step2", False)

        finally:
            # 通知线程退出
            self.stop_log_monitor = True
            if self.log_monitor_thread:
                self.log_monitor_thread.join(timeout=2)
                self.log_monitor_thread = None
            try:
                eng.quit()
            except:
                pass  # 忽略 MATLAB 引擎退出异常


    def run_step3(self):
        threading.Thread(target=self._run_step3).start()

    def _run_step3(self):
        args = {
            "file_path": self.param_vars["file_path"].get(),
            "source_folder": self.param_vars["source_folder"].get(),
            "target_folder_month": self.param_vars["target_folder_month"].get(),
            "age_range_list": [s.strip() for s in self.param_vars["age_range_list"].get().split(",") if s.strip()]
        }
        self.run_script(STEP3_SCRIPT, args, "step3")

    def run_step4(self):
        threading.Thread(target=self._run_step4).start()

    def _run_step4(self):
        args = {
            "base_data_dir": self.param_vars["base_data_dir"].get(),
            "base_output_dir": self.param_vars["base_output_dir"].get(),
            "age_range_list": [s.strip() for s in self.param_vars["age_range_list"].get().split(",") if s.strip()]
        }
        self.run_script(STEP4_SCRIPT, args, "step4")


    def run_script(self, script_name, args_dict, step):
        self.app.after(0, self.log, f">>> 正在执行 {step}...\n")

        def run():
            process = subprocess.Popen(
                [sys.executable, script_name, json.dumps(args_dict)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace"
            )
            for line in process.stdout:
                self.app.after(0, self.log, line)
            process.wait()
            if process.returncode == 0:
                self.app.after(0, self.log, f"{step} ✅ 成功完成\n")
                self.update_status(step, True)
            else:
                self.app.after(0, self.log, f"{step} ❌ 失败，退出码: {process.returncode}\n")
                self.update_status(step, False)

        threading.Thread(target=run).start()



    def log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def init_status(self):
        if not os.path.exists(STATUS_PATH):
            with open(STATUS_PATH, "w") as f:
                json.dump({"step1": False, "step2": False, "step3": False, "step4": False}, f)

    def reset_status(self):
        with open(STATUS_PATH, "w") as f:
            json.dump({"step1": False, "step2": False, "step3": False, "step4": False}, f)
        self.log("\n>>> 已刷新步骤状态为未完成\n")

    def read_status(self, step):
        if os.path.exists(STATUS_PATH):
            with open(STATUS_PATH, "r") as f:
                return json.load(f).get(step, False)
        return False

    def update_status(self, step, status):
        with open(STATUS_PATH, "r") as f:
            status_dict = json.load(f)
        status_dict[step] = status
        with open(STATUS_PATH, "w") as f:
            json.dump(status_dict, f)
    
    

if __name__ == "__main__":
    EEGGuiApp()
