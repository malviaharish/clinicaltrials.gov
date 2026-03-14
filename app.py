import streamlit as st
import requests
import pandas as pd
import io
import plotly.express as px

st.set_page_config(page_title="ClinicalTrials.gov Multi Search Tool", layout="wide")

st.title("🔬 ClinicalTrials.gov Multi-Keyword Search Tool")

keywords = st.text_input(
    "Enter keywords separated by comma",
    "Distal Femoral Osteotomy, Distal Femoral"
)

max_results = st.slider("Maximum trials per keyword", 50, 2000, 500)

# ---------- SAFE HELPERS ---------- #

def safe_join(values):
    if not values or not isinstance(values, list):
        return ""
    return "; ".join(str(v) for v in values)


def extract_outcomes(outcomes):
    if not isinstance(outcomes, list):
        return ""
    vals = []
    for o in outcomes:
        if isinstance(o, dict):
            vals.append(o.get("measure", ""))
    return "; ".join(vals)


def extract_interventions(interventions):
    if not isinstance(interventions, list):
        return ""
    vals = []
    for i in interventions:
        if isinstance(i, dict):
            vals.append(i.get("name", ""))
    return "; ".join(vals)


def extract_collaborators(collabs):
    if not isinstance(collabs, list):
        return ""
    vals = []
    for c in collabs:
        if isinstance(c, dict):
            vals.append(c.get("name", ""))
    return "; ".join(vals)


def extract_locations(locations):

    if not isinstance(locations, list):
        return "", []

    locs = []
    countries = []

    for loc in locations:

        if not isinstance(loc, dict):
            continue

        facility = loc.get("facility") or {}
        address = facility.get("address") or {}

        name = facility.get("name", "")
        city = address.get("city", "")
        country = address.get("country", "")

        locs.append(f"{name} ({city}, {country})")

        if country:
            countries.append(country)

    return "; ".join(locs), countries


def extract_documents(docs):
    if not isinstance(docs, list):
        return ""
    vals = []
    for d in docs:
        if isinstance(d, dict):
            vals.append(d.get("type", ""))
    return "; ".join(vals)


def extract_other_ids(ids):
    if not isinstance(ids, list):
        return ""
    vals = []
    for i in ids:
        if isinstance(i, dict):
            vals.append(i.get("id", ""))
    return "; ".join(vals)


# ---------- SEARCH ---------- #

