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


# =========================================================
# 0) 基础配置
# =========================================================
BASE_TEMPLATE_DIR = r"E:\Heihe\panlongjiangPOINTsourceDPS30yr\Scenarios\Default\TxtInOutB=3"
RUN_ROOT = r"E:\Heihe\panlongjiangPOINTsourceDPS30yr\Scenarios\Default\B=3_parallel_runs"
EXE_NAME = "SWATDPS_v2.1.exe"

CSTD = 2.0
CMAX = 4.5
EXCEED_FRAC_MAX = 0.44
EXTREME_Q = 0.95

POP_SIZE = 100
N_GEN = 30

SEED = 42
N_WORKERS = 12
TIMEOUT_SECONDS = 1800

# =========================================================
# 0.5) dps_eval 输出年份检查
# 你当前 Fortran 输出条件是：
# if (curyr > 4 .and. curyr < 34) then
# 即 year = 5..33，共29年
# =========================================================
ENABLE_EVAL_YEAR_CHECK = True
EVAL_YEAR_START = 5
EVAL_YEAR_END = 33
EXPECTED_N_YEARS = EVAL_YEAR_END - EVAL_YEAR_START + 1  # 29


# =========================================================
# 0.6) 目标函数归一化配置
# =========================================================
TNLOAD_MIN = 0.0
TNLOAD_MAX = 398700.0

EXCEED_Q_MIN = 0.0
EXCEED_Q_MAX = CMAX - CSTD     # = 2.5

# fac = 1.2 - u, 且 u ∈ [0,1] -> fac ∈ [0.2, 1.2]
FAC_MIN_ALLOWED = 0.2
GOV_COST_MIN = 0.0
GOV_COST_MAX = (1.0 - FAC_MIN_ALLOWED) ** 2   # = 0.64

CLIP_OBJ_TO_01 = True


def norm01(x: float, xmin: float, xmax: float, clip: bool = True) -> float:
    if xmax <= xmin:
        raise ValueError(f"归一化上下限非法: xmin={xmin}, xmax={xmax}")
    y = (x - xmin) / (xmax - xmin)
    if clip:
        y = np.clip(y, 0.0, 1.0)
    return float(y)


# =========================================================
# 66 个决策变量
# B = 3, K = 3, N = 7
#
# ***** 这里严格按你当前 main.f 的读取顺序 *****
# main.f 读取顺序：
# 1) a(k), k=1..3
# 2) w(irbf,kout), irbf=1..7, kout=1..3   [irbf外层, kout内层]
# 3) c(irbf,jdim), irbf=1..7, jdim=1..3
# 4) r(irbf,jdim), irbf=1..7, jdim=1..3
# 5) 最后 Python 自动追加 job_id
#
# 即：
# [a1,a2,a3,
#  w11,w12,w13,w21,w22,w23,...,w71,w72,w73,
#  c11,c12,c13,c21,c22,c23,...,c71,c72,c73,
#  r11,r12,r13,r21,r22,r23,...,r71,r72,r73]
# =========================================================
DPS_N_RBF = 7
DPS_KOUT = 3
DPS_BDIM = 3
N_VAR = 66
N_CMD_ARGS_TOTAL = 67   # 66变量 + 1个job_id


def build_bounds_and_cols_66():
    xl = []
    xu = []
    cols = []

    # a(k), k=1..3
    for kout in range(1, DPS_KOUT + 1):
        xl.append(0.0)
        xu.append(1.0)
        cols.append(f"a{kout}")

    # w(irbf,kout), irbf 外层, kout 内层
    for irbf in range(1, DPS_N_RBF + 1):
        for kout in range(1, DPS_KOUT + 1):
            xl.append(-1.0)
            xu.append(1.0)
            cols.append(f"w{irbf}{kout}")

    # c(irbf,jdim), irbf 外层, jdim 内层
    for irbf in range(1, DPS_N_RBF + 1):
        for jdim in range(1, DPS_BDIM + 1):
            xl.append(0.0)
            xu.append(1.0)
            cols.append(f"c{irbf}{jdim}")

    # r(irbf,jdim), irbf 外层, jdim 内层
    for irbf in range(1, DPS_N_RBF + 1):
        for jdim in range(1, DPS_BDIM + 1):
            xl.append(0.01)
            xu.append(1.0)
            cols.append(f"r{irbf}{jdim}")

    return np.array(xl, dtype=float), np.array(xu, dtype=float), cols


XL, XU, X_COLS = build_bounds_and_cols_66()

BAD_F = np.array([1.0e30, 1.0e30, 1.0e30, 1.0e30, 1.0e30], dtype=float)
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
    当前 Fortran 表头：
    year TNload TNconc u1 u2 u3 fac1 fac2 fac3

    且当前你已经改成：
    同一行的 TNload / TNconc / u / fac 为同一年
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
            raise ValueError(
                f"dps_eval 行数异常：期望 {EXPECTED_N_YEARS} 行，实际 {len(df)} 行"
            )

        expected_years = list(range(EVAL_YEAR_START, EVAL_YEAR_END + 1))
        years_actual = df["year"].astype(int).tolist()
        if years_actual != expected_years:
            raise ValueError(
                f"dps_eval 年份异常：期望 {expected_years[0]}..{expected_years[-1]}，"
                f"实际为 {years_actual[:3]} ... {years_actual[-3:]}"
            )

    return df


