# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import ctypes
import shutil
import queue
import traceback
import subprocess
import threading
from itertools import count
from multiprocessing.pool import ThreadPool

import numpy as np
import pandas as pd

from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.core.problem import Problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.core.callback import Callback
from pymoo.indicators.hv import HV
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting


# =========================================================
# 0) 基础配置
# =========================================================
BASE_TEMPLATE_DIR = r"E:\Heihe\panlongjiangPOINTsourceDPS30yr\Scenarios\Default\TxtInOutbase10000"
RUN_ROOT = r"E:\Heihe\panlongjiangPOINTsourceDPS30yr\Scenarios\Default\base10000_parallel_runs"
EXE_NAME = "SWAT_DPSbase.exe"

CSTD = 2.0
CMAX = 4.5
EXCEED_FRAC_MAX = 0.44
EXTREME_Q = 0.95

POP_SIZE = 100
N_GEN = 1000

SEED = 42
N_WORKERS = 12
TIMEOUT_SECONDS = 1800


# =========================================================
# 0.5) 直接优化 uk 的维度设置
# 你现在的 Fortran 已改为：
#   uk 共 87 个 + 1 个 job_id = 88 个命令行参数
# 映射到：
#   dps_u_yr(5:33,1:3)
# 即：
#   29 年 × 3 个 kout = 87 个变量
# =========================================================
UK_YEAR_START = 5
UK_YEAR_END = 33
N_UK_YEARS = UK_YEAR_END - UK_YEAR_START + 1   # 29
N_KOUT = 3
N_VAR = N_UK_YEARS * N_KOUT                    # 87
N_CMD_ARGS_TOTAL = N_VAR + 1                   # 88


# =========================================================
# 0.6) dps_eval 输出年份检查
# 当前 Fortran 输出条件：
# if (curyr > 4 .and. curyr < 34) then
# 即 year = 5..33，共29年
# =========================================================
ENABLE_EVAL_YEAR_CHECK = True
EVAL_YEAR_START = 5
EVAL_YEAR_END = 33
EXPECTED_N_YEARS = EVAL_YEAR_END - EVAL_YEAR_START + 1  # 29


# =========================================================
# 0.7) 目标函数归一化配置
# =========================================================
TNLOAD_MIN = 0.0
TNLOAD_MAX = 395400.0

# J2 采用 CMAX - CSTD = 2.5 作为归一化上限
EXCEED_Q_MIN = 0.0
EXCEED_Q_MAX = CMAX - CSTD  # = 2.5

# fac = 1.2 - u, 且 u ∈ [0,1]，则 fac ∈ [0.2, 1.2]
# max(1-fac, 0)^2 的最大值为 (1-0.2)^2 = 0.64
FAC_MIN_ALLOWED = 0.2
GOV_COST_MIN = 0.0
GOV_COST_MAX = (1.0 - FAC_MIN_ALLOWED) ** 2   # = 0.64

CLIP_OBJ_TO_01 = True
HV_REF_POINT = np.array([1.1, 1.1, 1.1, 1.1], dtype=float)


def norm01(x: float, xmin: float, xmax: float, clip: bool = True) -> float:
    if xmax <= xmin:
        raise ValueError(f"归一化上下限非法: xmin={xmin}, xmax={xmax}")
    y = (x - xmin) / (xmax - xmin)
    if clip:
        y = np.clip(y, 0.0, 1.0)
    return float(y)


# =========================================================
# 29×3 个 uk 决策变量
# 顺序：
# [u(5,1),u(5,2),u(5,3),u(6,1),...,u(33,3)]
# 与你的 Fortran 保持一致：
# do it = 1,29
#   idx_yr = it + 4   ! 5..33
#   do kout = 1,dps_kout
# =========================================================
XL = np.zeros(N_VAR, dtype=float)
XU = np.ones(N_VAR, dtype=float)

BAD_F = np.array([1.0e30, 1.0e30, 1.0e30, 1.0e30], dtype=float)
BAD_G = np.array([1.0e30, 1.0e30], dtype=float)


# =========================================================
# 1) Windows / Conda / OpenMP 稳定性设置
# =========================================================
if os.name == "nt":
    try:
        ctypes.windll.kernel32.SetDllDirectoryW("")
    except Exception:
        pass

env_bin = os.path.join(sys.prefix, "Library", "bin")
if os.path.isdir(env_bin):
    os.environ["PATH"] = env_bin + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(env_bin)
        except Exception:
            pass

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"


