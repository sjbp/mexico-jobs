"""
Process ENOE 2024 Q4 microdata into occupation-level statistics.

Reads SDEM (sociodemographic) and COE1 (employment conditions) tables,
joins them, applies survey weights, and computes per-occupation:
- Total employment (weighted)
- Median monthly income
- Median hourly income
- Mode education level
- Formality rate

Outputs: occupations.csv and occupations.json
"""

import csv
import json
import os
from collections import defaultdict
import statistics

# Paths
BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data", "enoe", "enoe_2024_4t")
SDEM_CSV = os.path.join(DATA, "conjunto_de_datos_sdem_enoe_2024_4t", "conjunto_de_datos", "conjunto_de_datos_sdem_enoe_2024_4t.csv")
COE1_CSV = os.path.join(DATA, "conjunto_de_datos_coe1_enoe_2024_4t", "conjunto_de_datos", "conjunto_de_datos_coe1_enoe_2024_4t.csv")
SINCO_CSV = os.path.join(DATA, "conjunto_de_datos_coe1_enoe_2024_4t", "catalogos", "p3.csv")

# SINCO major division names (first digit)
SINCO_DIVISIONS = {
    "1": "Funcionarios, directores y jefes",
    "2": "Profesionistas y técnicos",
    "3": "Trabajadores auxiliares en actividades administrativas",
    "4": "Comerciantes, empleados en ventas y agentes de ventas",
    "5": "Trabajadores en servicios personales y vigilancia",
    "6": "Trabajadores en actividades agrícolas, ganaderas, forestales, caza y pesca",
    "7": "Trabajadores artesanales",
    "8": "Operadores de maquinaria industrial, ensambladores, choferes y conductores de transporte",
    "9": "Trabajadores en actividades elementales y de apoyo",
}

# Short category names for the treemap (English for the viz, matching Karpathy style)
SINCO_CATEGORIES = {
    "1": "management",
    "2": "professional-technical",
    "3": "administrative-support",
    "4": "sales",
    "5": "personal-services",
    "6": "agriculture",
    "7": "crafts-trades",
    "8": "operators-drivers",
    "9": "elementary-support",
}

SINCO_CATEGORIES_ES = {
    "1": "Funcionarios y directivos",
    "2": "Profesionistas y técnicos",
    "3": "Auxiliares administrativos",
    "4": "Comerciantes y ventas",
    "5": "Servicios personales y vigilancia",
    "6": "Agropecuario y pesca",
    "7": "Artesanos y oficios",
    "8": "Operadores y conductores",
    "9": "Actividades elementales",
}

# Education levels from cs_p13_1
EDU_LABELS = {
    "0": "Ninguno",
    "1": "Preescolar",
    "2": "Primaria",
    "3": "Secundaria",
    "4": "Preparatoria o bachillerato",
    "5": "Normal",
    "6": "Carrera técnica",
    "7": "Profesional",
    "8": "Maestría",
    "9": "Doctorado",
    "99": "No especificado",
}

# Simplified education levels for the viz
EDU_SIMPLIFIED = {
    "0": "Sin escolaridad",
    "1": "Sin escolaridad",
    "2": "Primaria",
    "3": "Secundaria",
    "4": "Preparatoria",
    "5": "Normal/Técnica",
    "6": "Normal/Técnica",
    "7": "Profesional (licenciatura)",
    "8": "Maestría",
    "9": "Doctorado",
    "99": "No especificado",
}


def make_person_key(row):
    """Create a unique person key for joining SDEM and COE1."""
    return (
        row.get("cd_a", "").strip(),
        row.get("ent", "").strip(),
        row.get("con", "").strip(),
        row.get("upm", "").strip(),
        row.get("d_sem", "").strip(),
        row.get("n_pro_viv", "").strip(),
        row.get("v_sel", "").strip(),
        row.get("n_hog", "").strip(),
        row.get("h_mud", "").strip(),
        row.get("n_ent", "").strip(),
        row.get("n_ren", "").strip(),
    )


