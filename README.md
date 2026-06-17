# Lifespan vs. Healthspan — the Healthy Life Expectancy Gap

Streamlit dashboard for MSBA382 Healthcare Analytics. Core metric:
**gap = life expectancy − healthy life expectancy** (years lived in poor health).

## Files
- `app.py` — the dashboard (map, trends, ranking, gender, MENA focus, forecast)
- `data_prep.py` — builds `hale_le_gap.csv` from the live sources
- `DATA_DICTIONARY.md` — schema of the dataset
- `requirements.txt` — dependencies

## Run locally
    pip install -r requirements.txt
    python data_prep.py        # optional: writes hale_le_gap.csv
    streamlit run app.py

The app builds the data live from Our World in Data if no CSV is present,
so `data_prep.py` is optional locally.

## Publish (Streamlit Community Cloud)
1. Push this folder to a public GitHub repo.
2. On share.streamlit.io, create an app pointing to `app.py`.
3. (Optional) set the landing password in **Settings → Secrets**:

       password = "your_password_here"

   Default password if no secret is set: `healthspan2026`.

## Sources
WHO Global Health Observatory (HALE) and UN World Population Prospects
(life expectancy), processed by Our World in Data. HALE and LE come from
different producers — a small documented cross-source caveat on the gap.
