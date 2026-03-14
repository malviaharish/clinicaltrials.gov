import streamlit as st
import requests
import pandas as pd
import io
import plotly.express as px
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from wordcloud import WordCloud
import matplotlib.pyplot as plt

st.set_page_config(page_title="Clinical Trials Research Explorer", layout="wide")

st.title("🔬 ClinicalTrials Research Explorer")


keywords = st.text_input(
    "Enter keywords separated by comma",
    "Distal Femoral Osteotomy, Distal Femoral"
)

max_results = st.slider("Max trials per keyword", 50, 2000, 500)


# ---------------- HELPER FUNCTIONS ---------------- #

def safe_join(values):
    if not values or not isinstance(values, list):
        return ""
    return "; ".join(str(v) for v in values)


def extract_locations(locations):

    if not isinstance(locations, list):
        return "", []

    locs = []
    countries = []

    for loc in locations:

        if not isinstance(loc, dict):
            continue

        facility = loc.get("facility")

        if not isinstance(facility, dict):
            facility = {}

        address = facility.get("address")

        if not isinstance(address, dict):
            address = {}

        name = facility.get("name", "")
        city = address.get("city", "")
        country = address.get("country", "")

        locs.append(f"{name} ({city}, {country})")

        if country:
            countries.append(country)

    return "; ".join(locs), countries


# ---------------- SEARCH ---------------- #

if st.button("Search Clinical Trials"):

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]

    all_records = []
    all_countries = []

    url = "https://clinicaltrials.gov/api/v2/studies"

    for keyword in keyword_list:

        st.write(f"Searching: **{keyword}**")

        params = {
            "query.term": keyword,
            "pageSize": 100,
            "format": "json"
        }

        next_token = None
        fetched = 0

        while True:

            if next_token:
                params["pageToken"] = next_token

            r = requests.get(url, params=params)

            if r.status_code != 200:
                st.error("API Error")
                break

            data = r.json()
            studies = data.get("studies", [])

            for study in studies:

                protocol = study.get("protocolSection") or {}

                id_mod = protocol.get("identificationModule") or {}
                status_mod = protocol.get("statusModule") or {}
                desc_mod = protocol.get("descriptionModule") or {}
                cond_mod = protocol.get("conditionsModule") or {}
                design_mod = protocol.get("designModule") or {}
                contact_mod = protocol.get("contactsLocationsModule") or {}

                nct = id_mod.get("nctId", "")

                locations, countries = extract_locations(
                    contact_mod.get("locations")
                )

                all_countries.extend(countries)

                record = {

                    "Keyword": keyword,
                    "NCT": nct,
                    "Title": id_mod.get("briefTitle", ""),
                    "URL": f"https://clinicaltrials.gov/study/{nct}",
                    "Status": status_mod.get("overallStatus", ""),
                    "Summary": desc_mod.get("briefSummary", ""),
                    "Conditions": safe_join(cond_mod.get("conditions")),
                    "Study Type": design_mod.get("studyType", ""),
                    "Start Date": (status_mod.get("startDateStruct") or {}).get("date", ""),
                    "Locations": locations,
                    "Countries": "; ".join(countries)

                }

                all_records.append(record)

            fetched += len(studies)

            if fetched >= max_results:
                break

            next_token = data.get("nextPageToken")

            if not next_token:
                break


    df = pd.DataFrame(all_records)

    st.success(f"{len(df)} records retrieved")


# ---------------- PRISMA ---------------- #

    duplicates = df[df.duplicated(subset=["NCT"], keep=False)]
    unique_df = df.drop_duplicates(subset=["NCT"])

    st.subheader("Statistics")

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Records", len(df))
    c2.metric("Duplicates", len(duplicates))
    c3.metric("Unique Trials", len(unique_df))


# ---------------- SUMMARY PER KEYWORD ---------------- #

    st.subheader("Trial Count per Keyword")

    summary = df.groupby("Keyword")["NCT"].nunique().reset_index()
    summary.columns = ["Keyword", "Trials"]

    st.dataframe(summary)


# ---------------- CHARTS ---------------- #

    st.subheader("Trial Status Distribution")

    fig1 = px.histogram(df, x="Status")
    st.plotly_chart(fig1, use_container_width=True)


# ---------------- TIMELINE ---------------- #

    st.subheader("Trials Timeline")

    df["Year"] = pd.to_datetime(df["Start Date"], errors="coerce").dt.year

    fig2 = px.histogram(df, x="Year")

    st.plotly_chart(fig2, use_container_width=True)


# ---------------- SIMILAR STUDIES ---------------- #

    st.subheader("Find Similar Trials")

    titles = unique_df["Title"].fillna("")

    vectorizer = TfidfVectorizer(stop_words="english")

    matrix = vectorizer.fit_transform(titles)

    similarity = cosine_similarity(matrix)

    trial = st.selectbox("Select Trial", unique_df["NCT"])

    idx = unique_df.index[unique_df["NCT"] == trial][0]

    sim_scores = list(enumerate(similarity[idx]))

    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:6]

    similar_indices = [i[0] for i in sim_scores]

    similar_trials = unique_df.iloc[similar_indices]

    st.dataframe(similar_trials[["NCT", "Title", "Status"]])


# ---------------- DETAIL VIEW ---------------- #

    st.subheader("Trial Detail Viewer")

    trial_data = unique_df[unique_df["NCT"] == trial]

    st.write(trial_data.T)


# ---------------- DATA TABLE ---------------- #

    st.subheader("All Trials")

    st.dataframe(unique_df, use_container_width=True)


# ---------------- EXPORT ---------------- #

    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:

        df.to_excel(writer, sheet_name="All Results", index=False)
        unique_df.to_excel(writer, sheet_name="Unique Trials", index=False)
        duplicates.to_excel(writer, sheet_name="Duplicates", index=False)
        summary.to_excel(writer, sheet_name="Keyword Summary", index=False)

    buffer.seek(0)

    st.download_button(
        "Download Excel",
        buffer,
        "clinical_trials_results.xlsx"
    )
