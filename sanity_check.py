import pandas as pd

# Load raw and aggregated data
df = pd.read_csv("SkillsExploded.csv")
pairs = pd.read_csv("SkillsPairsDetailed.csv")

# Clean columns a bit like in your script
df.columns = [c.strip() for c in df.columns]
pairs.columns = [c.strip() for c in pairs.columns]

# Filter valid data (same as script)
df = df[df["Job ID"].notna() & df["Skill"].notna()]

# Helper: recompute supports inside a segment for one pair
def recompute_supports(row):
    cat = row["Category"]
    jt  = row["Job Type"]
    lvl = row["Experience Level"]
    a   = row["Skill A"]
    b   = row["Skill B"]

    # 1) Filter raw to this segment
    seg = df[
        (df["Category"] == cat) &
        (df["Job Type"] == jt) &
        (df["Experience Level"] == lvl)
    ]

    # 2) Jobs that have A / B in this segment
    jobs_A = set(seg.loc[seg["Skill"] == a, "Job ID"])
    jobs_B = set(seg.loc[seg["Skill"] == b, "Job ID"])

    # 3) Supports
    support_A = len(jobs_A)
    support_B = len(jobs_B)
    support_AB = len(jobs_A & jobs_B)

    return support_A, support_B, support_AB

# Global invariant checks
print("Checking basic invariants...")
bad_rows = pairs[
    (pairs["Support AB"] > pairs["Support A"]) |
    (pairs["Support AB"] > pairs["Support B"])
]
print(f"Invariants violations (Support AB > Support A/B): {len(bad_rows)}")

# Random sample of pairs to verify in detail
sample_size = 20  # you can increase later
sample = pairs.sample(n=sample_size, random_state=42)

mismatches = []

for idx, row in sample.iterrows():
    SA_calc, SB_calc, SAB_calc = recompute_supports(row)

    SA_stored = row["Support A"]
    SB_stored = row["Support B"]
    SAB_stored = row["Support AB"]
    JC_stored = row["Jobs_Count"]

    if (
        SA_calc != SA_stored or
        SB_calc != SB_stored or
        SAB_calc != SAB_stored or
        SAB_calc != JC_stored
    ):
        mismatches.append({
            "idx": idx,
            "Category": row["Category"],
            "Job Type": row["Job Type"],
            "Experience Level": row["Experience Level"],
            "Skill A": row["Skill A"],
            "Skill B": row["Skill B"],
            "Support A stored": SA_stored,
            "Support A calc": SA_calc,
            "Support B stored": SB_stored,
            "Support B calc": SB_calc,
            "Support AB stored": SAB_stored,
            "Support AB calc": SAB_calc,
            "Jobs_Count stored": JC_stored,
        })

print(f"\nChecked {sample_size} random pairs.")
print(f"Mismatches found: {len(mismatches)}")

if mismatches:
    print("First few mismatches:")
    for m in mismatches[:5]:
        print(m)
