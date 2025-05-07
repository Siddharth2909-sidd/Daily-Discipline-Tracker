import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from oauth2client.service_account import ServiceAccountCredentials

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Discipline Tracker", layout="centered")

CHECKLIST_FILE = "checklist.csv"
GOOGLE_SHEET_NAME = "Discipline Tracker Log"
SHEET_TAB_NAME = "Logs"
CREDENTIALS_FILE = "gcp_service_account.json"

# -------------------- GOOGLE SHEETS SETUP --------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(GOOGLE_SHEET_NAME).worksheet(SHEET_TAB_NAME)

# -------------------- LOAD CHECKLIST --------------------
@st.cache_data
def load_checklist():
    return pd.read_csv(CHECKLIST_FILE)

checklist_df = load_checklist()
if "Score" not in checklist_df.columns:
    st.error("Checklist file must contain 'Score' column.")
    st.stop()

# -------------------- SIDEBAR NAV --------------------
page = st.sidebar.radio("Navigate", ["🧘 Daily Tracker", "📊 Summary Dashboard"])

# -------------------- DAILY TRACKER --------------------
if page == "🧘 Daily Tracker":
    st.title("🧘 Daily Discipline Tracker")

    selected_date = st.date_input("Select Date", value=datetime.today()).strftime("%Y-%m-%d")
    st.markdown(f"### Tasks for {selected_date}")

    selected_tasks = []
    total_score = 0
    category_scores = {}

    for _, row in checklist_df.iterrows():
        category = row["Category"]
        task = row["Task"]
        score = row["Score"]
        if st.checkbox(f"**{category}** - {task} ({score} pts)", key=f"{selected_date}_{task}"):
            selected_tasks.append([selected_date, category, task, score])
            total_score += score
            category_scores[category] = category_scores.get(category, 0) + score

    st.markdown(f"### 🎯 Total Score: **{total_score} / 100**")
    if category_scores:
        st.markdown("#### 📂 Category-wise Score")
        for cat, val in category_scores.items():
            st.write(f"- {cat}: {val} pts")

    if st.button("💾 Save Progress"):
        if selected_tasks:
            sheet.append_rows(selected_tasks, value_input_option="USER_ENTERED")
            st.success("Progress saved to Google Sheet!")
        else:
            st.warning("No tasks selected to save.")

# -------------------- SUMMARY DASHBOARD --------------------
elif page == "📊 Summary Dashboard":
    st.title("📊 Summary Dashboard")

    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df["Date"] = pd.to_datetime(df["Date"])
    except Exception as e:
        st.error("Error loading data from Google Sheet.")
        st.stop()

    filter_type = st.selectbox("Select Period", ["Last 7 Days", "Last 30 Days", "Custom Range"])
    today = datetime.today().date()

    if filter_type == "Last 7 Days":
        start_date, end_date = today - timedelta(days=6), today
    elif filter_type == "Last 30 Days":
        start_date, end_date = today - timedelta(days=29), today
    else:
        col1, col2 = st.columns(2)
        start_date = col1.date_input("From", value=today - timedelta(days=6))
        end_date = col2.date_input("To", value=today)

    filtered_df = df[(df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)]

    st.subheader("🔘 Category-wise Scores (for selected period)")
    max_scores = checklist_df.groupby("Category")["Score"].sum()
    day_count = (end_date - start_date).days + 1
    cols = st.columns(3)
    for i, cat in enumerate(["Physical", "Lifestyle", "Mind"]):
        with cols[i]:
            cat_score = filtered_df[filtered_df["Category"] == cat]["Score"].sum()
            max_cat = max_scores.get(cat, 0) * day_count
            percent = int((cat_score / max_cat) * 100) if max_cat else 0
            st.metric(f"{cat}", f"{percent}%")

    st.subheader("📈 Daily Total Score Trend")
    trend = filtered_df.groupby(filtered_df["Date"].dt.date)["Score"].sum().reset_index()
    fig, ax = plt.subplots()
    ax.bar(trend["Date"], trend["Score"], color="#4CAF50")
    ax.set_xlabel("Date")
    ax.set_ylabel("Total Score")
    ax.set_title("Total Score by Date")
    ax.grid(True)
    plt.xticks(rotation=45)
    st.pyplot(fig)
