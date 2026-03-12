import streamlit as st
import requests
import pandas as pd
import io

st.set_page_config(page_title="ClinicalTrials.gov Multi Search Tool", layout="wide")

st.title("🔬 ClinicalTrials.gov Multi-Keyword Search Tool")

keywords = st.text_input(
    "Enter keywords separated by comma",
    "Distal Femoral Osteotomy, Distal Femoral"
)

max_results = st.slider("Number of studies per keyword", 10, 500, 100)


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
        return ""

    locs = []

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

    return "; ".join(locs)


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


# ---------- SEARCH BUTTON ---------- #

if st.button("Search Clinical Trials"):

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    all_records = []

    url = "https://clinicaltrials.gov/api/v2/studies"

    for keyword in keyword_list:

        params = {
            "query.term": keyword,
            "pageSize": max_results,
            "format": "json"
        }

        response = requests.get(url, params=params)

        if response.status_code != 200:
            st.error(f"Failed to retrieve results for: {keyword}")
            continue

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

            record = {

                "Search Term": keyword,
                "NCT Number": nct,
                "Study Title": id_mod.get("briefTitle", ""),
                "Study URL": f"https://clinicaltrials.gov/study/{nct}",
                "Acronym": id_mod.get("acronym", ""),
                "Study Status": status_mod.get("overallStatus", ""),
                "Brief Summary": desc_mod.get("briefSummary", ""),
                "Study Results": status_mod.get("hasResults", ""),
                "Conditions": safe_join(cond_mod.get("conditions")),
                "Interventions": extract_interventions(arms_mod.get("interventions")),
                "Primary Outcome Measures": extract_outcomes(outcome_mod.get("primaryOutcomes")),
                "Secondary Outcome Measures": extract_outcomes(outcome_mod.get("secondaryOutcomes")),
                "Other Outcome Measures": extract_outcomes(outcome_mod.get("otherOutcomes")),
                "Sponsor": (sponsor_mod.get("leadSponsor") or {}).get("name", ""),
                "Collaborators": extract_collaborators(sponsor_mod.get("collaborators")),
                "Sex": elig_mod.get("sex", ""),
                "Age": f"{elig_mod.get('minimumAge','')} - {elig_mod.get('maximumAge','')}",
                "Phases": safe_join(design_mod.get("phases")),
                "Enrollment": (design_mod.get("enrollmentInfo") or {}).get("count", ""),
                "Funder Type": (sponsor_mod.get("leadSponsor") or {}).get("class", ""),
                "Study Type": design_mod.get("studyType", ""),
                "Study Design": (design_mod.get("designInfo") or {}).get("allocation", ""),
                "Other IDs": extract_other_ids(id_mod.get("secondaryIdInfos")),
                "Start Date": (status_mod.get("startDateStruct") or {}).get("date", ""),
                "Primary Completion Date": (status_mod.get("primaryCompletionDateStruct") or {}).get("date", ""),
                "Completion Date": (status_mod.get("completionDateStruct") or {}).get("date", ""),
                "First Posted": (status_mod.get("studyFirstPostDateStruct") or {}).get("date", ""),
                "Results First Posted": (status_mod.get("resultsFirstPostDateStruct") or {}).get("date", ""),
                "Last Update Posted": (status_mod.get("lastUpdatePostDateStruct") or {}).get("date", ""),
                "Locations": extract_locations(contact_mod.get("locations")),
                "Study Documents": extract_documents(doc_mod.get("documents"))
            }

            all_records.append(record)

    df = pd.DataFrame(all_records)

    st.success(f"{len(df)} total records retrieved")

    st.dataframe(df, use_container_width=True)

    # ---------- DUPLICATE PROCESSING ---------- #

    duplicates = df[df.duplicated(subset=["NCT Number"], keep=False)]
    unique_trials = df.drop_duplicates(subset=["NCT Number"])

    st.write("Unique Trials:", len(unique_trials))
    st.write("Duplicate Trials:", len(duplicates))

    # ---------- EXCEL EXPORT ---------- #

    excel_buffer = io.BytesIO()

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="All Results", index=False)
        unique_trials.to_excel(writer, sheet_name="Unique Trials", index=False)
        duplicates.to_excel(writer, sheet_name="Duplicate Trials", index=False)

    excel_buffer.seek(0)

    st.download_button(
        label="📥 Download Excel (3 sheets)",
        data=excel_buffer,
        file_name="clinical_trials_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