# =========================================================
# 2) 全局 job_id 生成器
# =========================================================
_job_counter = count(1)
_job_lock = threading.Lock()


def next_job_id() -> int:
    with _job_lock:
        return next(_job_counter)


# =========================================================
# 3) worker 目录准备
# =========================================================
WORKER_DIRS = {}
WORKER_QUEUE = queue.Queue()


def prepare_worker_dirs():
    if not os.path.isdir(BASE_TEMPLATE_DIR):
        raise NotADirectoryError(f"BASE_TEMPLATE_DIR 不存在: {BASE_TEMPLATE_DIR}")

    exe_in_base = os.path.join(BASE_TEMPLATE_DIR, EXE_NAME)
    if not os.path.exists(exe_in_base):
        raise FileNotFoundError(f"母版目录中未找到 exe: {exe_in_base}")

    if os.path.exists(RUN_ROOT):
        shutil.rmtree(RUN_ROOT)
    os.makedirs(RUN_ROOT, exist_ok=True)

    print(f"正在创建 {N_WORKERS} 个独立 worker 目录，请稍等...")

    for wid in range(N_WORKERS):
        worker_dir = os.path.join(RUN_ROOT, f"worker_{wid}")
        shutil.copytree(
            BASE_TEMPLATE_DIR,
            worker_dir,
            ignore=shutil.ignore_patterns(
                "_parallel_runs",
                "__pycache__",
                "*.pyc",
                "*.pyo"
            )
        )

        WORKER_DIRS[wid] = worker_dir
        WORKER_QUEUE.put(wid)

    print("worker 目录创建完成：")
    for wid, wdir in WORKER_DIRS.items():
        print(f"  worker_{wid}: {wdir}")


# =========================================================
# 4) 文件与结果处理工具
# =========================================================
def cleanup_job_files(workdir: str, job_id: int) -> None:
    candidates = [
        os.path.join(workdir, f"{job_id}_dps_eval.out"),
        os.path.join(workdir, f"{job_id}_stdout.log"),
        os.path.join(workdir, f"{job_id}_stderr.log"),
        os.path.join(workdir, f"{job_id}output.rch"),
    ]
    for f in candidates:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


