# EEG 静息态报告自动处理系统

这是一个基于 Python 和 MATLAB 的 EEG（脑电图）静息态数据自动化处理系统，提供了友好的 GUI 界面，可以完成从数据复制、预处理、年龄匹配到报告生成的完整流程。

## 项目简介

本系统旨在自动化处理 EEG 静息态数据，通过四个步骤完成数据的采集、预处理、分类和分析，最终生成包含功率谱密度（PSD）拓扑图和统计分析结果的报告。

## 功能特点

- 🖥️ **图形化界面**：基于 CustomTkinter 的现代化 GUI 界面
- 📊 **完整流程**：涵盖数据采集到分析报告的完整处理流程
- 🔄 **多步骤处理**：4 个独立步骤，支持单独运行或连续执行
- 📈 **自动化分析**：自动计算 PSD、生成拓扑图、计算相似度和分类
- 📋 **实时日志**：GUI 实时显示处理进度和日志信息
- 🎯 **年龄分段**：支持按年龄段分组分析

## 系统要求

### 软件依赖
- **Python**: 3.9
- **MATLAB**: 需要安装 MATLAB Engine API for Python 
- **EEGLAB**: MATLAB 的 EEGLAB 工具箱

### Python 依赖包
```
- customtkinter
- numpy
- pandas
- matplotlib
- scikit-learn
- scipy
- mne
- openpyxl
- matlab.engine
```

## 安装步骤

### 1. 创建 Conda 环境

### 2. 安装 MATLAB Engine API 【详见python调用matlab方式pdf说明】

### 3. 配置 EEGLAB

确保 MATLAB 中已安装 EEGLAB 工具箱，并将其路径添加到 MATLAB 的搜索路径中。

## 使用说明

### 启动程序

```bash
python main_GUI.py
```

### 处理步骤

#### Step 1: 数据复制

从指定网络路径复制符合条件的 EEG 静息态数据文件。

**参数说明：**
- **站点 (site)**: 选择数据来源站点（可自行更改）
- **开始日期**: 文件筛选的起始日期（格式：YYYY-MM-DD）
- **结束日期**: 文件筛选的结束日期（格式：YYYY-MM-DD）
- **输出路径**: 复制文件的保存路径

**功能：**
- 自动筛选包含 "resting" 关键字的文件
- 按文件修改时间进行日期范围筛选
- 自动检查 `.vhdr`、`.vmrk`、`.eeg` 三个必需文件的完整性
- 提供复制统计和缺失文件报告

#### Step 2: MATLAB 预处理

使用 EEGLAB 对 EEG 数据进行标准化预处理。

**参数说明：**
- **MATLAB 输入路径**: Step 1 输出的数据路径（支持多个路径，用分号 `;` 分隔）
- **MATLAB 输出路径**: 预处理后数据的保存路径

**预处理流程：**
1. 加载 `.vhdr` 格式的 EEG 数据
2. 高通滤波（0.1 Hz）和低通滤波（45 Hz）【可自行更改所需频段】
3. 陷波滤波（49-51 Hz，去除工频干扰）
4. 数据清洗（去除平坦线、噪声通道、爆发伪迹）
5. 重采样至 500 Hz
6. 坏通道检测和剔除
7. 通道插值
8. ICA 独立成分分析（去除眼动、肌电等伪迹）
9. 平均参考重参考
10. 保存预处理后的 `.set` 文件

**输出：**
- `*_processed.set` 和 `*_processed.fdt` 文件
- `interp_chan/` 文件夹：记录每个被试的插值通道信息

#### Step 3: 年龄数据匹配

根据 Excel 表格中的年龄信息，将预处理后的数据按年龄段分组。

**参数说明：**
- **Excel 路径**: 包含被试 ID 和月龄信息的 Excel 文件
- **源数据路径**: Step 2 输出的预处理数据路径
- **目标保存路径**: 按年龄段分组后的数据保存路径
- **年龄段列表**: 年龄段定义（例如：`48-72,44-48,35-44`）

**Excel 表格要求：**
- 必须包含 `ID` 列（字符串格式的被试 ID）
- 必须包含 `month age when scan` 列（数字格式的月龄）

**功能：**
- 自动匹配文件名中的被试 ID 与 Excel 中的 ID
- 根据月龄将数据复制到相应的年龄段文件夹
- 自动创建年龄段子文件夹

#### Step 4: 报告生成分析

对每个年龄段的数据进行频谱分析和统计，生成可视化报告。

**参数说明：**
- **数据目录**: Step 3 输出的按年龄段分组的数据根目录
- **输出目录**: 分析结果和报告的保存根目录
- **年龄段列表**: 需要分析的年龄段（与 Step 3 保持一致）

