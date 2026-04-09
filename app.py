# app.py
import io
import pandas as pd
import streamlit as st
from optimized_country_processing_with_lookup import process_country_data_with_lookup  # :contentReference[oaicite:1]{index=1}
from openai import OpenAI
import json
import os
import unicodedata
import time

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def _canon(s: str) -> str:
    """case‑ & accent‑onafhankelijk normaliseren"""
    return unicodedata.normalize("NFKD", s).casefold()


def detect_key_columns(df):
    """
    Vraag GPT om *alle* kolomnamen die SAMEN één uniek product identificeren.
    Geeft een gevalideerde lijst terug met willekeurig (≥ 1) aantal kolommen.
    """
  
    prompt = f"""
    You receive the column headers of a medicine‑shortage spreadsheet.
    Return an array of ALL headers that, TOGETHER, uniquely identify a
    pharmaceutical product in this file (trade name/form, strength,
    pack size, etc.).  Keep the original spelling.

    Answer ONLY in JSON like:
    {{"headers": ["Name", "Strength", "Pack size", …] }}

    Headers:
    {json.dumps(list(df.columns), ensure_ascii=False)}
    """
    try:
        rsp   = client.chat.completions.create(
                    model="gpt-4o-mini",
                    response_format={"type": "json_object"},
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}],
                )
        data  = json.loads(rsp.choices[0].message.content)

        # -------- 1. haal array eruit, ongeacht label -------------
        raw   = (data.get("headers") or data.get("columns") or
                 (data if isinstance(data, list) else []))

    except Exception as e:
        st.warning(f"GPT‑detectie key‑kolommen mislukt: {e}")
        raw = []

    # -------- 2. map naar werkelijke headers (case/acc‑proof) ----
    canon_map  = {_canon(c): c for c in df.columns.astype(str)}
    validated  = []
    for h in raw:
        c = canon_map.get(_canon(str(h)))
        if c and c not in validated:
            validated.append(c)

    # -------- 3. nood‑fallback als GPT niets vond ----------------
    if not validated:
        validated = list(df.columns[:4])          # eerste 4 kolommen als nood‑invulling
    return validated

def detect_atc_and_id_columns(df, max_rows_per_col=5):
    """
    Ask GPT to identify which column in the DataFrame contains:
      • the ATC code
      • the unique product / article identifier (e.g. Varunummer)

    Returns (atc_column:str|None, id_column:str|None)
    """

    # 1) build a compact JSON‑ready overview of the data
    preview = {}
    for col in df.columns:
        # take a few non‑empty samples per column
        vals = (
            df[col].dropna()
                  .astype(str)
                  .head(max_rows_per_col)
                  .tolist()
        )
        preview[col] = vals

    # 2) send single chat completion
    prompt = f"""
Below is a JSON object where keys are Excel column names and the values are
examples of the data in those columns.  
Determine:

  • which column holds the ATC code (label = "atc_column")
  • which column holds the unique identifier for the product (label = "id_column")

Respond ONLY with a JSON object in the form:
{{
  "atc_column": "<exact column header or empty string>",
  "id_column":  "<exact column header or empty string>"
}}
Spreadsheet preview:
```json
{json.dumps(preview, indent=2)[:6000]} 
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        answer = json.loads(response.choices[0].message.content)
        return answer.get("atc_column") or None, answer.get("id_column") or None
    except Exception as e:
        st.error(f"ATC / ID detectie via GPT mislukt: {e}")
        return None, None


def detect_language_and_country(df, sample_size=100):
    """
    Bepaal op basis van enkele willekeurige cellen in de DataFrame
    • in welke taal de omschrijvingen zijn geschreven
    • voor welk land (regulatory scope) het bestand bedoeld is.

    Retourneert: (language:str, country:str)

    Voorbeeld‑response van GPT:
    {"language": "Swedish", "country": "Sweden"}
    """
    # 1) Sampling – neem maximaal `sample_size` niet‑lege cellen.
    samples = []
    for col in df.columns:
        non_null = df[col].dropna().astype(str).head(sample_size // len(df.columns) + 1)
        samples.extend(non_null.tolist())
        if len(samples) >= sample_size:
            break
    sample_text = "\n".join(samples[:sample_size])

    # 2) Prompt
    prompt = f"""
You are an expert in European pharmaceutical dossiers.
Below is a random sample of {len(samples)} cell values taken from a spreadsheet
with medicinal‑product shortage data. Determine

  • The natural language used in the text (e.g. "Swedish", "Dutch", "English").
  • The country this file is about (e.g. "Sweden", "Belgium").

Respond ONLY with a JSON object like:
{{
  "language": "<language>",
  "country": "<country>"
}}

Sample values:
\"\"\"
{sample_text}
\"\"\"
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0
        )
        answer = json.loads(response.choices[0].message.content)
        return answer.get("language", "English"), answer.get("country", "Unknown")
    except Exception as e:
        st.error(f"GPT‑detectie mislukt: {e}")
        return "Unknown", "Unknown"



st.set_page_config(page_title="Medication Matcher", layout="wide")
st.title("Medication shortage – match to Dutch Z‑index")

# ────────────────────────────────────────────────────────────────────────────────
# 1. Upload
# ────────────────────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload een Excel‑ of CSV‑bestand met tekorten‑meldingen",
    type=["xlsx", "xls", "csv"],
)

if not uploaded_file:
    st.stop()                      # wacht totdat er een bestand is geüpload

# ────────────────────────────────────────────────────────────────────────────────
# 2. Inlezen & voorbeeld
# ────────────────────────────────────────────────────────────────────────────────
if uploaded_file.name.lower().endswith(("xlsx", "xls")):
    df = pd.read_excel(uploaded_file)
