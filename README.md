# SWAT-DPS-NSGA2

SWAT-DPS-NSGA2 provides method code for coupling a modified SWAT2016 Rev.664 source code with NSGA-II to optimize dynamic point-source nitrogen control strategies.

The repository follows a compact research-code layout: optimization scripts are placed at the repository root, and the corresponding modified SWAT source-code versions are placed under `swat_source/`.

## Repository structure

```text
SWAT-DPS-NSGA2/
├─ README.md
├─ requirements.txt
├─ costtime.txt
├─ swat_nsga2_dps_b1.py
├─ swat_nsga2_dps_b3.py
├─ swat_nsga2_dps_b4.py
├─ swat_nsga2_ndb.py
├─ swat_source/
│  ├─ dps_b1/
│  ├─ dps_b3/
│  ├─ dps_b4/
│  └─ ndb/
└─ RawData/
   ├─ TxtInOutB=1/
   ├─ TxtInOutB=3/
   ├─ TxtInOutB=4/
   └─ TxtInOutbase10000/
```

## Optimization scripts

- `swat_nsga2_dps_b1.py`: DPS-B1 optimization script.
- `swat_nsga2_dps_b3.py`: DPS-B3 optimization script.
- `swat_nsga2_dps_b4.py`: DPS-B4 optimization script.
- `swat_nsga2_ndb.py`: non-feedback direct benchmark optimization script.

Each script runs NSGA-II, calls a corresponding modified SWAT executable, reads `*_dps_eval.out`, evaluates objectives and constraints, and writes Pareto solutions and convergence records.

## Modified SWAT source code

The `swat_source/` directory contains four modified SWAT source-code versions:

- `swat_source/dps_b1/`: one-dimensional DPS feedback version.
- `swat_source/dps_b3/`: three-dimensional DPS feedback version.
- `swat_source/dps_b4/`: four-dimensional DPS feedback version.
- `swat_source/ndb/`: non-feedback direct-control benchmark version.

Compared with native SWAT2016 Rev.664, these versions add command-line control inputs, annual DPS state extraction, dynamic point-source nitrogen-load updates, and `*_dps_eval.out` output for optimization.

## Raw data (SWAT TxtInOut projects)

The `RawData/` directory contains the four complete SWAT `TxtInOut` input projects used by the optimization scripts, one per control strategy:

- `RawData/TxtInOutB=1/`: input project for the one-dimensional DPS strategy (DPS-B1, ~6,590 files).
- `RawData/TxtInOutB=3/`: input project for the three-dimensional DPS strategy (DPS-B3, ~6,597 files).
- `RawData/TxtInOutB=4/`: input project for the four-dimensional DPS strategy (DPS-B4, ~6,600 files).
- `RawData/TxtInOutbase10000/`: input project for the non-feedback direct-control benchmark (`ndb`, ~6,592 files).

Each folder is a standard ArcSWAT-generated `TxtInOut` working directory containing the full set of SWAT input files (`.sub`, `.hru`, `.mgt`, `.sol`, `.gw`, `.rte`, `.chm`, `.pnd`, `.wgn`, `.wus`, weather data, `file.cio`, etc.). The watershed was delineated with the ArcGIS-SWAT interface; simulations run for 33 years starting in 2005 at a daily time step (`NBYR = 33`, `IYR = 2005`, measured precipitation).

To run an optimization, point the script's `BASE_TEMPLATE_DIR` to the matching folder, e.g.:

```python
BASE_TEMPLATE_DIR = r"RawData/TxtInOutB=1"   # for swat_nsga2_dps_b1.py
```

Compiled SWAT executables, model output files (`*.out`), Pareto results, and NSGA-II run configs inside these folders are intentionally excluded from version control (see `.gitignore`); only the model inputs are tracked.

## Installation

Python 3.9 is recommended (tested with Python 3.9.25).

```bash
pip install -r requirements.txt
```

A Fortran compiler is required to build the modified SWAT source code. After compiling the corresponding SWAT executable, place it in the SWAT `TxtInOut` working directory expected by the Python script.

## Usage

Before running, edit the user settings near the top of each optimization script, especially:

```python
BASE_TEMPLATE_DIR = r"path_to_your_TxtInOut_directory"
POP_SIZE = 100
N_GEN = 1000
N_WORKERS = 12
```

Then run one strategy, for example:

```bash
python swat_nsga2_dps_b1.py
python swat_nsga2_dps_b3.py
python swat_nsga2_dps_b4.py
python swat_nsga2_ndb.py
```

## Main outputs

The scripts write outputs to the configured SWAT working directory, including files such as:

- `pareto_solutions_nsga2.csv`
- `pareto_solutions_nsga2_66.csv`
- `pareto_solutions_nsga2_92param.csv`
- `pareto_solutions_nsga2_direct_uk_29x3.csv`
- `convergence_history*.csv`
- `nsga2_run_config*.json`
- `*_dps_eval.out`

Generated worker folders, logs, executables, and result files are intentionally excluded from version control.

## Notes

This repository is a method-code release together with the raw SWAT input projects used in the study (see `RawData/`).  Update the paths in the optimization scripts before running.
