import csv
from country_map import country_map


INPUT_FILE = "RawData.csv"
OUTPUT_CLEAN = "CleanData.csv"
OUTPUT_SKILLS = "SkillsExploded.csv"


def parse_budget(budget_raw):
    """Return (min, max, avg) budget values."""
    if not budget_raw:
        return "", "", ""

    s = str(budget_raw)
    if "-" in s:
        parts = s.split("-")
        try:
            low = float(parts[0].replace("$", "").strip())
            high = float(parts[1].replace("$", "").strip())
            return low, high, (low + high) / 2
        except:
            return "", "", ""
    else:
        try:
            val = float(s.replace("$", "").strip())
            return val, val, val
        except:
            return "", "", ""


def normalize_country(raw):
    """Normalize country using country_map."""
    if not raw:
        return ""
    key = raw.strip().upper()
    return country_map.get(key, raw.strip())


def main():
    # Load RawData.csv safely
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    headers = reader.fieldnames

    # Dynamic columns
    allowed_cols = [h for h in headers if h.startswith("allowedApplicantCountries")]
    tag_cols = [h for h in headers if h.startswith("tags/")]

    # Prepare outputs
    clean_header = [
        "Category", "Job ID", "Sub ID", "URL", "Title", "Description",
        "Budget Min", "Budget Max", "Budget Avg",
        "Client Location", "Country Normalized",
        "Payment Verified", "Relative Date", "Absolute Date",
        "Job Type", "Experience Level",
        "Allowed Applicant Countries", "Skills"
    ]

    skills_header = [
        "Category", "Job ID", "Sub ID", "Budget Avg",
        "Country Normalized", "Absolute Date",
        "Job Type", "Experience Level", "Skill"
    ]

    clean_output = [clean_header]
    skills_output = [skills_header]

    # Process each row
    for row in rows:
        category = row.get("category", "")
        job_id = row.get("id", "")
        sub_id = row.get("subId", "")
        url = row.get("url", "")
        title = row.get("title", "")
        desc = row.get("description", "")
        budget_raw = row.get("budget", "")
        payment_verified = row.get("paymentVerified", "")
        rel_date = row.get("relativeDate", "")
        abs_date = row.get("absoluteDate", "")
        job_type = row.get("jobType", "")
        exp_level = row.get("experienceLevel", "")
        client_location = row.get("clientLocation", "")

        # Budget parsing
        bmin, bmax, bavg = parse_budget(budget_raw)

        # Country
        norm_country = normalize_country(client_location)

        # Allowed countries
        allowed_list = [row[c].strip() for c in allowed_cols if row.get(c, "").strip() != ""]
        allowed_str = ", ".join(allowed_list)

        # Tags
        tag_list = [row[c].strip() for c in tag_cols if row.get(c, "").strip() != ""]
        tag_str = ", ".join(tag_list)

        # Add CleanData row
        clean_output.append([
            category, job_id, sub_id, url, title, desc,
            bmin, bmax, bavg,
            client_location, norm_country,
            payment_verified, rel_date, abs_date,
            job_type, exp_level,
            allowed_str, tag_str
        ])

        # Add SkillsExploded rows
        for skill in tag_list:
            skills_output.append([
                category, job_id, sub_id, bavg,
                norm_country, abs_date,
                job_type, exp_level,
                skill
            ])

    # Write CleanData
    with open(OUTPUT_CLEAN, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(clean_output)

    # Write SkillsExploded
    with open(OUTPUT_SKILLS, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(skills_output)

    print("Processing complete.")
    print(f"Wrote: {OUTPUT_CLEAN}")
    print(f"Wrote: {OUTPUT_SKILLS}")


if __name__ == "__main__":
    main()