if st.button("Search Clinical Trials"):

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]

    all_records = []
    all_countries = []

    url = "https://clinicaltrials.gov/api/v2/studies"

    for keyword in keyword_list:

        st.write(f"Fetching trials for: **{keyword}**")

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

            response = requests.get(url, params=params)

            if response.status_code != 200:
                st.error(f"Error retrieving {keyword}")
                break

            data = response.json()

            studies = data.get("studies", [])

            for study in studies:

                protocol = study.get("protocolSection") or {}

                id_mod = protocol.get("identificationModule") or {}
                status_mod = protocol.get("statusModule") or {}
                desc_mod = protocol.get("descriptionModule") or {}
                cond_mod = protocol.get("conditionsModule") or {}
                design_mod = protocol.get("designModule") or {}
                outcome_mod = protocol.get("outcomesModule") or {}
                sponsor_mod = protocol.get("sponsorCollaboratorsModule") or {}
                elig_mod = protocol.get("eligibilityModule") or {}
                contact_mod = protocol.get("contactsLocationsModule") or {}
                arms_mod = protocol.get("armsInterventionsModule") or {}
                doc_mod = protocol.get("documentModule") or {}

                nct = id_mod.get("nctId", "")

                locations, countries = extract_locations(contact_mod.get("locations"))

                all_countries.extend(countries)

                record = {

                    "Search Term": keyword,
                    "NCT Number": nct,
                    "Study Title": id_mod.get("briefTitle", ""),
                    "Study URL": f"https://clinicaltrials.gov/study/{nct}",
                    "Study Status": status_mod.get("overallStatus", ""),
                    "Brief Summary": desc_mod.get("briefSummary", ""),
                    "Conditions": safe_join(cond_mod.get("conditions")),
                    "Interventions": extract_interventions(arms_mod.get("interventions")),
                    "Primary Outcomes": extract_outcomes(outcome_mod.get("primaryOutcomes")),
                    "Secondary Outcomes": extract_outcomes(outcome_mod.get("secondaryOutcomes")),
                    "Sponsor": (sponsor_mod.get("leadSponsor") or {}).get("name", ""),
                    "Collaborators": extract_collaborators(sponsor_mod.get("collaborators")),
                    "Sex": elig_mod.get("sex", ""),
                    "Phases": safe_join(design_mod.get("phases")),
                    "Enrollment": (design_mod.get("enrollmentInfo") or {}).get("count", ""),
                    "Study Type": design_mod.get("studyType", ""),
                    "Start Date": (status_mod.get("startDateStruct") or {}).get("date", ""),
                    "Completion Date": (status_mod.get("completionDateStruct") or {}).get("date", ""),
                    "Locations": locations,
                    "Countries": "; ".join(countries),
                    "Documents": extract_documents(doc_mod.get("documents"))
                }

                all_records.append(record)

            fetched += len(studies)

            if fetched >= max_results:
                break

            next_token = data.get("nextPageToken")

            if not next_token:
                break

    df = pd.DataFrame(all_records)

    st.success(f"{len(df)} total records retrieved")

    # ---------- DUPLICATE HANDLING ---------- #

    duplicates = df[df.duplicated(subset=["NCT Number"], keep=False)]
    unique_trials = df.drop_duplicates(subset=["NCT Number"])

    # ---------- PRISMA STATS ---------- #

    st.subheader("PRISMA Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Records", len(df))
    col2.metric("Duplicates", len(duplicates))
    col3.metric("Unique Trials", len(unique_trials))

    # ---------- SUMMARY PER KEYWORD ---------- #

    st.subheader("Trial Count per Keyword")

    summary = df.groupby("Search Term")["NCT Number"].nunique().reset_index()
    summary.columns = ["Keyword", "Trials"]

    st.dataframe(summary)

    # ---------- INTERACTIVE CHARTS ---------- #

    st.subheader("Trial Status Distribution")

    fig1 = px.histogram(df, x="Study Status")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Trials by Study Type")

    fig2 = px.histogram(df, x="Study Type")
    st.plotly_chart(fig2, use_container_width=True)

    # ---------- COUNTRY MAP ---------- #

    st.subheader("Country Distribution Map")

    country_series = pd.Series(all_countries)
    country_counts = country_series.value_counts().reset_index()
    country_counts.columns = ["Country", "Trials"]

    fig_map = px.choropleth(
        country_counts,
        locations="Country",
        locationmode="country names",
        color="Trials",
        title="Clinical Trials by Country"
    )

    st.plotly_chart(fig_map, use_container_width=True)

    # ---------- TRIAL DETAIL VIEWER ---------- #

    st.subheader("Trial Detail Viewer")

    selected_trial = st.selectbox(
        "Select Trial (NCT Number)",
        unique_trials["NCT Number"]
    )

    trial_data = unique_trials[unique_trials["NCT Number"] == selected_trial]

    st.write(trial_data.T)

    # ---------- DATA TABLE ---------- #

    st.subheader("All Trials")

    st.dataframe(unique_trials, use_container_width=True)

    # ---------- EXCEL EXPORT ---------- #

    excel_buffer = io.BytesIO()

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:

        df.to_excel(writer, sheet_name="All Results", index=False)
        unique_trials.to_excel(writer, sheet_name="Unique Trials", index=False)
        duplicates.to_excel(writer, sheet_name="Duplicate Trials", index=False)
        summary.to_excel(writer, sheet_name="Keyword Summary", index=False)

    excel_buffer.seek(0)

    st.download_button(
        label="📥 Download Excel",
        data=excel_buffer,
        file_name="clinical_trials_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
