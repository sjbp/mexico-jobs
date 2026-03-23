"""
Build compact JSON for the website from occupations.json + optional scores.json.

Usage:
    python build_site_data.py
"""

import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(BASE, "output", "occupations.json"), encoding="utf-8") as f:
        occupations = json.load(f)

    # Load AI exposure scores if available
    scores_path = os.path.join(BASE, "output", "scores.json")
    scores = {}
    if os.path.exists(scores_path):
        with open(scores_path) as f:
            scores_list = json.load(f)
        scores = {s["sinco_code"]: s for s in scores_list}
        print(f"Loaded {len(scores)} AI exposure scores")
    else:
        print("No scores.json found — AI exposure layer will be empty")

    data = []
    for occ in occupations:
        code = occ["sinco_code"]
        score = scores.get(code, {})

        # Compute annual income from monthly (for comparability)
        monthly = occ.get("median_income_monthly")
        annual = monthly * 12 if monthly else None

        data.append({
            "title": occ["title"],
            "slug": occ["slug"],
            "sinco_code": code,
            "category": occ["category"],
            "category_es": occ["category_es"],
            "pay_monthly": monthly,
            "pay_annual": annual,
            "pay_hourly": occ.get("median_income_hourly"),
            "jobs": occ["jobs"],
            "education": occ["education_mode"],
            "pct_professional": occ.get("pct_professional", 0),
            "formality_rate": occ.get("formality_rate", 0),
            "health_insurance_rate": occ.get("health_insurance_rate", 0),
            "health_protection_index": occ.get("health_protection_index", 0),
            "hours_weekly": occ.get("median_hours_weekly"),
            "exposure": score.get("exposure"),
            "exposure_rationale": score.get("rationale"),
        })

    os.makedirs(os.path.join(BASE, "site"), exist_ok=True)
    with open(os.path.join(BASE, "site", "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    total_jobs = sum(d["jobs"] for d in data if d["jobs"])
    print(f"Wrote {len(data)} occupations to site/data.json")
    print(f"Total jobs: {total_jobs:,}")


if __name__ == "__main__":
    main()
