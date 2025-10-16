"""
step4.py

功能：
- 读取 EEG .set 文件，计算 PSD 并生成 topomap
- 计算每个被试的 PSD 均值、与群体的皮尔森相似性
- 计算每个被试在每个频段区域的 high/low/average 标签
- 输出合并表格（包含 pearson 相似度与分类标签）
"""

import os
import sys
import json
import mne
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from scipy.stats import pearsonr
import warnings
import time
import contextlib
import io

# 忽略 boundary 相关警告
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*boundary.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*expanding outside the data range.*")
mne.set_log_level("WARNING") 

# ========== 准备频段和区域定义 ==========
bands = {
    'delta': (1, 4),
    'theta': (4, 8),
    'alpha': (8, 12),
    'beta': (12, 30),
    'gamma': (30, 40)
}
band_names = list(bands.keys())

channel_group_hemisphere = {
    'mid_frontal': ['FC5', 'FC6', 'F3', 'F4', 'Fz'],
    'central': ['FC1', 'FC2', 'C3', 'C4', 'CP1', 'CP2'],
    'left_TPJ': ['CP5','T7', 'C3'],
    'right_TPJ': ['CP6','T8', 'C4'],
    'occipital': ['O1', 'Oz', 'O2', 'Pz']
}

# ========== 主处理函数 ==========
def run_age_analysis(data_dir, output_dir):
    assert os.path.isdir(data_dir), f"Invalid data_dir: {data_dir}"
    os.makedirs(output_dir, exist_ok=True)

    file_list = [f for f in os.listdir(data_dir) if f.endswith('.set')]
    if len(file_list) == 0:
        print("No .set files found.")
        return

    psd_all = []
    psd_band_avg_all = []
    group_id = []
    skip_id = []

    start_time = time.time()
    last_print_time = start_time

    for idx, file_name in enumerate(file_list):
        subject_id = file_name.split('_')[0]
        if subject_id in skip_id:
            continue
        group_id.append(subject_id)

        # 静默加载 raw 数据，防止 MNE 输出干扰 GUI
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            raw = mne.io.read_raw_eeglab(os.path.join(data_dir, file_name), preload=True, verbose=False)

        spectrum = raw.compute_psd(method='welch', fmin=0, fmax=40)
        psds, freqs = spectrum.get_data(return_freqs=True)
        
        if 'channel_to_index' not in locals():
            channel_order = raw.ch_names
            channel_to_index = {ch: i for i, ch in enumerate(channel_order)}

        # 可视化并保存 topomap
        scaler = MinMaxScaler()
        psds_normalized = scaler.fit_transform(psds)
        fig, axes = plt.subplots(1, len(bands), figsize=(15, 3))
        psds_person = []
        for i, (band_name, (fmin, fmax)) in enumerate(bands.items()):
            idx_band = np.logical_and(freqs >= fmin, freqs <= fmax)
            psds_band = psds[:, idx_band]
            psds_person.append(psds_band)
            psds_band_norm = psds_normalized[:, idx_band]
            mne.viz.plot_topomap(np.mean(psds_band_norm, axis=1), raw.info, cmap='Reds', axes=axes[i], show=False)
            axes[i].set_title(f"{band_name} ({fmin}-{fmax}Hz)")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{subject_id}.jpg"))
        plt.close(fig)

        psd_all.append(psds_person)

        # 计算频段平均功率
        psd_band_avg = np.zeros((psds.shape[0], len(bands)))
        for i, (band, (fmin, fmax)) in enumerate(bands.items()):
            idx = np.logical_and(freqs >= fmin, freqs <= fmax)
            psd_band_avg[:, i] = np.mean(psds[:, idx], axis=1)
        psd_band_avg_all.append(psd_band_avg)

    psd_band_avg_all = np.array(psd_band_avg_all)
    group_psd_band_avg = np.mean(psd_band_avg_all, axis=0)

    def average_region_band_psd(psd_band, region_channels):
        region_psd = {}
        for region, ch_names in region_channels.items():
            idx = [channel_to_index[ch] for ch in ch_names if ch in channel_to_index]
            if not idx:
                continue
            region_psd[region] = np.mean(psd_band[idx, :], axis=0)
        return region_psd

    group_mean_psd = {band_name: {} for band_name in bands}
    for b_idx, band_name in enumerate(bands):
        for region in channel_group_hemisphere:
            region_psds = []
            for subj_psd in psd_all:
                psd_band = subj_psd[b_idx]
                region_psd = average_region_band_psd(psd_band, channel_group_hemisphere)
                if region in region_psd:
                    region_psds.append(region_psd[region])
            if region_psds:
                group_mean_psd[band_name][region] = np.mean(region_psds, axis=0)

    pearson_results = []
    for subj_idx, subj_psd in enumerate(psd_all):
        subject_id = group_id[subj_idx]
        sim_entry = {"subject_id": subject_id}
        for b_idx, band_name in enumerate(bands):
            region_psd_dict = average_region_band_psd(subj_psd[b_idx], channel_group_hemisphere)
            for region in region_psd_dict:
                subj_vector = region_psd_dict[region]
                group_vector = group_mean_psd[band_name][region]
                if len(subj_vector) != len(group_vector):
                    continue
                corr, _ = pearsonr(subj_vector, group_vector)
                sim_entry[f"{region}_{band_name}_pearson"] = corr
        pearson_results.append(sim_entry)

    region_names = list(channel_group_hemisphere.keys())
    region_band_values = np.zeros((len(group_id), len(region_names), len(bands)))
    for r_idx, region in enumerate(region_names):
        ch_indices = [channel_to_index[ch] for ch in channel_group_hemisphere[region] if ch in channel_to_index]
        region_band_values[:, r_idx, :] = np.mean(psd_band_avg_all[:, ch_indices, :], axis=1)

    region_band_mean = np.mean(region_band_values, axis=0)
    region_band_std = np.std(region_band_values, axis=0)

    classification = np.empty((len(group_id), len(region_names), len(bands)), dtype=object)
    for subj in range(len(group_id)):
        for r_idx in range(len(region_names)):
            for b_idx in range(len(bands)):
                val = region_band_values[subj, r_idx, b_idx]
                mean = region_band_mean[r_idx, b_idx]
                std = region_band_std[r_idx, b_idx]
                if val > mean + std:
                    classification[subj, r_idx, b_idx] = 'high'
                elif val < mean - std:
                    classification[subj, r_idx, b_idx] = 'low'
                else:
                    classification[subj, r_idx, b_idx] = 'average'

    classification_results = []
    for subj_idx, subject_id in enumerate(group_id):
        entry = {"subject_id": subject_id}
        for r_idx, region in enumerate(region_names):
            for b_idx, band_name in enumerate(bands):
                key = f"{region}_{band_name}_class"
                entry[key] = classification[subj_idx, r_idx, b_idx]
        classification_results.append(entry)

    fig = plot_band_topomap_norm(group_psd_band_avg, raw)
    output_path = os.path.join(output_dir, "template.jpg")
    fig.savefig(output_path)
    print(f"已保存模板拓扑图至: {output_dir}")

    final_results = []
    for r1, r2 in zip(pearson_results, classification_results):
        assert r1['subject_id'] == r2['subject_id']
        merged = {**r1, **r2}
        final_results.append(merged)

    df = pd.DataFrame(final_results)
    df.to_excel(os.path.join(output_dir, "sub_sim.xlsx"), index=False)
    print("分析完成，结果保存至 sub_sim.xlsx")