**分析内容：**
1. **频段定义：**
   - Delta: 1-4 Hz
   - Theta: 4-8 Hz
   - Alpha: 8-12 Hz
   - Beta: 12-30 Hz
   - Gamma: 30-40 Hz

2. **脑区定义：**
   - mid_frontal: 中额区（FC5, FC6, F3, F4, Fz）
   - central: 中央区（FC1, FC2, C3, C4, CP1, CP2）
   - left_TPJ: 左侧颞顶联合区（CP5, T7, C3）
   - right_TPJ: 右侧颞顶联合区（CP6, T8, C4）
   - occipital: 枕区（O1, Oz, O2, Pz）

3. **输出结果：**
   - **个体拓扑图**: 每个被试的五个频段拓扑图（`{subject_id}.jpg`）
   - **群体模板图**: 该年龄段的平均拓扑图（`template.jpg`）
   - **统计表格**: `sub_sim.xlsx`，包含：
     - 每个被试在各脑区、各频段的皮尔森相似度（与群体均值比较）
     - 每个被试在各脑区、各频段的分类标签（high/low/average）

**分类标准：**
- **high**: 功率值 > 群体均值 + 1 个标准差
- **average**: 功率值在均值 ± 1 个标准差之间
- **low**: 功率值 < 群体均值 - 1 个标准差

## 文件结构

```
main_GUI_demo/
│
├── main_GUI.py                    # 主 GUI 程序
├── step1_copy_data.py             # Step 1: 数据复制脚本
├── step2_preprocess_multiple.m    # Step 2: MATLAB 预处理脚本
├── step3_age_data_match.py        # Step 3: 年龄匹配脚本
├── step4_all_age.py               # Step 4: 批量分析脚本
├── age_parameters.py              # Step 4 核心分析函数
├── environment.yml                # Conda 环境配置文件
├── step_status.json               # 步骤状态记录文件
└── README.md                      # 项目说明文档
```

## 数据流程图

```
[原始 EEG 数据] 
    ↓
[Step 1: 数据复制] → .vhdr, .vmrk, .eeg 文件
    ↓
[Step 2: MATLAB 预处理] → .set, .fdt 文件
    ↓
[Step 3: 年龄匹配分组] → 按年龄段分组的 .set 文件
    ↓
[Step 4: 分析报告生成] → 拓扑图 (.jpg) + 统计表格 (.xlsx)
```

## 注意事项

1. **文件命名规范**: 确保 EEG 文件命名格式为 `{被试ID}_resting_...`，其中被试 ID 在文件名开头且用下划线分隔。

2. **路径配置**: 
   - Step 1 中的数据源路径需要在 `step1_copy_data.py` 中配置（第 36-38 行）
   - 确保所有路径使用完整的绝对路径

3. **MATLAB 引擎**: Step 2 需要启动 MATLAB 引擎，首次运行可能较慢。【学有余力可以换成python mne库代替处理，我个人更喜欢matlab的计算】

4. **内存要求**: 处理大量数据时需要足够的内存，建议至少 8GB RAM。

5. **步骤状态**: 点击"刷新步骤状态"按钮可重置所有步骤的完成状态。

6. **日志监控**: GUI 底部的日志输出框会实时显示处理进度，建议保持关注以及时发现错误。

## 常见问题

### Q1: MATLAB Engine 无法启动
**A**: 确保 MATLAB 已正确安装，并且 Python 的 MATLAB Engine API 已安装。检查 MATLAB 版本与 Python 版本的兼容性。

### Q2: Step 2 处理时间很长
**A**: EEGLAB 的预处理流程（特别是 ICA）比较耗时，这是正常现象。可以在日志中查看实时进度。

### Q3: 某些被试的文件缺失
**A**: Step 1 执行后会生成完整性报告，请根据报告检查并补充缺失的文件。

### Q4: 年龄段匹配失败
**A**: 检查 Excel 文件中的 ID 格式是否与文件名中的被试 ID 一致（注意大小写和前导零）。

### Q5: Step 4 生成的图片无法显示
**A**: 确保输出目录有写入权限，且系统支持 matplotlib 的图形渲染。

## 技术支持

如遇到问题或需要技术支持，请通过以下方式联系：
- 提交 Issue 到项目仓库

## 更新日志

### Version 1.0
- 初始版本发布
- 实现四步骤完整流程
- 提供 GUI 界面
- 支持多年龄段批量处理

## 许可证

本项目仅供学术研究使用。

## 致谢

本项目使用了以下开源工具和库：
- [MNE-Python](https://mne.tools/)
- [EEGLAB](https://sccn.ucsd.edu/eeglab/)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- [NumPy](https://numpy.org/)
- [Pandas](https://pandas.pydata.org/)
- [Matplotlib](https://matplotlib.org/)

---

**最后更新**: 2025-10-16

