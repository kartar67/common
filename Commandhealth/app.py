import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import json, os
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(layout="wide")
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# Dropdown mappings based on extracted Excel data
health_psy_mapping = {
    "Blood Test": {
        "Haemoglobin": ["14","15","16","17","18"],
        "TLC": ["10000-11000","9000-10000","7000-9000","4000-7000","3000-4000","4000-5000"],
        "Neutrophil": ["70-75%","60-70%","50-60%","45-50%","40-45%"],
        "Lymphocytes": ["45-50%","25-45%","20-25%"],
        "Monocytes": ["9-10%","4-8%","2-3%"],
        "Eosinophil": ["5-6%","3-4%","1-2%"],
        "Basophil": ["<1%",">1%"],
        "Platelets": ["3.6 - 4 Lakh","2 - 3.5 Lakh","< 1.5 - 1.99 Lakh"],
        "Blood Sugar Fasting": ["105 - 110","76 - 104","< 70 - 75"],
        "Blood Sugar Post Prandial": ["120 - 140","91 - 119","< 80 - 90"]
    },
    "Physical Check": {
        "Blood Pr Upper": ["> 120","110 - 119","100 - 109"],
        "Blood Pr Lower": ["69 - 60","79 - 70","< 80"]
        },
    "Lipid Profile": {
        "Total Cholestrol": ["190 - 200","161 - 189","< 150 - 160"],
        "Triglyceride": ["140 - 150","111 - 139","< 100 - 110"],
        "LDL": ["90 - 100","61 - 89","< 50 - 60"],
        "HDL": ["55 - 60","46 - 54",">40 - 45"]
    },
    "Psy": {
        "Loan": ["Yes", "No"],
        "Shape 1": ["Yes", "No"],
        "Court Case": ["Yes", "No"],
        "Punishment": ["Yes", "No"]
        }
}

# Scoring logic
score_mapping = {
    "Haemoglobin": {"14": 4, "15": 1, "16": 0, "17": 1, "18": 4},
    "TLC": {"10000-11000": 4, "9000-10000": 1, "7000-9000": 0, "4000-7000": 0, "3000-4000": 1, "4000-5000": 4},
    "Neutrophil": {"70-75%": 4, "60-70%": 1, "50-60%": 0, "45-50%": 1, "40-45%": 4},
    "Lymphocytes": {"45-50%": 4, "25-45%": 0, "20-25%": 4},
    "Monocytes": {"9-10%": 4, "4-8%": 0, "2-3%": 4},
    "Eosinophil": {"5-6%": 3, "3-4%": 0, "1-2%": 3},
    "Basophil": {"<1%": 0, ">1%": 3},
    "Platelets": {"3.6 - 4 Lakh": 3, "2 - 3.5 Lakh": 0, "< 1.5 - 1.99 Lakh": 3},
    "Blood Sugar Fasting": {"105 - 110": 4, "76 - 104": 0, "< 70 - 75": 4},
    "Blood Sugar Post Prandial": {"120 - 140": 4, "91 - 119": 0, "< 80 - 90": 4},
    "Blood Pr Upper": {"> 120": 4, "110 - 119": 2, "100 - 109": 0},
    "Blood Pr Lower": {"69 - 60": 0, "79 - 70": 2, "< 80": 4},
    "Total Cholestrol": {"190 - 200": 4, "161 - 189": 0, "< 150 - 160": 4},
    "Triglyceride": {"140 - 150": 4, "111 - 139": 0, "< 100 - 110": 4},
    "LDL": {"90 - 100": 4, "61 - 89": 0, "< 50 - 60": 4},
    "HDL": {"55 - 60": 4, "46 - 54": 0, ">40 - 45": 4},
    "Loan": {"Yes": 3, "No": 0},
    "Shape 1": {"Yes": 0, "No": 3},
    "Court Case": {"Yes": 3, "No": 0},
    "Punishment": {"Yes": 3, "No": 0}
}