def plot_band_topomap_norm(psds, raw):
    """
    绘制频带拓扑图，并对数据进行归一化。

    参数：
    psds : ndarray
        形状为 (n_channels, n_bands) 的 PSD 数组。
    raw : mne.io.Raw
        包含电极布局和位置信息的 Raw 对象。
    """
    # 获取 montage
    montage = raw.get_montage()
    
    # 创建一个新的 info 对象，使用相同的通道名称和类型
    info = mne.create_info(ch_names=raw.ch_names, sfreq=raw.info['sfreq'], ch_types='eeg')
    info.set_montage(montage)
    
    # 绘制各频带的 topomap
    fig, axes = plt.subplots(1, len(bands), figsize=(15, 5))
    im = None
    for ax, (band, (fmin, fmax)) in zip(axes, bands.items()):
        # 计算频带内的平均功率
        band_power = psds[:, list(bands.keys()).index(band)]
        # 对 band_power 数据进行归一化
        band_power_normalized = normalize(band_power)
        # 绘制 topomap
        im, _ = mne.viz.plot_topomap(band_power_normalized, info, axes=ax, show=False)
        ax.set_title(band)
    
    # 添加 colorbar
    if im is not None:
        cbar = plt.colorbar(im, ax=axes, orientation='horizontal', fraction=0.05, pad=0.1)
        cbar.set_label('Normalized Power')

    return fig  # 返回图形对象

def normalize(data):
    """将数据归一化到 [0, 1] 范围内。"""
    min_val = np.min(data)
    max_val = np.max(data)
    return (data - min_val) / (max_val - min_val) if max_val > min_val else data

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EEG Step 4 Analysis by Age Range")
    parser.add_argument("--base_data_dir", required=True, help="Base directory containing age-range EEG .set files")
    parser.add_argument("--base_output_dir", required=True, help="Output directory to save results")
    parser.add_argument("--age_range_list", nargs="+", required=True, help="List of age ranges, e.g. 0-4 4-8 8-12")

    args = parser.parse_args()

    for age_range in args.age_range_list:
        data_dir = os.path.join(args.base_data_dir, age_range)
        output_dir = os.path.join(args.base_output_dir, age_range)
        try:
            run_age_analysis(data_dir, output_dir)
            print(f"成功完成: {age_range}")
        except Exception as e:
            print(f" 出错跳过: {age_range}，错误信息: {e}")