def load_sinco_catalog():
    """Load SINCO 4-digit occupation codes and descriptions."""
    catalog = {}
    with open(SINCO_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["CVE"].strip()
            desc = row["DESCRIP"].strip()
            if len(code) == 4:
                catalog[code] = desc
    return catalog


def main():
    print("Loading SINCO catalog...")
    sinco = load_sinco_catalog()
    print(f"  {len(sinco)} occupation codes loaded")

    # Load COE1 to get SINCO codes per person
    print("Loading COE1 (employment conditions)...")
    person_sinco = {}
    coe1_count = 0
    with open(COE1_CSV, encoding="latin-1") as f:
        reader = csv.DictReader(f)
        for row in reader:
            coe1_count += 1
            p3 = row.get("p3", "").strip()
            if len(p3) == 4 and p3 != "9999":
                key = make_person_key(row)
                person_sinco[key] = p3
    print(f"  {coe1_count} COE1 records, {len(person_sinco)} with valid SINCO codes")

    # Process SDEM with occupation codes from COE1
    print("Processing SDEM (sociodemographic)...")
    # Per occupation: collect weighted employment, incomes, education
    occ_data = defaultdict(lambda: {
        "weighted_employment": 0,
        "incomes": [],  # (income, weight) pairs for weighted median
        "hourly_incomes": [],
        "education_counts": defaultdict(float),  # weighted counts
        "formal_count": 0,
        "informal_count": 0,
        "hours_worked": [],
        "health_access_count": 0,
        "health_no_access_count": 0,
        "health_protection_score_sum": 0,  # weighted sum of per-person scores
        "health_protection_weight": 0,     # total weight for health scoring
    })

    sdem_count = 0
    matched = 0
    with open(SDEM_CSV, encoding="latin-1") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sdem_count += 1
            key = make_person_key(row)

            # Only process employed people (clase1=1 means PEA, clase2=1 means employed)
            clase1 = row.get("clase1", "").strip()
            clase2 = row.get("clase2", "").strip()
            if clase1 != "1" or clase2 != "1":
                continue

            sinco_code = person_sinco.get(key)
            if not sinco_code:
                continue

            matched += 1
            weight = float(row.get("fac_tri", "0").strip() or "0")
            if weight <= 0:
                continue

            occ = occ_data[sinco_code]
            occ["weighted_employment"] += weight

            # Monthly income
            ingocup = row.get("ingocup", "").strip()
            if ingocup and ingocup not in ("", "0", "999998", "999999"):
                try:
                    income = float(ingocup)
                    if 0 < income < 999998:
                        occ["incomes"].append((income, weight))
                except ValueError:
                    pass

            # Hourly income
            ing_x_hrs = row.get("ing_x_hrs", "").strip()
            if ing_x_hrs and ing_x_hrs not in ("", "0"):
                try:
                    hourly = float(ing_x_hrs)
                    if 0 < hourly < 99999:
                        occ["hourly_incomes"].append((hourly, weight))
                except ValueError:
                    pass

            # Education (cs_p13_1 is detailed level)
            edu = row.get("cs_p13_1", "").strip()
            if edu in EDU_SIMPLIFIED:
                occ["education_counts"][edu] += weight

            # Hours worked
            hrsocup = row.get("hrsocup", "").strip()
            if hrsocup and hrsocup not in ("", "0"):
                try:
                    hrs = float(hrsocup)
                    if 0 < hrs <= 168:
                        occ["hours_worked"].append((hrs, weight))
                except ValueError:
                    pass

            # Formality (emp_ppal: 1=informal, 2=formal)
            # NOTE: ENOE emp_ppal coding is 1=informal, 2=formal.
            # Initially coded as 1=formal which produced inverted results
            # (e.g. domestic workers showing 95% formal). Swapped 2024-03-23.
            formality = row.get("emp_ppal", "").strip()
            if formality == "2":
                occ["formal_count"] += weight
            elif formality == "1":
                occ["informal_count"] += weight

            # Health insurance access (seg_soc: 1=with access, 2=without)
            seg_soc = row.get("seg_soc", "").strip()
            if seg_soc == "1":
                occ["health_access_count"] += weight
            elif seg_soc == "2":
                occ["health_no_access_count"] += weight

            # Health Protection Index (medica5c-based composite score)
            # medica5c: 1=no benefits, 2=health only, 3=health+other, 4=other but no health, 5=NE
            # Scores: 3→100, 2→70, 4→20, 1→0
            medica5c = row.get("medica5c", "").strip()
            health_scores = {"3": 100, "2": 70, "4": 20, "1": 0}
            if medica5c in health_scores:
                occ["health_protection_score_sum"] += health_scores[medica5c] * weight
                occ["health_protection_weight"] += weight

    print(f"  {sdem_count} SDEM records, {matched} matched to occupations")

    # Compute statistics per occupation
    print("Computing occupation statistics...")
    results = []
    for code in sorted(occ_data.keys()):
        occ = occ_data[code]
        if occ["weighted_employment"] < 1000:  # Skip tiny occupations
            continue

        name = sinco.get(code, f"Ocupación {code}")
        category = SINCO_CATEGORIES.get(code[0], "other")
        category_es = SINCO_CATEGORIES_ES.get(code[0], "Otro")
        division_es = SINCO_DIVISIONS.get(code[0], "Otro")

        # Weighted median income
        median_income = weighted_median(occ["incomes"])
        median_hourly = weighted_median(occ["hourly_incomes"])
        median_hours = weighted_median(occ["hours_worked"])

        # Mode education level (highest weighted count)
        edu_counts = occ["education_counts"]
        if edu_counts:
            mode_edu_code = max(edu_counts, key=edu_counts.get)
            mode_edu = EDU_SIMPLIFIED.get(mode_edu_code, "No especificado")
            # Also compute % with professional degree or higher
            higher_ed_weight = sum(
                edu_counts.get(e, 0) for e in ("7", "8", "9")
            )
            total_edu_weight = sum(edu_counts.values())
            pct_professional = (
                higher_ed_weight / total_edu_weight * 100
                if total_edu_weight > 0
                else 0
            )
        else:
            mode_edu = "No especificado"
            pct_professional = 0

        # Formality rate
        total_formal = occ["formal_count"] + occ["informal_count"]
        formality_rate = (
            occ["formal_count"] / total_formal * 100 if total_formal > 0 else 0
        )

        # Health insurance access rate
        total_health = occ["health_access_count"] + occ["health_no_access_count"]
        health_rate = (
            occ["health_access_count"] / total_health * 100 if total_health > 0 else 0
        )

        # Health Protection Index (0-100 composite score)
        health_protection_index = (
            occ["health_protection_score_sum"] / occ["health_protection_weight"]
            if occ["health_protection_weight"] > 0 else 0
        )

        # Slug for the occupation
        slug = f"sinco-{code}"

        results.append({
            "sinco_code": code,
            "title": name,
            "slug": slug,
            "category": category,
            "category_es": category_es,
            "division_es": division_es,
            "jobs": round(occ["weighted_employment"]),
            "median_income_monthly": round(median_income) if median_income else None,
            "median_income_hourly": round(median_hourly, 1) if median_hourly else None,
            "median_hours_weekly": round(median_hours, 1) if median_hours else None,
            "education_mode": mode_edu,
            "pct_professional": round(pct_professional, 1),
            "formality_rate": round(formality_rate, 1),
            "health_insurance_rate": round(health_rate, 1),
            "health_protection_index": round(health_protection_index, 1),
        })

    # Sort by employment
    results.sort(key=lambda x: x["jobs"], reverse=True)

    total_jobs = sum(r["jobs"] for r in results)
    print(f"\n  {len(results)} occupations with sufficient data")
    print(f"  {total_jobs:,} total jobs represented")

    # Write CSV
    os.makedirs(os.path.join(BASE, "output"), exist_ok=True)
    csv_path = os.path.join(BASE, "output", "occupations.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"  Wrote {csv_path}")

    # Write JSON catalog
    json_path = os.path.join(BASE, "output", "occupations.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {json_path}")

    # Print top 20
    print("\nTop 20 occupations by employment:")
    print(f"{'Code':<6} {'Jobs':>12} {'Income':>10} {'Edu':>25} {'Formal%':>8}  Title")
    print("-" * 110)
    for r in results[:20]:
        income = f"${r['median_income_monthly']:,}" if r['median_income_monthly'] else "N/A"
        print(f"{r['sinco_code']:<6} {r['jobs']:>12,} {income:>10} {r['education_mode']:>25} {r['formality_rate']:>7.1f}%  {r['title'][:50]}")


def weighted_median(pairs):
    """Compute weighted median from (value, weight) pairs."""
    if not pairs:
        return None
    # Sort by value
    pairs_sorted = sorted(pairs, key=lambda x: x[0])
    total_weight = sum(w for _, w in pairs_sorted)
    if total_weight <= 0:
        return None
    cumulative = 0
    target = total_weight / 2
    for value, weight in pairs_sorted:
        cumulative += weight
        if cumulative >= target:
            return value
    return pairs_sorted[-1][0]


if __name__ == "__main__":
    main()