# Remarks mapping for better handling
remarks_mapping = {
    "Haemoglobin": {"14": "Moderate Polycythemia", "15": "Mild Polycythemia", "16": "Good", "17": "Severe Polycythemia", "18": "Risk of Blood Cancer"},
    "TLC": {"10000-11000": "Very High TLC - Possible Inflammation", "9000-10000": "High TLC - Possible Inflammation", "7000-9000": "Good", "4000-7000": "Good", "3000-4000": "Low TLC - Possible Infection", "4000-5000": "Very Low TLC - Possible Infection"},
    "Neutrophil": {"70-75%": "a", "60-70%": "b", "50-60%": "c", "45-50%": "d", "40-45%": "e"},
    "Lymphocytes": {"45-50%": "f", "25-45%": "g", "20-25%": "h"},
    "Monocytes": {"9-10%": "i", "4-8%": "j", "2-3%": "k"},
    "Eosinophil": {"5-6%": "n", "3-4%": "o", "1-2%": "p"},
    "Basophil": {"<1%": "l", ">1%": "m"},
    "Platelets": {"3.6 - 4 Lakh": "q", "2 - 3.5 Lakh": "r", "< 1.5 - 1.99 Lakh": "s"},
    "Blood Sugar Fasting": {'105 - 110': 't', '76 - 104': 'u', '< 70 - 75': 'v'},
    "Blood Sugar Post Prandial": {'120 - 140': 'w', '91 - 119': 'x', '< 80 - 90': 'y'},
    "Blood Pr Upper": {'> 120': 'z', '110 - 119': 'aa', '100 - 109': 'bb'},
    "Blood Pr Lower": {'69 - 60': 'cc', '79 - 70': 'dd', '< 80': 'ee'},
    "Total Cholestrol": {'190 - 200': 'ff', '161 - 189': 'gg', '< 150 - 160': 'hh'},
    "Triglyceride": {'140 - 150': 'ii', '111 - 139': 'jj', '< 100 - 110': 'kk'},
    "LDL": {'90 - 100': 'll', '61 - 89': 'mm', '< 50 - 60': 'nn'},
    "HDL": {'55 - 60': 'oo', '46 - 54': 'pp', '>40 - 45': 'qq'},
    "Loan": {'Yes': 'rr', 'No': 'ss'},
    "Shape 1": {'Yes': 'tt', 'No': 'uu'},
    "Court Case": {'Yes': 'vv', 'No': 'ww'},
    "Punishment": {'Yes': 'xx', 'No': 'yy'}
}

# Function to apply color formatting to the "score" column
def score_color_mapping(val):
    if val <= 10:
        return "background-color: lightgreen; color: black;"
    elif 10 < val <= 20:
        return "background-color: lightyellow; color: black;"
    elif 20 < val <= 30:
        return "background-color: lightcoral; color: black;"  # Light Red
    else:
        return "background-color: red; color: white;"  # Dark Red


def fetch_data():
    with sqlite3.connect("health_data.db") as conn:
        return pd.read_sql("SELECT * FROM health_data", conn)

def parse_json_fields(record):
    """Convert stringified JSON fields to dictionaries for better formatting."""
    json_fields = ["blood_test", "physical_check", "lipid_profile", "psy"]
    for field in json_fields:
        if field in record and isinstance(record[field], str):
            try:
                record[field] = json.loads(record[field])
            except json.JSONDecodeError:
                st.error(f"Error decoding JSON for {field}")
    return record

def display_record_details(record):
    st.subheader("Selected Record Details")
    parsed_record = parse_json_fields(record.to_dict())
    st.json(parsed_record, expanded=True)
    
def calculate_score(data):
    total_score = 0
    remarks = []
    debug_output = []
    
    for subcategory, value in data.items():
        if subcategory in score_mapping and value in score_mapping[subcategory]:
            score = score_mapping[subcategory][value]
            total_score += score

            # Add debug output for each calculation
            debug_output.append(f"{subcategory}: {value} -> Score: {score}")
            
            if subcategory in remarks_mapping and value in remarks_mapping[subcategory]:
                remarks.append(remarks_mapping[subcategory][value])
    
    # Print debug output to console
    print("\nScore Calculation Details:")
    for debug_line in debug_output:
        print(debug_line)
    print(f"Total Score: {total_score}")

    # Optionally display in Streamlit for debugging
    with st.expander("Debug: Score Calculation Details", expanded=False):
        for debug_line in debug_output:
            st.write(debug_line)
        st.write(f"**Total Score: {total_score}**")

    return total_score, "; ".join(remarks)

# Get the directory where the script or exe is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "health_data.db")

