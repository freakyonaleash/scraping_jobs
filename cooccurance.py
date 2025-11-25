import pandas as pd
import itertools
import numpy as np

# === Configuration ===
INPUT_FILE = "SkillsExploded.csv"
OUTPUT_FILE = "SkillsPairsDetailed.csv"

# === Load data ===
df = pd.read_csv(INPUT_FILE)
df.columns = [c.strip() for c in df.columns]

# Filter valid data
df = df[df["Job ID"].notna() & df["Skill"].notna()]
df["Budget Avg"] = pd.to_numeric(df["Budget Avg"], errors="coerce")
df["Skill"] = df["Skill"].astype(str).str.strip()

# === Segmentation columns (WITHOUT country) ===
seg_cols = [
    "Category",
    "Job Type",
    "Experience Level"
]

# === Build job records ===
# IMPORTANT: group by (Job ID, Category, Job Type, Experience Level)
# So the same Job ID in multiple segments is treated as multiple jobs.
def job_info(group):
    return {
        "skills": sorted(set(group["Skill"].dropna())),
        "budget_avg": group["Budget Avg"].mean(),
        "budget_median": group["Budget Avg"].median(),
        "category": group["Category"].iloc[0],
        "job_type": group["Job Type"].iloc[0],
        "experience": group["Experience Level"].iloc[0]
    }

jobs = (
    df.groupby(["Job ID", "Category", "Job Type", "Experience Level"])
      .apply(job_info)
      .to_dict()
)

# === Build canonical job+skill table for supports ===
job_skill_rows = []
for (job_id, category, job_type, experience), info in jobs.items():
    for s in info["skills"]:
        job_skill_rows.append({
            "Job ID": job_id,
            "Skill": s,
            "Category": info["category"],
            "Job Type": info["job_type"],
            "Experience Level": info["experience"],
        })

job_skills_df = pd.DataFrame(job_skill_rows)

# === Generate pairs per (Job ID, Category, Job Type, Experience) job ===
rows = []
for (job_id, category, job_type, experience), info in jobs.items():
    skills = info["skills"]
    if len(skills) < 2:
        continue
    for a, b in itertools.combinations(skills, 2):
        rows.append({
            "Skill A": a,
            "Skill B": b,
            "Category": info["category"],
            "Job Type": info["job_type"],
            "Experience Level": info["experience"],
            "Budget Avg": info["budget_avg"],
            "Budget Median": info["budget_median"]
        })

pairs_df = pd.DataFrame(rows)

# === SEGMENTED AGGREGATION (Category + Job Type + Experience) ===
agg = pairs_df.groupby(
    seg_cols + ["Skill A", "Skill B"]
).agg(
    Jobs_Count=("Skill A", "count"),
    Avg_Budget=("Budget Avg", "mean"),
    Median_Budget=("Budget Median", "median"),
    Min_Budget=("Budget Avg", "min"),
    Max_Budget=("Budget Avg", "max")
).reset_index()

# === SEGMENTED SUPPORTS & METRICS (all inside same segment) ===

# 1) Support for single skills inside each segment (from canonical job_skills_df)
skill_seg_counts = (
    job_skills_df
    .groupby(seg_cols + ["Skill"])["Job ID"]
    .nunique()
    .reset_index()
)

# For Skill A
supportA = skill_seg_counts.rename(
    columns={"Skill": "Skill A", "Job ID": "Support A"}
)
agg = agg.merge(
    supportA,
    on=seg_cols + ["Skill A"],
    how="left"
)

# For Skill B
supportB = skill_seg_counts.rename(
    columns={"Skill": "Skill B", "Job ID": "Support B"}
)
agg = agg.merge(
    supportB,
    on=seg_cols + ["Skill B"],
    how="left"
)

# 2) Support AB inside the segment
agg["Support AB"] = agg["Jobs_Count"]

# 3) Total jobs per segment (for Lift), from canonical job_skills_df
seg_total_jobs = (
    job_skills_df.groupby(seg_cols)["Job ID"]
    .nunique()
    .to_dict()
)

seg_keys = agg[seg_cols].apply(tuple, axis=1)
seg_totals_series = seg_keys.map(seg_total_jobs)

# 4) Confidence, Lift, Jaccard (all segmented, consistent)
agg["Confidence A→B"] = agg["Support AB"] / agg["Support A"]
agg["Confidence B→A"] = agg["Support AB"] / agg["Support B"]

agg["Lift"] = (
    agg["Support AB"] * seg_totals_series
    / (agg["Support A"] * agg["Support B"])
)

agg["Jaccard"] = agg["Support AB"] / (
    agg["Support A"] + agg["Support B"] - agg["Support AB"]
)

# === Save output ===
agg = agg.sort_values("Jobs_Count", ascending=False)
agg.to_csv(OUTPUT_FILE, index=False)

print(f"✅ Saved {len(agg)} segmented skill pairs to {OUTPUT_FILE}")





