# Empleos MX

Visualización interactiva del mercado laboral mexicano como treemap, inspirado en [karpathy/jobs](https://github.com/karpathy/jobs).

**457 ocupaciones** cubriendo **~60M empleos** a partir de microdatos de la ENOE de INEGI (2024 T4). El área de cada rectángulo es proporcional al empleo total. El color muestra la métrica seleccionada.

## Capas de color

| Capa | Qué muestra | Escala | Fuente |
|---|---|---|---|
| **Ingreso** | Ingreso mensual mediano (MXN) | $2K–$50K | Variable `ingocup` de ENOE, mediana ponderada por `fac_tri` |
| **Educación** | Nivel educativo más frecuente por ocupación | Sin escolaridad → Doctorado | Variable `cs_p13_1` de ENOE, moda ponderada |
| **Formalidad** | % de trabajadores con empleo formal | 0%–100% | Variable `emp_ppal` de ENOE (1=informal, 2=formal) |
| **Protección en Salud** | Índice compuesto de acceso a salud y prestaciones | 0–100 | Variable `medica5c` de ENOE (ver metodología abajo) |
| **Seguro de salud** | % con acceso a instituciones de salud | 0%–100% | Variable `seg_soc` de ENOE (medida binaria) |
| **Exposición IA** | Estimación de impacto de IA por ocupación | 0–10 | Scoring con Claude Haiku sobre cada ocupación SINCO |

### Protección en Salud (índice compuesto)

Promedio ponderado por ocupación de un score individual basado en `medica5c`:

| Valor medica5c | Significado | Score |
|---|---|---|
| 3 | Acceso a instituciones de salud + otras prestaciones | 100 |
| 2 | Solo acceso a instituciones de salud | 70 |
| 4 | Otras prestaciones pero sin acceso a salud | 20 |
| 1 | Sin prestaciones | 0 |

Más informativo que la medida binaria de "Seguro de salud" porque distingue entre cobertura completa, parcial y nula.

## Fuente de datos

**ENOE** (Encuesta Nacional de Ocupación y Empleo) — encuesta trimestral de hogares de INEGI.
- Microdatos: [inegi.org.mx/programas/enoe/15ymas](https://www.inegi.org.mx/programas/enoe/15ymas/)
- Clasificación de ocupaciones: SINCO 2019 (4 dígitos, ~490 códigos)
- Variables: ocupación, ingreso (auto-reportado), educación, horas, formalidad, acceso a salud
- Ponderadores de expansión trimestral aplicados para estimaciones poblacionales

## Inicio rápido

```bash
# Ver la visualización (ya construida)
cd site && python3 -m http.server 8765
# Abrir http://localhost:8765

# Opcional: correr scoring de exposición IA (requiere API key)
export ANTHROPIC_API_KEY=sk-...
pip install anthropic
python score.py
python build_site_data.py
```

## Pipeline

```
Microdatos ENOE (INEGI)
    ↓ process_enoe.py
output/occupations.csv + occupations.json
    ↓ score.py (opcional, requiere Anthropic API key)
output/scores.json
    ↓ build_site_data.py
site/data.json → site/index.html (treemap en Canvas)
```

## Diferencias con la versión de EE.UU.

| | EE.UU. (karpathy/jobs) | México (este proyecto) |
|---|---|---|
| Fuente | BLS Occupational Outlook Handbook | Microdatos ENOE de INEGI |
| Ocupaciones | 342 | 457 |
| Empleos cubiertos | 143M | ~60M |
| Ingresos | Reportados por empleador | Auto-reportados (encuesta de hogares) |
| Proyecciones de crecimiento | Outlook BLS a 10 años | No disponible |
| Formalidad | N/A | Empleo formal vs. informal |
| Protección en salud | N/A | Índice compuesto + acceso binario |
| Clasificación | SOC | SINCO 2019 |

## Archivos

- `process_enoe.py` — Procesa microdatos ENOE en estadísticas por ocupación
- `build_site_data.py` — Combina stats + scores en site/data.json
- `score.py` — Scoring de exposición IA con Claude Haiku
- `site/index.html` — Visualización treemap en Canvas
- `site/data.json` — Datos para la visualización (pre-construido)
- `data/enoe/` — Microdatos ENOE crudos (no comiteados)
- `output/` — Datos procesados por ocupación
- `vercel.json` — Configuración de deploy para Vercel
