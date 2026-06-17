# Dashboard-ready dataset — `hale_le_gap.csv`

One row per **entity × year** (≈183 countries + WHO regional aggregates + World, 2000–2021).
Core metric: **gap = life_exp − hale** (years lived in poor health).

| Column | Type | Meaning |
|---|---|---|
| `entity` | text | Country / WHO region / World |
| `iso3` | text | ISO-3 code (blank for aggregate rows) |
| `year` | int | 2000–2021 |
| `life_exp` | float | Life expectancy at birth, both sexes (lifespan) |
| `hale` | float | Healthy life expectancy at birth, both sexes (healthspan) |
| `gap` | float | **life_exp − hale — the headline metric** |
| `life_exp_male` | float | Male life expectancy at birth |
| `life_exp_female` | float | Female life expectancy at birth |
| `gap_male` | float | life_exp_male − hale (see HALE-by-sex caveat) |
| `gap_female` | float | life_exp_female − hale |
| `le_sex_gap` | float | Female − male life expectancy |
| `mena` | bool | Eastern Mediterranean / MENA focus flag |
| `is_aggregate` | bool | True for WHO-region / World rows (benchmarks, not countries) |

**Sources:** HALE — WHO Global Health Observatory; Life expectancy — UN World Population Prospects; both via Our World in Data.
**Caveat:** HALE (WHO) and LE (UN) are different producers → small cross-source note on the gap. HALE-by-sex is not published on OWID, so the gender layer leans on LE by sex.
