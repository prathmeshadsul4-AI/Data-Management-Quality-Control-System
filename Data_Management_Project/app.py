import os
import streamlit as st
import pandas as pd
import sqlite3
import re
from datetime import datetime

# =========================================================
# DATABASE
# =========================================================

DB_NAME = "data_management.db"


def init_database():
    conn = sqlite3.connect(DB_NAME)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            customer_id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            city TEXT,
            department TEXT,
            status TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def seed_sample_data():
    conn = sqlite3.connect(DB_NAME)
    record_count = conn.execute(
        "SELECT COUNT(*) FROM records"
    ).fetchone()[0]
    conn.close()

    if record_count > 0:
        return

    sample_path = os.path.join(
        "data",
        "sample_customers.csv"
    )

    if not os.path.exists(sample_path):
        return

    sample_df = pd.read_csv(sample_path)
    cleaned_df = clean_data(sample_df)
    save_to_database(cleaned_df)


# =========================================================
# DATA CLEANING
# =========================================================

def clean_data(df):

    df = df.copy()

    # Clean column names
    df.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        for column in df.columns
    ]

    # Remove extra spaces
    for column in df.columns:
        if pd.api.types.is_object_dtype(df[column]) or pd.api.types.is_string_dtype(df[column]):
            df[column] = df[column].fillna("").astype(str).str.strip()

    # Standardize names
    if "name" in df.columns:
        df["name"] = df["name"].fillna("").astype(str).str.title()

    # Standardize city
    if "city" in df.columns:
        df["city"] = df["city"].fillna("").astype(str).str.title()

    # Standardize department
    if "department" in df.columns:
        df["department"] = df["department"].fillna("").astype(str).str.title()

    # Convert email to lowercase
    if "email" in df.columns:
        df["email"] = df["email"].fillna("").astype(str).str.lower()

    # Remove symbols from phone numbers
    if "phone" in df.columns:
        df["phone"] = df["phone"].fillna("").astype(str).str.replace(
            r"\D",
            "",
            regex=True
        )

    return df


# =========================================================
# DATA VALIDATION
# =========================================================

def validate_email(email):

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return bool(
        re.match(pattern, str(email))
    )


def validate_phone(phone):

    return bool(
        re.match(r"^\d{10}$", str(phone))
    )


def validate_data(df):

    df = df.copy()

    # Email validation
    df["email_valid"] = df["email"].apply(
        validate_email
    )

    # Phone validation
    df["phone_valid"] = df["phone"].apply(
        validate_phone
    )

    # Missing values
    df["missing_fields"] = (
        df.isna().sum(axis=1)
        +
        df.astype(str).eq("").sum(axis=1)
    )

    # Duplicate Customer IDs
    df["duplicate_id"] = df[
        "customer_id"
    ].duplicated(
        keep=False
    )

    # Final quality status
    df["data_quality"] = df.apply(
        lambda row:

        "Valid"

        if (
            row["email_valid"]
            and
            row["phone_valid"]
            and
            row["missing_fields"] == 0
            and
            not row["duplicate_id"]
        )

        else "Needs Review",

        axis=1
    )

    return df


# =========================================================
# SAVE DATA TO DATABASE
# =========================================================