else:
    # ↓↓↓ vervang dit hele stuk ↓↓↓
    import csv, io

    # 1) probeer automatisch het delimiter te 'sniffen'
    uploaded_file.seek(0)                           # reset pointer
    sample = uploaded_file.read(4096)               # bytes
    uploaded_file.seek(0)                           # reset opnieuw

    try:
        dialect  = csv.Sniffer().sniff(
            sample.decode("utf‑8", errors="ignore"), delimiters=";,|\t"
        )
        sep = dialect.delimiter
    except csv.Error:
        # fallback‑heuristiek
        text = sample.decode("utf‑8", errors="ignore")
        sep  = ";" if text.count(";") > text.count(",") else ","

    # 2) lees met de PythON‑engine (toleranter)
    try:
        df = pd.read_csv(
            uploaded_file,
            sep=sep,
            engine="python",        # minder streng dan 'c'
            encoding="utf‑8",
        )
    except pd.errors.ParserError:
        # 3) laatste redmiddel: andere encoding of onregelmatige regels overslaan
        uploaded_file.seek(0)
        df = pd.read_csv(
            uploaded_file,
            sep=sep,
            engine="python",
            encoding="latin‑1",
            on_bad_lines="warn",    # of "skip" om problematische regels over te slaan
        )
st.success(f"Bestand geladen met {len(df):,} rijen en {len(df.columns)} kolommen.")
st.dataframe(df.head(50))

# ────────────────────────────────────────────────────────────────────────────────
# 3. Kolom‑selectie
# -------------------------------
st.subheader("Kies of bevestig de kolommen voor het matching‑script")

all_columns  = df.columns.astype(str).tolist()
default_cols = all_columns[: min(4, len(all_columns))]

# ---- 3a • AI detection for ATC & ID -----------------------------------------
# (1) simple heuristic  – good enough in 90 % of cases
heuristic_atc = next((c for c in all_columns if "atc" in c.lower()), None)
heuristic_id  = next((c for c in all_columns if c.lower() in
                      ["varunummer", "artikelnummer", "id", "product id", "unique id"]), None)

# (2) fallback to GPT if one of the two is still unknown
if not heuristic_atc or not heuristic_id:
    with st.spinner("GPT zoekt ATC‑ en ID‑kolom …"):
        gpt_atc, gpt_id = detect_atc_and_id_columns(df)
        heuristic_atc = heuristic_atc or gpt_atc
        heuristic_id  = heuristic_id  or gpt_id

# -----------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    atc_column = st.selectbox(
        "ATC‑kolom",
        options=all_columns,
        index=all_columns.index(heuristic_atc) if heuristic_atc in all_columns else 0,
        help="Wordt automatisch voorgesteld; pas aan indien nodig."
    )
  

with col2:
    id_column = st.selectbox(
        "Unieke ID‑kolom ",
        options=all_columns,
        index=all_columns.index(heuristic_id) if heuristic_id in all_columns else 0,
    )
    important_columns = st.multiselect(
     "Kolommen die samen een unieke ‘medication key’ vormen",
     options=all_columns,
     default=detect_key_columns(df) 
 )
    
# ────────────────────────────────────────────────────────────────────────────────
# 4. Taal uit het bestand ophalen
# ────────────────────────────────────────────────────────────────────────────────
st.subheader("Automatisch gedetecteerde taal en land")
with st.spinner("GPT detecteert taal en land…"):
    detected_language, detected_country = detect_language_and_country(df)

col_auto1, col_auto2 = st.columns(2)
language = col_auto1.text_input(
    "Taal (detectie) – wijzig indien nodig",
    value=detected_language,
)
country_name = col_auto2.text_input(
    "Land (detectie) – wijzig indien nodig",
    value=detected_country,
)

st.caption(
    "De waarden hierboven zijn door GPT bepaald op basis van de gegevens in het bestand. "
    "Pas ze aan als de detectie onjuist is."
)

batch_size   = 5

# ────────────────────────────────────────────────────────────────────────────────
# 5. Start knop
# ────────────────────────────────────────────────────────────────────────────────
if st.button("Start matching"):
    tmp_path = "upload_tmp.xlsx" if uploaded_file.name.endswith(("xlsx", "xls")) else "upload_tmp.csv"
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.info("Matching gestart… dit kan enkele minuten duren.")
    progress = st.progress(0)

    try:
        with st.spinner("LLM batches draaien…"):
            df_combos, df_final = process_country_data_with_lookup(
                input_file=tmp_path,
                sheet_name=None,
                country_name=country_name,
                language=language,               # ← taal uit bestand / invoer
                atc_column=atc_column,
                important_columns=important_columns,
                index_column=country_name+"_index",       # ← default 'taal_index'
                country_id_column=id_column,
                batch_size=batch_size,
                delay=2,
                test_mode=False,
                checkpoint_frequency=5,          # ← save every 5 batches (prevents data loss)
            )
        progress.progress(100)

        # ─────────  na het succesvol afronden van het proces ─────────
        if df_final is not None:
            st.success("Matching voltooid ✅")
            st.write("Eerste 200 rijen met PRK‑codes:")
            st.dataframe(df_final.head(200))

            # ---------- nieuw: download‑knop ----------
            csv_bytes = df_final.to_csv(index=False).encode("utf-8")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            prk_filename = f"{country_name.lower()}_tekortmeldingen_met_PRK_{timestamp}.csv"
            st.download_button(
                label="⬇️ Download met PRK‑bestand",
                data=csv_bytes,
                file_name=prk_filename,
                mime="text/csv",
            )
    except Exception as e:
        st.error(f"Er ging iets mis: {e}")