# =========================================================
# 5) 目标函数与约束
# 与你当前 28 参数版保持一致
# =========================================================
def calc_objectives(df: pd.DataFrame, cstd: float, extreme_q: float) -> np.ndarray:
    """
    5 个目标（全部最小化），返回值全部为无量纲 [0,1]

    J1 = 平均年 TN 负荷
    J2 = 超标频率
    J3 = 极端超标强度（q95 of exceedance）
    J4 = 三个点源总体策略平滑性
    J5 = 三个点源总体治理成本
    """
    tnload = df["TNload"].to_numpy(dtype=float)
    tnconc = df["TNconc"].to_numpy(dtype=float)

    u = df[["u1", "u2", "u3"]].to_numpy(dtype=float)
    fac = df[["fac1", "fac2", "fac3"]].to_numpy(dtype=float)

    exceed = np.maximum(tnconc - cstd, 0.0)

    J1_raw = float(np.mean(tnload))
    J2_raw = float(np.mean(tnconc > cstd))
    J3_raw = float(np.quantile(exceed, extreme_q))
    J4_raw = float(np.mean(np.abs(np.diff(u, axis=0)))) if len(u) > 1 else 0.0
    J5_raw = float(np.mean(np.maximum(1.0 - fac, 0.0) ** 2))

    J1 = norm01(J1_raw, TNLOAD_MIN, TNLOAD_MAX, CLIP_OBJ_TO_01)
    J2 = norm01(J2_raw, 0.0, 1.0, CLIP_OBJ_TO_01)
    J3 = norm01(J3_raw, EXCEED_Q_MIN, EXCEED_Q_MAX, CLIP_OBJ_TO_01)
    J4 = norm01(J4_raw, 0.0, 1.0, CLIP_OBJ_TO_01)
    J5 = norm01(J5_raw, GOV_COST_MIN, GOV_COST_MAX, CLIP_OBJ_TO_01)

    return np.array([J1, J2, J3, J4, J5], dtype=float)


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
# 6) 运行一次 SWAT（独立 worker 目录）
# Python 参数顺序必须与 main.f 完全一致：
# [a1,a2,a3,
#  w11,w12,w13,w21,w22,w23,...,w71,w72,w73,
#  c11,c12,c13,c21,c22,c23,...,c71,c72,c73,
#  r11,r12,r13,r21,r22,r23,...,r71,r72,r73]
# 最后自动追加 job_id
# =========================================================
def run_swat_one_candidate(x: np.ndarray) -> tuple[int, pd.DataFrame]:
    worker_id = WORKER_QUEUE.get()
    worker_dir = WORKER_DIRS[worker_id]

    try:
        job_id = next_job_id()
        cleanup_job_files(worker_dir, job_id)

        x = np.asarray(x, dtype=float).ravel()
        if x.size != N_VAR:
            raise ValueError(f"输入参数长度={x.size}，但 66 参数版要求 N_VAR={N_VAR}")

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
# 7) pymoo 问题定义
# =========================================================
class SWATDPSProblem(Problem):
    def __init__(self, n_threads=1):
        super().__init__(
            n_var=N_VAR,
            n_obj=5,
            n_ieq_constr=2,
            xl=XL,
            xu=XU
        )
        self.pool = ThreadPool(n_threads)

    def _evaluate(self, X, out, *args, **kwargs):
        def eval_one(x):
            try:
                _, df = run_swat_one_candidate(np.asarray(x, dtype=float))
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
# 8) 收敛诊断 callback
# =========================================================
class ConvergenceCallback(Callback):
    def __init__(self):
        super().__init__()
        self.rows = []

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

        self.rows.append(row)

    def to_dataframe(self) -> pd.DataFrame:
        if len(self.rows) == 0:
            return pd.DataFrame()

        hist_df = pd.DataFrame(self.rows)

        obj_cols = [c for c in hist_df.columns if c.endswith("_min")]
        for col in obj_cols:
            improve_col = col.replace("_min", "_improve_from_prev")
            hist_df[improve_col] = hist_df[col].shift(1) - hist_df[col]

        return hist_df


