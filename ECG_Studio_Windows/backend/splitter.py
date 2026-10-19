"""Preserves the supplied pandas reader, transformations and six-hour grouping."""
from pathlib import Path
import pandas as pd


def split_ecg(input_file, output_folder, progress=lambda **kw: None):
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=False)
    start_time = None
    read_rows = valid_rows = 0
    counts = {}
    reader = pd.read_csv(input_file, sep=",", comment="#", skiprows=1,
                         header=None, names=["timestamp", "ecg_raw", "ecg_mv"],
                         chunksize=100_000)
    with reader:
        for i, chunk in enumerate(reader, start=1):
            read_rows += len(chunk)
            chunk["timestamp"] = chunk["timestamp"].astype(str).str.strip()
            chunk["ecg_raw"] = pd.to_numeric(chunk["ecg_raw"], errors="coerce")
            chunk["ecg_mv"] = pd.to_numeric(chunk["ecg_mv"], errors="coerce")
            chunk["continuous_time"] = pd.to_datetime(chunk["timestamp"],
                format="%Y-%m-%d %H:%M:%S.%f", errors="coerce")
            chunk = chunk.dropna(subset=["continuous_time", "ecg_raw", "ecg_mv"]).reset_index(drop=True)
            valid_rows += len(chunk)
            if not chunk.empty:
                if start_time is None:
                    start_time = chunk["continuous_time"].iloc[0]
                chunk["elapsed_time"] = chunk["continuous_time"] - start_time
                chunk["block_number"] = (chunk["elapsed_time"] // pd.Timedelta(hours=6)).astype(int)
                for block_num, subset in chunk.groupby("block_number"):
                    start_hour = block_num * 6
                    name = f"ECG_{start_hour:02d}h_to_{start_hour + 6:02d}h.csv"
                    output_file = output_folder / name
                    subset.to_csv(output_file, mode="a", index=False, header=not output_file.exists())
                    counts[name] = counts.get(name, 0) + len(subset)
            progress(chunks=i, read_rows=read_rows, valid_rows=valid_rows,
                     discarded_rows=read_rows-valid_rows)
    return {"read_rows": read_rows, "valid_rows": valid_rows,
            "discarded_rows": read_rows-valid_rows,
            "outputs": [{"name": n, "rows": counts[n], "bytes": (output_folder/n).stat().st_size}
                        for n in sorted(counts)]}