# Database setup
def init_db():
    if os.path.exists(DB_FILE):
        return  # If the database already exists, skip reinitialization
    """Create the database file if it does not exist and set up tables."""
    db_exists = os.path.exists(DB_FILE)  # Check if the database already exists

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_data (
                ser_no TEXT, fmn TEXT, unit TEXT, army_no TEXT, full_name TEXT, 
                year TEXT, blood_test TEXT, physical_check TEXT, lipid_profile TEXT, psy TEXT, 
                score INTEGER, remarks TEXT,
                PRIMARY KEY (ser_no, fmn, unit, army_no, full_name, year)
            )
        """)
        conn.commit()

    if not db_exists:
        print("New database created.")
    else:
        print("Existing database loaded.")

# Initialize the database only once per session
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state["db_initialized"] = True


# Save data to database
def save_to_db(data):
    total_score = 0
    remarks_list = []

    # Iterate through all categories to calculate the total score
    for category in ["Blood Test", "Physical Check", "Lipid Profile", "Psy"]:
        if category in data:
            category_score, category_remarks = calculate_score(data[category])
            total_score += category_score
            if category_remarks:
                remarks_list.append(category_remarks)

    remarks = "; ".join(remarks_list)  # Combine remarks from all categories

    with sqlite3.connect("health_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO health_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (data["Ser No"], data["Fmn"], data["Unit"], data["Army Number"],
                        data["Full Name"], data["Year"], json.dumps(data["Blood Test"]),
                        json.dumps(data["Physical Check"]), json.dumps(data["Lipid Profile"]),
                        json.dumps(data["Psy"]), total_score, remarks))
        conn.commit()
    st.success(f"Data saved successfully! Total Score: {total_score}")

    
# Streamlit UI
st.title("Health Overview App")
page = st.sidebar.radio("Navigation", ["Data Input", "Reporting"])

if page == "Data Input":
    st.header("Enter Health Data")
    
    def mandatory_input(label, key):
        return st.text_input(f"{label} * ❗", key=key)
    
    col1, col2 = st.columns(2)
    with col1:
        ser_no = mandatory_input("Ser No", "ser_no")
        fmn = mandatory_input("Fmn", "fmn")
        unit = mandatory_input("Unit", "unit")
    with col2:
        army_no = mandatory_input("Army Number", "army_no")
        name = mandatory_input("Full Name", "full_name")
        year = st.selectbox("Year * ❗", ["2023", "2024", "2025"], key="year")
    
    st.subheader("Health Categories")
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    
    form_data = {}
    with col1:
        st.subheader("Blood Test")
        form_data["Blood Test"] = {}
        for subcategory, options in health_psy_mapping["Blood Test"].items():
            form_data["Blood Test"][subcategory] = st.selectbox(f"{subcategory}:", options, key=f"BloodTest_{subcategory}")
    
    with col2:
        st.subheader("Physical Check")
        form_data["Physical Check"] = {}
        for subcategory, options in health_psy_mapping["Physical Check"].items():
            form_data["Physical Check"][subcategory] = st.selectbox(f"{subcategory}:", options, key=f"PhysicalCheck_{subcategory}")
    
    with col3:
        st.subheader("Lipid Profile")
        form_data["Lipid Profile"] = {}
        for subcategory, options in health_psy_mapping["Lipid Profile"].items():
            form_data["Lipid Profile"][subcategory] = st.selectbox(f"{subcategory}:", options, key=f"LipidProfile_{subcategory}")
    
    with col4:
        st.subheader("Psy")
        form_data["Psy"] = {}
        for subcategory, options in health_psy_mapping["Psy"].items():
            form_data["Psy"][subcategory] = st.selectbox(f"{subcategory}:", options, key=f"Psy_{subcategory}")
    
    if st.button("Save Data"):
        if all([ser_no, fmn, unit, army_no, name, year]):
            save_to_db({"Ser No": ser_no, "Fmn": fmn, "Unit": unit, "Army Number": army_no,
                        "Full Name": name, "Year": year, "Blood Test": form_data["Blood Test"],
                        "Physical Check": form_data["Physical Check"], "Lipid Profile": form_data["Lipid Profile"], "Psy": form_data["Psy"]})
        else:
            st.error("All primary key fields are mandatory!")

elif page == "Reporting":
    st.header("Health Data Reports")
    df = fetch_data()

    if df.empty:
        st.warning("No data available.")

    search_query = st.text_input("Search by Name, Unit, or Army No:")
    if search_query:
        df = df[df.apply(lambda row: search_query.lower() in str(row.values).lower(), axis=1)]

    # Define the new column order  
    column_order = [
        "ser_no", "fmn", "unit", "army_no", "full_name", "year", "score", "remarks",
        "blood_test", "physical_check", "lipid_profile", "psy"
    ]
    
    # Reorder the DataFrame  
    df = df[column_order]

    # Apply conditional formatting using a lambda function with map
    styled_df = df.style.map(lambda val: score_color_mapping(val), subset=["score"])

    st.dataframe(styled_df, height=400, width=1400)  # Display the styled DataFrame

    selected_name = st.selectbox("Select a Name:", df["full_name"].unique() if not df.empty else [])

    if selected_name:
        filtered_df = df[df["full_name"] == selected_name].reset_index(drop=True)

        if not filtered_df.empty:
            index = st.session_state.get("record_index", 0)

            # Display Current Record
            selected_data = filtered_df.iloc[index]

            st.subheader(f"Record {index+1} of {len(filtered_df)}")
            st.success(f"Total Score: {selected_data["score"]}")
            st.info(selected_data["remarks"])
            display_record_details(selected_data)

            # Show navigation buttons only if multiple records exist
            if len(filtered_df) > 1:
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("Previous", disabled=(index == 0)):
                        st.session_state["record_index"] = index - 1
                        st.rerun()
                with col2:
                    if st.button("Next", disabled=(index == len(filtered_df) - 1)):
                        st.session_state["record_index"] = index + 1
                        st.rerun()
