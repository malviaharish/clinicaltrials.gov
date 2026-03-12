import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="ClinicalTrials.gov Search Tool", layout="wide")

st.title("🔬 ClinicalTrials.gov Trial Search Tool")

# User input
search_term = st.text_input("Enter keyword (disease, drug, device, etc.)", "")
max_results = st.slider("Number of trials", 10, 200, 50)

# Search button
if st.button("Search Trials"):

    if search_term == "":
        st.warning("Please enter a search term.")
    else:

        url = "https://clinicaltrials.gov/api/v2/studies"

        params = {
            "query.term": search_term,
            "pageSize": max_results,
            "format": "json"
        }

        response = requests.get(url, params=params)

        if response.status_code != 200:
            st.error("Failed to fetch data from ClinicalTrials.gov")
        else:

            data = response.json()

            trials = []

            for study in data.get("studies", []):
                protocol = study.get("protocolSection", {})

                identification = protocol.get("identificationModule", {})
                status = protocol.get("statusModule", {})
                design = protocol.get("designModule", {})
                conditions = protocol.get("conditionsModule", {})
                sponsor = protocol.get("sponsorCollaboratorsModule", {})

                trials.append({
                    "NCT Number": identification.get("nctId", ""),
                    "Title": identification.get("briefTitle", ""),
                    "Condition": ", ".join(conditions.get("conditions", [])),
                    "Study Status": status.get("overallStatus", ""),
                    "Study Type": design.get("studyType", ""),
                    "Sponsor": sponsor.get("leadSponsor", {}).get("name", ""),
                    "Start Date": status.get("startDateStruct", {}).get("date", "")
                })

            df = pd.DataFrame(trials)

            st.success(f"{len(df)} trials found")

            st.dataframe(df, use_container_width=True)

            # CSV download
            csv = df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="clinical_trials_results.csv",
                mime="text/csv"
            )
