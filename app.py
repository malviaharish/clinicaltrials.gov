import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="ClinicalTrials.gov Search Tool", layout="wide")

st.title("🔬 ClinicalTrials.gov Advanced Search Tool")

keyword = st.text_input("Enter keyword (disease, drug, device)")
max_results = st.slider("Number of studies", 10, 500, 100)


# ---------------- SAFE HELPERS ---------------- #

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


# ---------------- SEARCH BUTTON ---------------- #

if st.button("Search Clinical Trials"):

    if keyword.strip() == "":
        st.warning("Please enter a search keyword")

    else:

        url = "https://clinicaltrials.gov/api/v2/studies"

        params = {
            "query.term": keyword,
            "pageSize": max_results,
            "format": "json"
        }

        response = requests.get(url, params=params)

        if response.status_code != 200:
            st.error("Failed to fetch data from ClinicalTrials.gov")
        else:

            data = response.json()
            studies = data.get("studies", [])

            records = []

            for study in studies:

                if not isinstance(study, dict):
                    continue

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

                records.append(record)

            df = pd.DataFrame(records)

            st.success(f"{len(df)} studies retrieved")

            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")

            st.download_button(
                "📥 Download CSV",
                csv,
                "clinical_trials_export.csv",
                "text/csv"
            )