def read_dps_eval(workdir: str, job_id: int) -> pd.DataFrame:
    """
    当前 Fortran 输出表头为：
    year TNload TNconc u1 u2 u3 fac1 fac2 fac3

    并且同一行的 TNload / TNconc / u / fac 已经是同一年。
    """
    eval_file = os.path.join(workdir, f"{job_id}_dps_eval.out")
    if not os.path.exists(eval_file):
        raise FileNotFoundError(f"未找到结果文件: {eval_file}")

    df = pd.read_csv(eval_file, sep=r"\s+", engine="python")

    required_cols = {
        "year", "TNload", "TNconc",
        "u1", "u2", "u3",
        "fac1", "fac2", "fac3"
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"结果文件缺少列: {missing}")

    if len(df) == 0:
        raise ValueError("结果文件为空")

    numeric_cols = ["year", "TNload", "TNconc", "u1", "u2", "u3", "fac1", "fac2", "fac3"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df[numeric_cols].isna().any().any():
        raise ValueError("结果文件中存在 NaN")

    if ENABLE_EVAL_YEAR_CHECK:
        if len(df) != EXPECTED_N_YEARS:
            raise ValueError(f"dps_eval 行数异常：期望 {EXPECTED_N_YEARS} 行，实际 {len(df)} 行")

        expected_years = list(range(EVAL_YEAR_START, EVAL_YEAR_END + 1))
        years_actual = df["year"].astype(int).tolist()
        if years_actual != expected_years:
            raise ValueError(
                f"dps_eval 年份异常：期望 {expected_years[0]}..{expected_years[-1]}，"
                f"实际为 {years_actual[:3]} ... {years_actual[-3:]}"
            )

    return df


# =========================================================
# 5) 决策变量列名
# 输出为 u5_1 ... u33_3
# =========================================================
def make_x_column_names():
    cols = []
    for yr in range(UK_YEAR_START, UK_YEAR_END + 1):
        for kout in range(1, N_KOUT + 1):
            cols.append(f"u{yr}_{kout}")
    return cols


# =========================================================
# 6) 目标函数与约束
# J1~J4 与你当前 28/66/92 参数 DPS 版保持一致
# =========================================================
def calc_objectives(df: pd.DataFrame, cstd: float, extreme_q: float) -> np.ndarray:
    """
    4 个目标（全部最小化），返回值全部为无量纲 [0,1]

    J1 = 平均年 TN 负荷
    J2 = 极端超标强度（q95 of exceedance）
    J3 = 三个点源总体策略平滑性
    J4 = 三个点源总体治理成本
    """
    tnload = df["TNload"].to_numpy(dtype=float)
    tnconc = df["TNconc"].to_numpy(dtype=float)

    u = df[["u1", "u2", "u3"]].to_numpy(dtype=float)
    fac = df[["fac1", "fac2", "fac3"]].to_numpy(dtype=float)

    exceed = np.maximum(tnconc - cstd, 0.0)

    T = len(df)

    J1_raw = float(np.mean(tnload))
    J2_raw = float(np.quantile(exceed, extreme_q))
    J3_raw = float(np.mean(np.abs(np.diff(u, axis=0)))) if T > 1 else 0.0
    J4_raw = float(np.mean(np.maximum(1.0 - fac, 0.0) ** 2))

    J1 = norm01(J1_raw, TNLOAD_MIN, TNLOAD_MAX, CLIP_OBJ_TO_01)
    J2 = norm01(J2_raw, EXCEED_Q_MIN, EXCEED_Q_MAX, CLIP_OBJ_TO_01)
    J3 = norm01(J3_raw, 0.0, 1.0, CLIP_OBJ_TO_01)
    J4 = norm01(J4_raw, GOV_COST_MIN, GOV_COST_MAX, CLIP_OBJ_TO_01)

    return np.array([J1, J2, J3, J4], dtype=float)


def calc_constraints(df: pd.DataFrame, cstd: float, cmax: float, exceed_frac_max: float) -> np.ndarray:
    """
    2 个不等式约束（pymoo 格式：G <= 0）
    g1 = max(TNconc) - CMAX <= 0
    g2 = exceedance_frequency - EXCEED_FRAC_MAX <= 0
    """
    tnconc = df["TNconc"].to_numpy(dtype=float)

    g1 = float(np.max(tnconc) - cmax)
    exceed_freq = float(np.mean(tnconc > cstd))
    g2 = float(exceed_freq - exceed_frac_max)

    return np.array([g1, g2], dtype=float)


# =========================================================
# 7) 运行一次 SWAT（独立 worker 目录）
# 这里会把 87 个 uk + 1 个 job_id 传给 exe
# 所以你的 Fortran main 也必须同步为接收 88 个命令行参数
# =========================================================
def run_swat_one_candidate(x: np.ndarray) -> tuple[int, pd.DataFrame]:
    """
    x 顺序：
    [u(5,1),u(5,2),u(5,3),u(6,1),...,u(33,3)]
    """
    worker_id = WORKER_QUEUE.get()
    worker_dir = WORKER_DIRS[worker_id]

    try:
        job_id = next_job_id()
        cleanup_job_files(worker_dir, job_id)

        x = np.asarray(x, dtype=float).ravel()
        if x.size != N_VAR:
            raise ValueError(f"决策变量长度错误：期望 {N_VAR}，实际 {x.size}")

        exe_path = os.path.join(worker_dir, EXE_NAME)
        if not os.path.exists(exe_path):
            raise FileNotFoundError(f"未找到可执行文件: {exe_path}")

        cmd = [exe_path] + [str(v) for v in x.tolist()] + [str(job_id)]

        stdout_log = os.path.join(worker_dir, f"{job_id}_stdout.log")
        stderr_log = os.path.join(worker_dir, f"{job_id}_stderr.log")
        eval_file = os.path.join(worker_dir, f"{job_id}_dps_eval.out")

        print(f"\n[worker_{worker_id} | job_id={job_id}] 启动 SWAT")
        print("[cwd] ", worker_dir)

        t0 = time.time()
        result = subprocess.run(
            cmd,
            cwd=worker_dir,
            capture_output=True,
            text=True,
            encoding="gbk" if os.name == "nt" else None,
            errors="ignore",
            timeout=TIMEOUT_SECONDS
        )
        elapsed = time.time() - t0

        with open(stdout_log, "w", encoding="utf-8", errors="ignore") as f:
            f.write(result.stdout or "")

        with open(stderr_log, "w", encoding="utf-8", errors="ignore") as f:
            f.write(result.stderr or "")

        print(f"[worker_{worker_id} | job_id={job_id}] returncode = {result.returncode}")
        print(f"[worker_{worker_id} | job_id={job_id}] elapsed    = {elapsed:.1f}s")

        if result.returncode != 0:
            raise RuntimeError(
                f"SWAT returncode={result.returncode}\n"
                f"stdout_log: {stdout_log}\n"
                f"stderr_log: {stderr_log}"
            )

        if not os.path.exists(eval_file):
            raise FileNotFoundError(
                f"SWAT 正常退出，但未找到结果文件: {eval_file}\n"
                f"stdout_log: {stdout_log}\n"
                f"stderr_log: {stderr_log}"
            )

        df = read_dps_eval(worker_dir, job_id)

        print(
            f"[worker_{worker_id} | job_id={job_id}] 完成 | "
            f"最后一年 TNconc = {df['TNconc'].iloc[-1]:.4f}"
        )

        return job_id, df

    finally:
        WORKER_QUEUE.put(worker_id)


# =========================================================
# 8) pymoo 问题定义
# =========================================================
class SWATDirectUKProblem(Problem):
    def __init__(self, n_threads=1):
        super().__init__(
            n_var=N_VAR,
            n_obj=4,
            n_ieq_constr=2,
            xl=XL,
            xu=XU
        )
        self.pool = ThreadPool(n_threads)

    def _evaluate(self, X, out, *args, **kwargs):
        def eval_one(x):
            try:
                x = np.asarray(x, dtype=float).ravel()
                _, df = run_swat_one_candidate(x)

                F = calc_objectives(df, CSTD, EXTREME_Q)
                G = calc_constraints(df, CSTD, CMAX, EXCEED_FRAC_MAX)

                return F, G

            except Exception as e:
                print("\n[评估失败] 参数 =", np.asarray(x, dtype=float))
                print("错误信息：", str(e))
                print(traceback.format_exc())
                return BAD_F, BAD_G

        params = [[X[k]] for k in range(len(X))]
        results = self.pool.starmap(eval_one, params)

        out["F"] = np.array([r[0] for r in results], dtype=float)
        out["G"] = np.array([r[1] for r in results], dtype=float)

    def close(self):
        self.pool.close()
        self.pool.join()


# =========================================================
# 9) 收敛诊断 callback
# =========================================================
class ConvergenceCallback(Callback):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.hv_indicator = HV(ref_point=HV_REF_POINT)
        self.nds = NonDominatedSorting()

    def notify(self, algorithm):
        pop = algorithm.pop
        F = pop.get("F")
        G = pop.get("G")

        if F is None or len(F) == 0:
            return

        F = np.asarray(F, dtype=float)

        if G is None:
            feasible = np.ones(F.shape[0], dtype=bool)
        else:
            G = np.asarray(G, dtype=float)
            if G.ndim == 1:
                G = G.reshape(-1, 1)
            feasible = np.all(G <= 0.0, axis=1)

        n_total = F.shape[0]
        n_feas = int(np.sum(feasible))
        feas_ratio = n_feas / n_total if n_total > 0 else np.nan

        if n_feas > 0:
            F_use = F[feasible]
            basis = "feasible"
        else:
            F_use = F
            basis = "all"

        row = {
            "gen": int(algorithm.n_gen),
            "n_total": n_total,
            "n_feasible": n_feas,
            "feasible_ratio": feas_ratio,
            "basis": basis,
        }

        n_obj = F_use.shape[1]
        for j in range(n_obj):
            fj = F_use[:, j]
            row[f"J{j+1}_min"] = float(np.min(fj))
            row[f"J{j+1}_mean"] = float(np.mean(fj))
            row[f"J{j+1}_max"] = float(np.max(fj))
            row[f"J{j+1}_span"] = float(np.max(fj) - np.min(fj))

        if n_feas > 0:
            nd_idx = self.nds.do(F_use, only_non_dominated_front=True)
            F_nd = F_use[nd_idx]
            row["hypervolume"] = float(self.hv_indicator.do(F_nd))
        else:
            row["hypervolume"] = np.nan

        self.rows.append(row)

    def to_dataframe(self) -> pd.DataFrame:
        if len(self.rows) == 0:
            return pd.DataFrame()

        hist_df = pd.DataFrame(self.rows)

        obj_cols = [c for c in hist_df.columns if c.endswith("_min")]
        for col in obj_cols:
            improve_col = col.replace("_min", "_improve_from_prev")
            hist_df[improve_col] = hist_df[col].shift(1) - hist_df[col]

        if "hypervolume" in hist_df.columns:
            hist_df["hypervolume_improve_from_prev"] = hist_df["hypervolume"] - hist_df["hypervolume"].shift(1)

        return hist_df


def save_convergence_outputs(hist_df: pd.DataFrame, out_dir: str, tail_n: int = 10):
    if hist_df is None or hist_df.empty:
        print("没有可用的收敛历史，跳过收敛输出。")
        return

    hist_csv = os.path.join(out_dir, "nsga2_convergence_history_direct_uk_29x3.csv")
    hist_df.to_csv(hist_csv, index=False, encoding="utf-8-sig")

    obj_cols = [c for c in hist_df.columns if c.endswith("_min")]
    tail_df = hist_df.tail(min(tail_n, len(hist_df))).copy()

    summary = {}
    for col in obj_cols:
        improve_col = col.replace("_min", "_improve_from_prev")
        arr = tail_df[improve_col].to_numpy(dtype=float)
        summary[f"{col}_tail_mean_improve"] = float(np.nanmean(arr))
        summary[f"{col}_tail_max_improve"] = float(np.nanmax(arr))

    if "hypervolume_improve_from_prev" in tail_df.columns:
        hv_arr = tail_df["hypervolume_improve_from_prev"].to_numpy(dtype=float)
        summary["hypervolume_tail_mean_improve"] = float(np.nanmean(hv_arr))
        summary["hypervolume_tail_max_improve"] = float(np.nanmax(hv_arr))
        summary["last_hypervolume"] = float(hist_df["hypervolume"].iloc[-1])

    summary_rows = [{
        "n_generations": int(len(hist_df)),
        "tail_n": int(min(tail_n, len(hist_df))),
        "first_gen_feasible_ratio": float(hist_df["feasible_ratio"].iloc[0]),
        "last_gen_feasible_ratio": float(hist_df["feasible_ratio"].iloc[-1]),
        **summary
    }]
    summary_df = pd.DataFrame(summary_rows)

    summary_csv = os.path.join(out_dir, "nsga2_convergence_summary_direct_uk_29x3.csv")
    summary_df.to_csv(summary_csv, index=False, encoding="utf-8-sig")

    print("\n================ 收敛诊断摘要 ================")
    print(f"历史文件已保存: {hist_csv}")
    print(f"摘要文件已保存: {summary_csv}")
    print(f"总代数: {len(hist_df)}")
    print(
        f"可行率: 第1代 = {hist_df['feasible_ratio'].iloc[0]:.3f}, "
        f"最后1代 = {hist_df['feasible_ratio'].iloc[-1]:.3f}"
    )

    print("\n最近几代最优值：")
    show_cols = ["gen", "n_feasible", "feasible_ratio", "hypervolume"] + obj_cols
    print(hist_df[show_cols].tail(min(10, len(hist_df))))

    print("\n最近几代平均改进幅度（正数表示仍在改善，越接近 0 说明越停滞）：")
    for k, v in summary.items():
        if "tail_mean_improve" in k:
            print(f"{k}: {v:.6e}")


# =========================================================
# 10) 主程序
# =========================================================
def main():
    prepare_worker_dirs()

    problem = SWATDirectUKProblem(n_threads=N_WORKERS)
    callback = ConvergenceCallback()

    try:
        algorithm = NSGA2(
            pop_size=POP_SIZE,
            eliminate_duplicates=True,
            crossover=SBX(prob=0.9, eta=15),
            mutation=PM(prob=0.1, eta=20)
        )

        print(
            f"\n当前运行参数: POP_SIZE={POP_SIZE}, N_GEN={N_GEN}, "
            f"N_WORKERS={N_WORKERS}, CSTD={CSTD}, CMAX={CMAX}, "
            f"EXCEED_FRAC_MAX={EXCEED_FRAC_MAX}, EXTREME_Q={EXTREME_Q}, "
            f"N_VAR={N_VAR} (={N_UK_YEARS}×{N_KOUT}), "
            f"CMD_ARGS_TOTAL={N_CMD_ARGS_TOTAL}"
        )

        res = minimize(
            problem,
            algorithm,
            termination=("n_gen", N_GEN),
            seed=SEED,
            verbose=True,
            save_history=False,
            callback=callback
        )

        if res.X is None or res.F is None:
            raise RuntimeError(
                "优化结束，但没有得到可用解。"
                "请优先检查：1) SWAT 是否正常输出 dps_eval；"
                "2) Fortran main 是否已改为接收 87 个 uk + 1 个 job_id（共 88 个参数）；"
                "3) CMAX / EXCEED_FRAC_MAX 是否设得过严；"
                "4) CSTD/CMAX 是否与研究设定一致。"
            )

        X = np.asarray(res.X, dtype=float)
        F = np.asarray(res.F, dtype=float)
        G = np.asarray(res.G, dtype=float) if res.G is not None else None

        if X.ndim == 1:
            X = X.reshape(1, -1)
        if F.ndim == 1:
            F = F.reshape(1, -1)
        if G is not None and G.ndim == 1:
            G = G.reshape(1, -1)

        x_cols = make_x_column_names()

        f_cols = [
            "J1n_TNload_mean_01",
            "J2n_extreme_exceedance_q95_01",
            "J3n_total_smoothness_01",
            "J4n_total_governance_cost_01"
        ]

        df_x = pd.DataFrame(X, columns=x_cols)
        df_f = pd.DataFrame(F, columns=f_cols)

        if G is not None:
            g_cols = [
                "g1_max_TNconc_minus_CMAX",
                "g2_exceed_freq_minus_limit"
            ]
            df_g = pd.DataFrame(G, columns=g_cols)
            df_out = pd.concat([df_x, df_f, df_g], axis=1)
        else:
            df_out = pd.concat([df_x, df_f], axis=1)

        out_csv = os.path.join(BASE_TEMPLATE_DIR, "pareto_solutions_nsga2_direct_uk_29x3.csv")
        df_out.to_csv(out_csv, index=False, encoding="utf-8-sig")

        cfg_json = os.path.join(BASE_TEMPLATE_DIR, "nsga2_run_config_direct_uk_29x3.json")
        with open(cfg_json, "w", encoding="utf-8") as f:
            json.dump({
                "base_template_dir": BASE_TEMPLATE_DIR,
                "run_root": RUN_ROOT,
                "exe_name": EXE_NAME,
                "mode": "direct_uk_29x3",
                "n_uk_years": N_UK_YEARS,
                "uk_year_range": [UK_YEAR_START, UK_YEAR_END],
                "n_kout": N_KOUT,
                "n_var": N_VAR,
                "cmd_args_total": N_CMD_ARGS_TOTAL,
                "fortran_mapping_assumption": {
                    "x_to_dps_u_yr": "87 uk values -> dps_u_yr(5:33,1:3)",
                    "note": "当前 dps_eval 输出年份为 curyr=5..33，且同一行 TNload/TNconc/u/fac 已对齐"
                },
                "dps_eval_columns": ["year", "TNload", "TNconc", "u1", "u2", "u3", "fac1", "fac2", "fac3"],
                "j4_j5_source": "dps_eval.out columns u1,u2,u3,fac1,fac2,fac3",
                "fac_relation_note": "fac = 1.2 - u, but Python does not reconstruct fac; it reads fac1,fac2,fac3 directly from dps_eval.out",
                "cstd": CSTD,
                "cmax_constraint": CMAX,
                "j2_extreme_exceedance_normalization_upper_bound": EXCEED_Q_MAX,
                "exceed_frac_constraint": EXCEED_FRAC_MAX,
                "extreme_quantile_for_J2": EXTREME_Q,
                "tnload_min": TNLOAD_MIN,
                "tnload_max": TNLOAD_MAX,
                "gov_cost_min": GOV_COST_MIN,
                "gov_cost_max": GOV_COST_MAX,
                "clip_obj_to_01": CLIP_OBJ_TO_01,
                "pop_size": POP_SIZE,
                "n_gen": N_GEN,
                "n_workers": N_WORKERS,
                "seed": SEED,
                "xl": XL.tolist(),
                "xu": XU.tolist()
            }, f, ensure_ascii=False, indent=2)

        hist_df = callback.to_dataframe()
        save_convergence_outputs(hist_df, BASE_TEMPLATE_DIR, tail_n=10)

        print("\n优化完成。")
        print(f"Pareto 解已保存到: {out_csv}")
        print(f"运行配置已保存到: {cfg_json}")
        print("\n前 5 组解：")
        print(df_out.head())

    finally:
        problem.close()


if __name__ == "__main__":
    main()
