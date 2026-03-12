import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="ClinicalTrials.gov Advanced Search", layout="wide")

st.title("🔬 ClinicalTrials.gov Advanced Search Tool")

keyword = st.text_input("Enter search keyword (disease, drug, device)")
max_results = st.slider("Number of studies to retrieve", 10, 500, 100)


def extract_list(data, key):
    if key in data:
        return "; ".join(data[key])
    return ""


def extract_outcomes(outcomes):
    if not outcomes:
        return ""
    return "; ".join([o.get("measure", "") for o in outcomes])


def extract_locations(locations):
    if not locations:
        return ""
    locs = []
    for loc in locations:
        facility = loc.get("facility", {})
        name = facility.get("name", "")
        city = facility.get("address", {}).get("city", "")
        country = facility.get("address", {}).get("country", "")
        locs.append(f"{name} ({city}, {country})")
    return "; ".join(locs)


if st.button("Search Clinical Trials"):

    if keyword == "":
        st.warning("Please enter a search keyword")
    else:

        url = "https://clinicaltrials.gov/api/v2/studies"

        params = {
            "query.term": keyword,
            "pageSize": max_results,
            "format": "json"
        }

        response = requests.get(url, params=params)
        data = response.json()

        studies = data.get("studies", [])

        records = []

        for study in studies:

            protocol = study.get("protocolSection", {})
            id_mod = protocol.get("identificationModule", {})
            status_mod = protocol.get("statusModule", {})
            desc_mod = protocol.get("descriptionModule", {})
            cond_mod = protocol.get("conditionsModule", {})
            design_mod = protocol.get("designModule", {})
            outcome_mod = protocol.get("outcomesModule", {})
            sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})
            elig_mod = protocol.get("eligibilityModule", {})
            contact_mod = protocol.get("contactsLocationsModule", {})
            oversight_mod = protocol.get("oversightModule", {})
            arms_mod = protocol.get("armsInterventionsModule", {})
            doc_mod = protocol.get("documentModule", {})

            nct = id_mod.get("nctId", "")

            record = {
                "NCT Number": nct,
                "Study Title": id_mod.get("briefTitle", ""),
                "Study URL": f"https://clinicaltrials.gov/study/{nct}",
                "Acronym": id_mod.get("acronym", ""),
                "Study Status": status_mod.get("overallStatus", ""),
                "Brief Summary": desc_mod.get("briefSummary", ""),
                "Study Results": status_mod.get("hasResults", ""),
                "Conditions": "; ".join(cond_mod.get("conditions", [])),
                "Interventions": "; ".join([i.get("name","") for i in arms_mod.get("interventions",[])]),
                "Primary Outcome Measures": extract_outcomes(outcome_mod.get("primaryOutcomes")),
                "Secondary Outcome Measures": extract_outcomes(outcome_mod.get("secondaryOutcomes")),
                "Other Outcome Measures": extract_outcomes(outcome_mod.get("otherOutcomes")),
                "Sponsor": sponsor_mod.get("leadSponsor", {}).get("name",""),
                "Collaborators": "; ".join([c.get("name","") for c in sponsor_mod.get("collaborators",[])]),
                "Sex": elig_mod.get("sex",""),
                "Age": elig_mod.get("minimumAge","") + " - " + elig_mod.get("maximumAge",""),
                "Phases": "; ".join(design_mod.get("phases", [])),
                "Enrollment": design_mod.get("enrollmentInfo",{}).get("count",""),
                "Funder Type": sponsor_mod.get("leadSponsor",{}).get("class",""),
                "Study Type": design_mod.get("studyType",""),
                "Study Design": design_mod.get("designInfo",{}).get("allocation",""),
                "Other IDs": "; ".join([i.get("id","") for i in id_mod.get("secondaryIdInfos",[])]),
                "Start Date": status_mod.get("startDateStruct",{}).get("date",""),
                "Primary Completion Date": status_mod.get("primaryCompletionDateStruct",{}).get("date",""),
                "Completion Date": status_mod.get("completionDateStruct",{}).get("date",""),
                "First Posted": status_mod.get("studyFirstPostDateStruct",{}).get("date",""),
                "Results First Posted": status_mod.get("resultsFirstPostDateStruct",{}).get("date",""),
                "Last Update Posted": status_mod.get("lastUpdatePostDateStruct",{}).get("date",""),
                "Locations": extract_locations(contact_mod.get("locations")),
                "Study Documents": "; ".join([d.get("type","") for d in doc_mod.get("documents",[])])
            }

            records.append(record)

        df = pd.DataFrame(records)

        st.success(f"{len(df)} studies retrieved")

        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "📥 Download CSV",
            csv,
            "clinical_trials_full_export.csv",
            "text/csv"
        )
