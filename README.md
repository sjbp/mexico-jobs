# Mexico Jobs Visualizer

Interactive treemap visualization of Mexico's labor market, inspired by [karpathy/jobs](https://github.com/karpathy/jobs).

Visualizes **457 occupations** covering **~60M jobs** from INEGI's ENOE survey (2024 Q4). Each rectangle's area is proportional to employment. Color layers: income, education, formality, and AI exposure.

## Data Source

**ENOE** (Encuesta Nacional de Ocupación y Empleo) — INEGI's quarterly household employment survey.
- Microdata: [inegi.org.mx/programas/enoe/15ymas](https://www.inegi.org.mx/programas/enoe/15ymas/)
- Occupation codes: SINCO 2019 (4-digit, ~490 codes)
- Variables: occupation, income (self-reported), education, hours, formality status
- Survey weights applied for population-level estimates

## Quick Start

```bash
# View the visualization (already built)
cd site && python3 -m http.server 8765
# Open http://localhost:8765

# Optional: run AI exposure scoring (requires API key)
export ANTHROPIC_API_KEY=sk-...
pip install anthropic
python score.py
python build_site_data.py
```

## Pipeline

```
ENOE microdata (INEGI)
    ↓ process_enoe.py
output/occupations.csv + occupations.json
    ↓ score.py (optional, requires Anthropic API key)
output/scores.json
    ↓ build_site_data.py
site/data.json → site/index.html (Canvas treemap)
```

## Color Layers

| Layer | What it shows | Scale |
|---|---|---|
| **Ingreso** | Median monthly income (MXN) | $2K–$50K |
| **Educación** | Most common education level | Sin escolaridad → Doctorado |
| **Formalidad** | % of workers in formal employment | 0%–100% |
| **Exposición IA** | LLM-estimated AI disruption risk | 0–10 (requires scoring) |

## Key Differences from US Version

| | US (karpathy/jobs) | Mexico (this project) |
|---|---|---|
| Source | BLS Occupational Outlook Handbook | INEGI ENOE microdata |
| Occupations | 342 | 457 |
| Jobs covered | 143M | ~60M |
| Income | Employer-reported median | Self-reported median |
| Growth projections | 10-year BLS outlook | Not available |
| Formality | N/A | Formal vs. informal employment |
| Classification | SOC | SINCO 2019 |

## Files

- `process_enoe.py` — Process ENOE microdata into occupation stats
- `build_site_data.py` — Merge stats + scores into site/data.json
- `score.py` — LLM scoring for AI exposure (Claude Haiku)
- `site/index.html` — Canvas treemap visualization
- `site/data.json` — Visualization data (pre-built)
- `data/enoe/` — Raw ENOE microdata (not committed)
- `output/` — Processed occupation data
