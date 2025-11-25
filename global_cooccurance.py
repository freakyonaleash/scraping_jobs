import pandas as pd
from itertools import combinations

INPUT_FILE = "SkillsExploded.csv"
OUTPUT_FILE = "SkillsPairsGlobal.csv"

# --------------------------------------------------
# Load and clean data
# --------------------------------------------------
df = pd.read_csv(INPUT_FILE)
df.columns = [c.strip() for c in df.columns]

df = df.rename(columns={
    "Job ID": "job_id",
    "Skill": "skill",
    "Job Type": "job_type",
    "Budget Avg": "budget",
})

# keep only valid rows
df = df[df["job_id"].notna() & df["skill"].notna()].copy()
df["budget"] = pd.to_numeric(df["budget"], errors="coerce")
df["job_type"] = df["job_type"].str.lower().fillna("")
df["job_id"] = df["job_id"].astype(str)

# one set of skills per job
skill_groups = (
    df.groupby("job_id")["skill"]
      .apply(lambda s: sorted(set(s)))
)

# --------------------------------------------------
# Build pair rows per job, with correct job counts
# --------------------------------------------------
pair_records = []

for job_id, skills in skill_groups.items():
    if len(skills) < 2:
        continue

    job_rows = df[df["job_id"] == job_id]

    is_hourly = (job_rows["job_type"] == "hourly").any()
    is_fixed  = (job_rows["job_type"] == "fixed").any()

    hourly_budgets = job_rows[job_rows["job_type"] == "hourly"]["budget"].dropna()
    fixed_budgets  = job_rows[job_rows["job_type"] == "fixed"]["budget"].dropna()

    hourly_avg = hourly_budgets.mean()   if not hourly_budgets.empty else None
    hourly_med = hourly_budgets.median() if not hourly_budgets.empty else None
    fixed_avg  = fixed_budgets.mean()    if not fixed_budgets.empty else None
    fixed_med  = fixed_budgets.median()  if not fixed_budgets.empty else None

    for a, b in combinations(skills, 2):
        pair_records.append({
            "Skill A": a,
            "Skill B": b,
            # per job indicators
            "Hourly_Jobs": 1 if is_hourly else 0,
            "Fixed_Jobs":  1 if is_fixed  else 0,
            # per job budget stats
            "Hourly_Avg":    hourly_avg,
            "Hourly_Median": hourly_med,
            "Fixed_Avg":     fixed_avg,
            "Fixed_Median":  fixed_med,
            "job_id": job_id,
        })

pairs = pd.DataFrame(pair_records)

# --------------------------------------------------
# Global supports A, B, AB
# --------------------------------------------------
support_A = (
    df.groupby("skill")["job_id"]
      .nunique()
      .rename("Support A")
)

support_B = support_A.rename("Support B")

support_AB = (
    pairs.groupby(["Skill A", "Skill B"])["job_id"]
         .nunique()
         .rename("Support AB")
)

total_jobs = df["job_id"].nunique()

# --------------------------------------------------
# Association metrics: confidence, lift, jaccard
# --------------------------------------------------
stats = support_AB.reset_index()
stats = stats.merge(support_A, left_on="Skill A", right_index=True)
stats = stats.merge(support_B, left_on="Skill B", right_index=True)

stats["Confidence A→B"] = stats["Support AB"] / stats["Support A"]
stats["Confidence B→A"] = stats["Support AB"] / stats["Support B"]

stats["Lift"] = (
    stats["Support AB"] * total_jobs /
    (stats["Support A"] * stats["Support B"])
)

stats["Jaccard"] = (
    stats["Support AB"] /
    (stats["Support A"] + stats["Support B"] - stats["Support AB"])
)

# --------------------------------------------------
# Aggregate budget stats per pair
# --------------------------------------------------
budget_stats = (
    pairs.groupby(["Skill A", "Skill B"])
         .agg({
             "Hourly_Jobs":   "sum",
             "Fixed_Jobs":    "sum",
             "Hourly_Avg":    "mean",
             "Hourly_Median": "median",
             "Fixed_Avg":     "mean",
             "Fixed_Median":  "median",
         })
         .reset_index()
)

final = stats.merge(budget_stats, on=["Skill A", "Skill B"], how="left")
final = final.sort_values("Support AB", ascending=False)

final.to_csv(OUTPUT_FILE, index=False)
print(f"✔ Global co-occurrence created: {OUTPUT_FILE}")





