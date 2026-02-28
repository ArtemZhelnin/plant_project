from dataclasses import dataclass
from typing import Dict, List

import numpy as np


@dataclass(frozen=True)
class ScaleStats:
    mean: float
    std: float
    min: float
    max: float
    relative_std_percent: float
    n: int


def compute_stats(values: List[float]) -> ScaleStats:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        raise ValueError("No values for stats")

    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0

    rel = float((std / mean) * 100.0) if mean != 0 else 0.0

    return ScaleStats(
        mean=mean,
        std=std,
        min=float(np.min(arr)),
        max=float(np.max(arr)),
        relative_std_percent=rel,
        n=int(arr.size),
    )


def filter_outliers(values: List[float], z: float = 2.0) -> Dict[str, object]:
    """Filter outliers using |x-mean| > z*std."""
    if len(values) == 0:
        return {"kept_idx": [], "dropped_idx": [], "values_kept": []}

    st = compute_stats(values)
    if st.std == 0:
        return {"kept_idx": list(range(len(values))), "dropped_idx": [], "values_kept": list(values)}

    kept_idx: List[int] = []
    dropped_idx: List[int] = []
    kept: List[float] = []

    for i, v in enumerate(values):
        if abs(v - st.mean) > z * st.std:
            dropped_idx.append(i)
        else:
            kept_idx.append(i)
            kept.append(v)

    return {"kept_idx": kept_idx, "dropped_idx": dropped_idx, "values_kept": kept}


def to_dict(st: ScaleStats) -> Dict[str, float]:
    return {
        "mean": st.mean,
        "std": st.std,
        "min": st.min,
        "max": st.max,
        "relative_std_percent": st.relative_std_percent,
        "n": st.n,
    }