def save_to_database(df):

    conn = sqlite3.connect(DB_NAME)

    for _, row in df.iterrows():

        conn.execute(
            """
            INSERT OR REPLACE INTO records
            (
                customer_id,
                name,
                email,
                phone,
                city,
                department,
                status,
                created_at
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,

            (
                row["customer_id"],
                row["name"],
                row["email"],
                row["phone"],
                row["city"],
                row.get(
                    "department",
                    ""
                ),
                row.get(
                    "status",
                    "Active"
                ),
                datetime.now().isoformat()
            )
        )

    conn.commit()
    conn.close()


# =========================================================
# INITIALIZE DATABASE
# =========================================================

init_database()
seed_sample_data()


# =========================================================
# STREAMLIT CONFIGURATION
# =========================================================

st.set_page_config(

    page_title="Data Management System",

    page_icon="📊",

    layout="wide"
)


# =========================================================
# TITLE
# =========================================================

st.title(
    "📊 Data Management & Quality Control System"
)

st.write(
    """
    Manage, clean, validate, store and analyze
    business data using an automated data-management
    workflow.
    """
)


st.divider()


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("📌 Navigation")

page = st.sidebar.radio(

    "Select Module",

    [
        "Dashboard",
        "Data Import",
        "Data Quality",
        "Database",
        "Search Data",
        "Reports"
    ]
)


# =========================================================
# DASHBOARD
# =========================================================

if page == "Dashboard":

    st.header("📊 Data Management Dashboard")

    conn = sqlite3.connect(DB_NAME)

    data = pd.read_sql_query(
        "SELECT * FROM records",
        conn
    )

    conn.close()

    total_records = len(data)

    total_cities = (
        data["city"].nunique()
        if not data.empty
        else 0
    )

    total_departments = (
        data["department"].nunique()
        if not data.empty
        else 0
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Records",
        total_records
    )

    col2.metric(
        "Cities",
        total_cities
    )

    col3.metric(
        "Departments",
        total_departments
    )

    st.divider()

    if not data.empty:

        st.subheader(
            "Department Distribution"
        )

        department_data = (
            data["department"]
            .value_counts()
        )

        st.bar_chart(
            department_data
        )

        st.subheader(
            "Stored Records"
        )

        st.dataframe(
            data,
            use_container_width=True
        )

    else:

        st.info(
            "No data available. "
            "Go to Data Import and upload a CSV or Excel file."
        )


# =========================================================
# DATA IMPORT
# =========================================================

elif page == "Data Import":

    st.header("📥 Import Data")

    uploaded_file = st.file_uploader(

        "Upload CSV or Excel file",

        type=[
            "csv",
            "xlsx"
        ]
    )

    if uploaded_file:

        # Read CSV
        if uploaded_file.name.endswith(
            ".csv"
        ):

            raw_data = pd.read_csv(
                uploaded_file
            )

        # Read Excel
        else:

            raw_data = pd.read_excel(
                uploaded_file
            )

        st.subheader(
            "Raw Data"
        )

        st.dataframe(
            raw_data,
            use_container_width=True
        )

        st.write(
            f"Total Rows: **{len(raw_data)}**"
        )

        # Clean data
        cleaned_data = clean_data(
            raw_data
        )

        st.subheader(
            "Cleaned Data"
        )

        st.dataframe(
            cleaned_data,
            use_container_width=True
        )

        st.success(
            "Data cleaning completed!"
        )


# =========================================================
# DATA QUALITY
# =========================================================

elif page == "Data Quality":

    st.header(
        "🔍 Data Quality Analysis"
    )

    uploaded_file = st.file_uploader(

        "Upload data for quality analysis",

        type=[
            "csv",
            "xlsx"
        ]
    )

    if uploaded_file:

        if uploaded_file.name.endswith(
            ".csv"
        ):

            raw_data = pd.read_csv(
                uploaded_file
            )

        else:

            raw_data = pd.read_excel(
                uploaded_file
            )

        cleaned_data = clean_data(
            raw_data
        )

        required_columns = [

            "customer_id",
            "name",
            "email",
            "phone",
            "city"

        ]

        missing_columns = [

            column

            for column in required_columns

            if column not in cleaned_data.columns

        ]

        if missing_columns:

            st.error(
                "Missing columns: "
                +
                ", ".join(
                    missing_columns
                )
            )

        else:

            result = validate_data(
                cleaned_data
            )

            # Metrics
            total = len(result)

            valid = int(
                (
                    result["data_quality"]
                    == "Valid"
                ).sum()
            )

            review = int(
                (
                    result["data_quality"]
                    == "Needs Review"
                ).sum()
            )

            duplicates = int(
                result["duplicate_id"]
                .sum()
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Total Records",
                total
            )

            col2.metric(
                "Valid Records",
                valid
            )

            col3.metric(
                "Needs Review",
                review
            )

            col4.metric(
                "Duplicates",
                duplicates
            )

            st.divider()

            st.subheader(
                "Quality Analysis"
            )

            st.dataframe(
                result,
                use_container_width=True
            )

            # Valid records
            valid_records = result[
                result["data_quality"]
                == "Valid"
            ]

            # Remove helper columns
            database_data = valid_records.drop(

                columns=[
                    "email_valid",
                    "phone_valid",
                    "missing_fields",
                    "duplicate_id",
                    "data_quality"
                ],

                errors="ignore"
            )

            st.subheader(
                "Store Valid Records"
            )

            if st.button(
                "💾 Store Valid Records"
            ):

                save_to_database(
                    database_data
                )

                st.success(
                    f"{len(database_data)} "
                    "valid records stored successfully!"
                )

            # Download report
            report = result.to_csv(
                index=False
            )

            st.download_button(

                "⬇️ Download Quality Report",

                report,

                "data_quality_report.csv",

                "text/csv"
            )


# =========================================================
# DATABASE
# =========================================================

elif page == "Database":

    st.header(
        "🗄️ Database Records"
    )

    conn = sqlite3.connect(
        DB_NAME
    )

    data = pd.read_sql_query(

        """
        SELECT *
        FROM records
        ORDER BY created_at DESC
        """,

        conn
    )

    conn.close()

    if data.empty:

        st.info(
            "Database is empty."
        )

    else:

        st.dataframe(
            data,
            use_container_width=True
        )

        csv_data = data.to_csv(
            index=False
        )

        st.download_button(

            "⬇️ Export Database",

            csv_data,

            "database_export.csv",

            "text/csv"
        )


# =========================================================
# SEARCH
# =========================================================

elif page == "Search Data":

    st.header(
        "🔎 Search Records"
    )

    search = st.text_input(
        "Search by name, email, city or department"
    )

    conn = sqlite3.connect(
        DB_NAME
    )

    data = pd.read_sql_query(
        "SELECT * FROM records",
        conn
    )

    conn.close()

    if not data.empty:

        if search:

            search_result = data[
                data.astype(str)
                .apply(

                    lambda column:

                    column.str.contains(

                        search,

                        case=False,

                        na=False

                    )

                )
                .any(axis=1)
            ]

        else:

            search_result = data

        st.dataframe(

            search_result,

            use_container_width=True
        )

        st.write(
            f"Records Found: **{len(search_result)}**"
        )

    else:

        st.info(
            "No records available."
        )


# =========================================================
# REPORTS
# =========================================================

elif page == "Reports":

    st.header(
        "📈 Data Management Reports"
    )

    conn = sqlite3.connect(
        DB_NAME
    )

    data = pd.read_sql_query(
        "SELECT * FROM records",
        conn
    )

    conn.close()

    if data.empty:

        st.info(
            "No data available for reports."
        )

    else:

        # Department report
        st.subheader(
            "Department Report"
        )

        department_report = (

            data
            .groupby("department")
            .size()
            .reset_index(
                name="Total Records"
            )

        )

        st.dataframe(
            department_report,
            use_container_width=True
        )

        st.bar_chart(

            department_report.set_index(
                "department"
            )
        )

        # City report
        st.subheader(
            "City Report"
        )

        city_report = (

            data
            .groupby("city")
            .size()
            .reset_index(
                name="Total Records"
            )

        )

        st.dataframe(
            city_report,
            use_container_width=True
        )

        st.bar_chart(

            city_report.set_index(
                "city"
            )
        )

        # Export
        report_csv = data.to_csv(
            index=False
        )

        st.download_button(

            "⬇️ Download Report",

            report_csv,

            "data_management_report.csv",

            "text/csv"
        )
        