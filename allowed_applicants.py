import csv
from country_map import country_map

INPUT_FILE = "RawData.csv"
OUTPUT_FILE = "AllowedApplicantsExploded.csv"


def parse_budget(budget_raw):
    """Return avg budget."""
    if not budget_raw:
        return ""

    s = str(budget_raw)
    if "-" in s:
        parts = s.split("-")
        try:
            low = float(parts[0].replace("$", "").strip())
            high = float(parts[1].replace("$", "").strip())
            return (low + high) / 2
        except:
            return ""
    else:
        try:
            return float(s.replace("$", "").strip())
        except:
            return ""


def normalize_country(raw):
    """Normalize country using country_map."""
    if not raw:
        return ""
    key = raw.strip().upper()
    return country_map.get(key, raw.strip())


def main():
    # Load RawData.csv
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    headers = reader.fieldnames

    # Detect unlimited allowed countries columns
    allowed_cols = [h for h in headers if h.startswith("allowedApplicantCountries")]

    output = []

    # Header similar to skills exploded, now includes Budget Avg
    output_header = [
        "Category",
        "Job ID",
        "Sub ID",
        "Budget Avg",
        "Country Normalized",   # client's normalized country
        "Absolute Date",
        "Job Type",
        "Experience Level",
        "Allowed Applicant Country"
    ]

    output.append(output_header)

    for row in rows:
        # Extract shared fields
        category = row.get("category", "")
        job_id = row.get("id", "")
        sub_id = row.get("subId", "")
        client_location = row.get("clientLocation", "")
        norm_country = normalize_country(client_location)
        abs_date = row.get("absoluteDate", "")
        job_type = row.get("jobType", "")
        exp_level = row.get("experienceLevel", "")

        # Budget Avg
        budget_raw = row.get("budget", "")
        bavg = parse_budget(budget_raw)

        # Collect allowed applicant countries
        allowed_list = [
            row[c].strip()
            for c in allowed_cols
            if row.get(c, "").strip() != ""
        ]

        # Create exploded rows
        for allowed_country in allowed_list:
            output.append([
                category,
                job_id,
                sub_id,
                bavg,
                norm_country,
                abs_date,
                job_type,
                exp_level,
                allowed_country
            ])

    # Write output CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(output)

    print("Allowed Applicant Countries exploded.")
    print(f"Wrote: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