def save_convergence_outputs(hist_df: pd.DataFrame, out_dir: str, tail_n: int = 10):
    if hist_df is None or hist_df.empty:
        print("没有可用的收敛历史，跳过收敛输出。")
        return

    hist_csv = os.path.join(out_dir, "nsga2_convergence_history_66.csv")
    hist_df.to_csv(hist_csv, index=False, encoding="utf-8-sig")

    obj_cols = [c for c in hist_df.columns if c.endswith("_min")]
    tail_df = hist_df.tail(min(tail_n, len(hist_df))).copy()

    summary = {}
    for col in obj_cols:
        improve_col = col.replace("_min", "_improve_from_prev")
        arr = tail_df[improve_col].to_numpy(dtype=float)
        summary[f"{col}_tail_mean_improve"] = float(np.nanmean(arr))
        summary[f"{col}_tail_max_improve"] = float(np.nanmax(arr))

    summary_rows = [{
        "n_generations": int(len(hist_df)),
        "tail_n": int(min(tail_n, len(hist_df))),
        "first_gen_feasible_ratio": float(hist_df["feasible_ratio"].iloc[0]),
        "last_gen_feasible_ratio": float(hist_df["feasible_ratio"].iloc[-1]),
        **summary
    }]
    summary_df = pd.DataFrame(summary_rows)

    summary_csv = os.path.join(out_dir, "nsga2_convergence_summary_66.csv")
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
    show_cols = ["gen", "n_feasible", "feasible_ratio"] + obj_cols
    print(hist_df[show_cols].tail(min(10, len(hist_df))))

    print("\n最近几代平均改进幅度（正数表示仍在改善，越接近 0 说明越停滞）：")
    for k, v in summary.items():
        if "tail_mean_improve" in k:
            print(f"{k}: {v:.6e}")


# =========================================================
# 9) 主程序
# =========================================================
def main():
    print("\n================ 当前 DPS 版本 ================")
    print("说明              = 66个决策变量（B=3, K=3, N=7），命令行总参数=67（最后一个是 job_id）")
    print("命令行读取顺序     = a -> w -> c -> r -> job_id")
    print(f"N_VAR             = {N_VAR}")
    print(f"N_CMD_ARGS(total) = {N_CMD_ARGS_TOTAL}")
    print(f"N_RBF             = {DPS_N_RBF}")
    print(f"KOUT              = {DPS_KOUT}")
    print(f"BDIM              = {DPS_BDIM}")
    print("==============================================\n")

    prepare_worker_dirs()

    problem = SWATDPSProblem(n_threads=N_WORKERS)
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
            f"EXCEED_FRAC_MAX={EXCEED_FRAC_MAX}, EXTREME_Q={EXTREME_Q}"
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
                "2) main.f 是否仍然接收 66 个参数 + 1 个 job_id；"
                "3) Python 与 Fortran 的参数顺序是否完全一致；"
                "4) CMAX / EXCEED_FRAC_MAX 是否设得过严；"
                "5) CSTD/CMAX 是否与你当前研究设定一致。"
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

        df_x = pd.DataFrame(X, columns=X_COLS)
        df_f = pd.DataFrame(F, columns=[
            "J1n_TNload_mean_01",
            "J2n_exceedance_frequency_01",
            "J3n_extreme_exceedance_q95_01",
            "J4n_total_smoothness_01",
            "J5n_total_governance_cost_01"
        ])

        if G is not None:
            df_g = pd.DataFrame(G, columns=[
                "g1_max_TNconc_minus_CMAX",
                "g2_exceed_freq_minus_limit"
            ])
            df_out = pd.concat([df_x, df_f, df_g], axis=1)
        else:
            df_out = pd.concat([df_x, df_f], axis=1)

        out_csv = os.path.join(BASE_TEMPLATE_DIR, "pareto_solutions_nsga2_66.csv")
        df_out.to_csv(out_csv, index=False, encoding="utf-8-sig")

        cfg_json = os.path.join(BASE_TEMPLATE_DIR, "nsga2_run_config_66.json")
        with open(cfg_json, "w", encoding="utf-8") as f:
            json.dump({
                "desc": "66个决策变量（B=3, K=3, N=7），命令行总参数=67（最后一个是 job_id）",
                "read_order_note": "Python与Fortran统一为 a -> w -> c -> r -> job_id",
                "n_rbf": DPS_N_RBF,
                "n_kout": DPS_KOUT,
                "n_bdim": DPS_BDIM,
                "n_var": N_VAR,
                "n_cmd_args_total": N_CMD_ARGS_TOTAL,
                "x_cols": X_COLS,
                "base_template_dir": BASE_TEMPLATE_DIR,
                "run_root": RUN_ROOT,
                "exe_name": EXE_NAME,
                "dps_eval_columns": ["year", "TNload", "TNconc", "u1", "u2", "u3", "fac1", "fac2", "fac3"],
                "dps_eval_note": "当前 dps_eval 中同一行 TNload/TNconc/u/fac 已对齐，且无 z 列",
                "eval_year_check_enabled": ENABLE_EVAL_YEAR_CHECK,
                "eval_year_range": [EVAL_YEAR_START, EVAL_YEAR_END],
                "cstd": CSTD,
                "cmax_constraint": CMAX,
                "j3_normalization_upper_bound": EXCEED_Q_MAX,
                "exceed_frac_constraint": EXCEED_FRAC_MAX,
                "extreme_quantile_for_J3": EXTREME_Q,
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