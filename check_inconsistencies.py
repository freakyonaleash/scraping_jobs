import pandas as pd

INPUT_FILE = "SkillsExploded.csv"

# Load data
df = pd.read_csv(INPUT_FILE)
df.columns = [c.strip() for c in df.columns]

# Keep only valid rows
df = df[df["Job ID"].notna() & df["Skill"].notna()].copy()

# Basic cleaning for text fields
for col in ["Skill", "Category", "Job Type", "Experience Level", "Country Normalized"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

# Columns that define your segment
seg_cols = ["Category", "Job Type", "Experience Level"]

# 1. Detect Job IDs that belong to multiple categories or levels or job types
meta = (
    df.groupby("Job ID")[seg_cols]
      .nunique()
)

problem_jobs = meta[
    (meta["Category"] > 1) |
    (meta["Job Type"] > 1) |
    (meta["Experience Level"] > 1)
]

print(f"Jobs with inconsistent segment info: {len(problem_jobs)}")

# 2. Detailed view: all raw rows for those Job IDs
detailed = df[df["Job ID"].isin(problem_jobs.index)].copy()
detailed = detailed.sort_values(
    ["Job ID", "Category", "Job Type", "Experience Level", "Skill"]
)

detailed.to_csv("InconsistentJobs_detailed.csv", index=False)
print("Saved detailed rows to InconsistentJobs_detailed.csv")

# 3. Compact summary: one row per Job ID and Skill with lists of values
def unique_join(series):
    vals = sorted(set(series.dropna()))
    return ", ".join(vals)

summary = (
    detailed
    .groupby(["Job ID", "Skill"])
    .agg(
        Categories=("Category", unique_join),
        Job_Types=("Job Type", unique_join),
        Experience_Levels=("Experience Level", unique_join),
        Countries=("Country Normalized", unique_join) if "Country Normalized" in df.columns else ("Category", lambda s: "")
    )
    .reset_index()
)

summary = summary.sort_values(["Job ID", "Skill"])
summary.to_csv("InconsistentJobs_summary.csv", index=False)
print("Saved summary to InconsistentJobs_summary.csv")
