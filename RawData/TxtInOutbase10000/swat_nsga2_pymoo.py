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

from pymoo.core.problem import Problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize


# =========================================================
# 0) 基础配置
# =========================================================
# 母版目录：必须是你单独运行 SWAT 已经能跑通的目录
BASE_TEMPLATE_DIR = r"E:\\Heihe\\panlongjiangPOINTsourceDPStest\\Scenarios\Default\\TxtInOut"

# 注意：RUN_ROOT 必须放在 BASE_TEMPLATE_DIR 外面，不能放里面
RUN_ROOT = r"E:\\Heihe\\panlongjiangPOINTsourceDPStest\\Scenarios\\Default\\_parallel_runs"

EXE_NAME = "SWAT664DPSyr.exe"

# Python 侧计算可靠度时用的阈值
# 要与你 SWAT 源码里写死的 cstd 一致
CSTD = 2.0

# 优化设置（先小规模测试）
POP_SIZE = 16
N_GEN = 4
SEED = 42

# 并行 worker 数
N_WORKERS = 8

# 单次 SWAT 最大运行时间（秒）
TIMEOUT_SECONDS = 1800

# 决策变量顺序：
# [a, c1, c2, c3, w1, w2, w3, r1, r2, r3]
XL = np.array([
    0.0,   0.0, 0.0, 0.0,
   -1.0, -1.0, -1.0,
    0.05, 0.05, 0.05
], dtype=float)

XU = np.array([
    1.0,   1.0, 1.0, 1.0,
    1.0,   1.0, 1.0,
    1.00,  1.00, 1.00
], dtype=float)

BAD_F = np.array([1.0e30, 1.0, 1.0e6, 1.0e6], dtype=float)


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
    eval_file = os.path.join(workdir, f"{job_id}_dps_eval.out")
    if not os.path.exists(eval_file):
        raise FileNotFoundError(f"未找到结果文件: {eval_file}")

    df = pd.read_csv(eval_file, sep=r"\s+", engine="python")

    required_cols = {"year", "TNload", "TNconc", "z", "ustar", "fac"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"结果文件缺少列: {missing}")

    if len(df) == 0:
        raise ValueError("结果文件为空")

    for col in ["TNload", "TNconc", "z", "ustar", "fac"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df[["TNload", "TNconc", "z", "ustar", "fac"]].isna().any().any():
        raise ValueError("结果文件中存在 NaN")

    return df


def calc_objectives(df: pd.DataFrame, cstd: float) -> np.ndarray:
    tnload = df["TNload"].to_numpy(dtype=float)
    tnconc = df["TNconc"].to_numpy(dtype=float)
    ustar = df["ustar"].to_numpy(dtype=float)

    J1 = float(np.mean(tnload))
    reliability = float(np.mean(tnconc <= cstd))
    J2 = 1.0 - reliability
    J3 = float(np.mean(np.abs(np.diff(ustar)))) if len(ustar) > 1 else 0.0
    J4 = float(np.mean(np.abs(ustar - 0.75)))

    return np.array([J1, J2, J3, J4], dtype=float)


# =========================================================
# 5) 运行一次 SWAT（独立 worker 目录）
# =========================================================
def run_swat_one_candidate(x: np.ndarray) -> tuple[int, pd.DataFrame]:
    worker_id = WORKER_QUEUE.get()
    worker_dir = WORKER_DIRS[worker_id]

    try:
        job_id = next_job_id()
        cleanup_job_files(worker_dir, job_id)

        a = float(x[0])
        c1, c2, c3 = map(float, x[1:4])
        w1, w2, w3 = map(float, x[4:7])
        r1, r2, r3 = map(float, x[7:10])

        exe_path = os.path.join(worker_dir, EXE_NAME)
        if not os.path.exists(exe_path):
            raise FileNotFoundError(f"未找到可执行文件: {exe_path}")

        cmd = [
            exe_path,
            str(a),
            str(c1), str(c2), str(c3),
            str(w1), str(w2), str(w3),
            str(r1), str(r2), str(r3),
            str(job_id),
        ]

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
# 6) pymoo 问题定义
# =========================================================
class SWATDPSProblem(Problem):
    def __init__(self, n_threads=1):
        super().__init__(
            n_var=10,
            n_obj=4,
            n_ieq_constr=0,
            xl=XL,
            xu=XU
        )
        self.pool = ThreadPool(n_threads)

    def _evaluate(self, X, out, *args, **kwargs):
        def eval_one(x):
            try:
                _, df = run_swat_one_candidate(np.array(x, dtype=float))
                return calc_objectives(df, CSTD)
            except Exception as e:
                print("\n[评估失败] 参数 =", np.array(x, dtype=float))
                print("错误信息：", str(e))
                print(traceback.format_exc())
                return BAD_F

        params = [[X[k]] for k in range(len(X))]
        F = self.pool.starmap(eval_one, params)
        out["F"] = np.array(F, dtype=float)

    def close(self):
        self.pool.close()
        self.pool.join()


# =========================================================
# 7) 主程序
# =========================================================
def main():
    prepare_worker_dirs()

    problem = SWATDPSProblem(n_threads=N_WORKERS)

    try:
        algorithm = NSGA2(
            pop_size=POP_SIZE,
            eliminate_duplicates=True
        )

        res = minimize(
            problem,
            algorithm,
            termination=("n_gen", N_GEN),
            seed=SEED,
            verbose=True,
            save_history=False
        )

        X = np.asarray(res.X, dtype=float)
        F = np.asarray(res.F, dtype=float)

        x_cols = [
            "a", "c1", "c2", "c3",
            "w1", "w2", "w3",
            "r1", "r2", "r3"
        ]
        f_cols = [
            "J1_TNload_mean",
            "J2_1_minus_reliability",
            "J3_smoothness",
            "J4_deviation_intensity"
        ]

        df_x = pd.DataFrame(X, columns=x_cols)
        df_f = pd.DataFrame(F, columns=f_cols)
        df_out = pd.concat([df_x, df_f], axis=1)

        out_csv = os.path.join(BASE_TEMPLATE_DIR, "pareto_solutions_nsga2.csv")
        df_out.to_csv(out_csv, index=False, encoding="utf-8-sig")

        cfg_json = os.path.join(BASE_TEMPLATE_DIR, "nsga2_run_config.json")
        with open(cfg_json, "w", encoding="utf-8") as f:
            json.dump({
                "base_template_dir": BASE_TEMPLATE_DIR,
                "run_root": RUN_ROOT,
                "exe_name": EXE_NAME,
                "cstd_python_only": CSTD,
                "pop_size": POP_SIZE,
                "n_gen": N_GEN,
                "n_workers": N_WORKERS,
                "seed": SEED,
                "xl": XL.tolist(),
                "xu": XU.tolist()
            }, f, ensure_ascii=False, indent=2)

        print("\n优化完成。")
        print(f"Pareto 解已保存到: {out_csv}")
        print(f"运行配置已保存到: {cfg_json}")

    finally:
        problem.close()


if __name__ == "__main__":
    main()