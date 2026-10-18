#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import pandas as pd

input_file = "example.csv"
output_folder = "ecg_subsets"
os.makedirs(output_folder, exist_ok=True)

chunk_size = 100_000
block_size = pd.Timedelta(hours=6)

start_time = None

print("Processing ECG file in chunks...")


# In[2]:


reader = pd.read_csv(
    input_file,
    sep=",",
    comment="#",             # skip metadata lines
    skiprows=1,              # skip the plain header row after comments
    header=None,
    names=["timestamp", "ecg_raw", "ecg_mv"],
    chunksize=chunk_size
)


# In[3]:


for i, chunk in enumerate(reader, start=1):
    print(f"\nProcessing chunk {i}...")

    # Clean possible whitespace
    chunk["timestamp"] = chunk["timestamp"].astype(str).str.strip()
    chunk["ecg_raw"] = pd.to_numeric(chunk["ecg_raw"], errors="coerce")
    chunk["ecg_mv"] = pd.to_numeric(chunk["ecg_mv"], errors="coerce")

    # Parse timestamps using known format
    chunk["continuous_time"] = pd.to_datetime(
        chunk["timestamp"],
        format="%Y-%m-%d %H:%M:%S.%f",
        errors="coerce"
    )
      # Drop bad rows
    chunk = chunk.dropna(subset=["continuous_time", "ecg_raw", "ecg_mv"]).reset_index(drop=True)

    if chunk.empty:
        print("Chunk empty after cleaning, skipping.")
        continue

    if start_time is None:
        start_time = chunk["continuous_time"].iloc[0]

    chunk["elapsed_time"] = chunk["continuous_time"] - start_time
    chunk["block_number"] = (chunk["elapsed_time"] // block_size).astype(int)
    for block_num, subset in chunk.groupby("block_number"):
        start_hour = block_num * 6
        end_hour = start_hour + 6

        output_file = os.path.join(
            output_folder,
            f"ECG_{start_hour:02d}h_to_{end_hour:02d}h.csv"
        )

        subset.to_csv(
            output_file,
            mode="a",
            index=False,
            header=not os.path.exists(output_file)
        )

print("\nDone.")


# In[4]:


summary = []

for f in sorted(os.listdir(output_folder)):
    path = os.path.join(output_folder, f)
    nrows = sum(1 for _ in open(path, "r", encoding="utf-8", errors="ignore")) - 1
    size_mb = os.path.getsize(path) / (1024 * 1024)
    summary.append((f, nrows, size_mb))

summary_df = pd.DataFrame(summary, columns=["file", "rows", "size_mb"])
print(summary_df)


# In[ ]:




