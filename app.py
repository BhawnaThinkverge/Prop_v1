import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np
import requests
import io
from docx import Document
from PyPDF2 import PdfReader
from num2words import num2words
import datetime as dt
import os
from dotenv import load_dotenv
import glob
import time
import json
from urllib.parse import urljoin
import fitz 
import pytesseract
from PIL import Image, ImageOps
from langchain_groq import ChatGroq
from typing import Optional, List, Tuple, Dict, Any
import logging
from io import BytesIO
import re
from pydantic import BaseModel, Field
import pdfplumber
import camelot
from pdf2image import convert_from_bytes
import platform
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from datetime import date, datetime
from bs4 import BeautifulSoup
from sqlalchemy import create_engine







# Try optional AI deps (app continues even if missing)
try:
    from langchain_core.prompts import PromptTemplate
    from langchain.chains import LLMChain
    from langchain_huggingface import HuggingFaceEndpoint
    HAS_LANGCHAIN = True
except Exception:
    HAS_LANGCHAIN = False

BACKEND_BASE_URL = os.getenv("BANK_AUCTION_INSIGHTS_API_URL", "http://localhost:8000")
AUCTION_INSIGHTS_ENDPOINT = "/auction-insights"


    





# Load environment variables
load_dotenv()
HF_API_KEY = (os.getenv("HF_API_KEY") or "").strip()

st.set_page_config(
    page_title="Auction Portal India",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
            font-weight: bold;
        }
        .metric-tile {
            background: linear-gradient(135deg, #ff6b6b 0%, #ff8e53 100%);
            padding: 1rem;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin: 0.5rem 0;
        }
        .analytics-header {
            font-size: 1.8rem;
            color: #2e7d32;
            margin-bottom: 1rem;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.title("🏛️ Auction Portal")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate to:",
    ["🏠 Dashboard", "🔍 Search Analytics", "📊 Basic Analytics","📈 KPI Analytics","📈 KPI Analytics 2","📊 Auction Insights" , "📚 PBN FAQs"],
    index=0
)



#####################################################################################################################################################################
########################################################################################################################################################################
# Load data
@st.cache_data
def load_auction_data():
    csv_path = r"C:\Users\Amit Sharma\ai-platform\frontend\auction_exports\combined_auctions_20250819_154419.csv"
    try:
        # Get list of CSV files
        csv_files = glob.glob("auction_exports/combined_auctions_*.csv")
        
        if not csv_files:
            st.error("❌ No CSV files found in auction_exports folder.")
            return None, None
        
        # Pick the latest file by modification time
        latest_file = max(csv_files, key=os.path.getmtime)
        df = pd.read_csv(latest_file)
        #st.success(f"✅ Loaded data from {latest_file} with {len(df)} records.")
        
        
        

        
        # Rename columns for clarity
        df = df.rename(columns={
            'Auction ID/CIN/LLPIN': 'Auction ID',
            'Bank/Organisation Name': 'Bank',
            'Location-City/District/address': 'Location',
            '_Auction date': 'Auction Date',
            '_Last Date of EMD Submission': 'EMD Submission Date',
            '_Reserve Price': '₹Reserve Price',
            'EMD Amount': '₹EMD Amount',
            'Nature of Assets': 'Nature of Assets',
            'Details URL': 'Details URL',
            'Auction Notice URL': 'Notice URL',
            'Source': 'Source',
            'Notice_date': 'Notice_date'
        })
        # Convert date columns to datetime64[ns] and create duplicate columns for filtering
        df['EMD Submission Date_dt'] = pd.to_datetime(df['EMD Submission Date'], format="%d-%m-%Y", errors='coerce')
        df['Auction Date_dt'] = pd.to_datetime(df['Auction Date'], format="%d-%m-%Y", errors='coerce')
        df['Notice_date'] = pd.to_datetime(df['Notice_date'], format="%d/%m/%Y", errors='coerce')

        # Convert date columns to datetime64[ns] and format as strings for display
        df['EMD Submission Date'] = pd.to_datetime(df['EMD Submission Date'], format="%d-%m-%Y", errors='coerce')
        df['Auction Date'] = pd.to_datetime(df['Auction Date'], format="%d-%m-%Y", errors='coerce')

        # Convert to string format to avoid Arrow conversion issues (only date part)
        df['EMD Submission Date'] = df['EMD Submission Date'].dt.strftime('%d-%m-%Y')
        df['Auction Date'] = df['Auction Date'].dt.strftime('%d-%m-%Y')

        # Use tz-naive date for "today" (as datetime object for consistency in calculations)
        today_date = pd.Timestamp.now(tz=None).date()

        # Calculate days_until_submission safely
        if 'days_until_submission' not in df.columns:
            df['days_until_submission'] = df['EMD Submission Date'].apply(
                lambda x: (pd.to_datetime(x).date() - today_date).days if pd.notna(x) and x != '' else -999
            )
        # Clean numeric columns
        df['₹Reserve Price'] = pd.to_numeric(df['₹Reserve Price'].astype(str).str.replace(r'[,₹\s]', '', regex=True), errors='coerce')
        df['₹EMD Amount'] = pd.to_numeric(df['₹EMD Amount'].astype(str).str.replace(r'[,₹\s]', '', regex=True), errors='coerce')

        # Calculate EMD % and categorize
        # Calculate EMD %
        df['EMD %'] = (df['₹EMD Amount'] / df['₹Reserve Price'] * 100).round(2)

        # Define bins and labels
        bins = [-float("inf"), 5, 10, 15, 20, float("inf")]
        labels = ["<5%", "5-10%", "10-15%", "15-20%", ">20%"]

        # Categorize into bins
        df['EMD % Category'] = pd.cut(df['EMD %'], bins=bins, labels=labels, right=False)
      

        if df['EMD Submission Date'].isna().any():
            pass
            #st.warning("⚠️ Some EMD Submission Dates could not be parsed and are set to NaT. These rows may have invalid data.")

        return df, csv_path
    except Exception as e:
        st.error(f"❌ Failed to load data: {e}")
        return None, None








#####################################################################################################################################################################
########################################################################################################################################################################







# Load data
df, latest_csv = load_auction_data()

# Dashboard Page
if page == "🏠 Dashboard" and df is not None:
    st.markdown('<div class="main-header">🏛️ Auction Portal India</div>', unsafe_allow_html=True)
    #st.markdown(f"**Last Updated:** {latest_csv.split('_')[-1].split('.')[0] if latest_csv else 'Unknown'}")


    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_auctions = len(df)
        st.metric("Total Auctions", total_auctions)
    
    with col2:
        invalid_count = df['EMD Submission Date'].isna().sum()
        st.metric("Invalid EMD Dates", invalid_count)
    
    with col3:
        active_auctions = len(df[df['days_until_submission'] >= 0])
        st.metric("Active Auctions", active_auctions)

    from babel.numbers import format_currency
    import pandas as pd

    def format_indian_currency(value):
        if pd.isna(value) or value <= 0:
            return "N/A"
        # Convert to lakhs or crores
        if value >= 10000000:  # 1 crore = 10 million
            formatted = value / 10000000
            return f"{formatted:.2f} cr"
        elif value >= 100000:  # 1 lakh = 100,000
            formatted = value / 100000
            return f"{formatted:.2f} lakhs"
        else:
            return f"{value:.2f}"

    with col4:
        avg_reserve = df[df['days_until_submission'] >= 0]['₹Reserve Price'].mean()
        formatted_value = format_indian_currency(avg_reserve)
        st.metric("Avg Reserve Price of active auctions", formatted_value)
    # Display filtered data
    filtered_df = df[df['days_until_submission'] >= 0]
    if not filtered_df.empty:
        st.dataframe(filtered_df[['Auction ID', 'Bank', 'Location', 'Auction Date', 'EMD Submission Date',
                                 '₹Reserve Price', '₹EMD Amount', 'EMD %', 'EMD % Category', 'Nature of Assets'
                                 ,   'days_until_submission']],
                     use_container_width=True)
        st.write(f"**Total Auctions (Today or Future):** {len(filtered_df)}")
 
    else:
        st.info("✅ No auctions found for day or future dates.")
        








#####################################################################################################################################################################
########################################################################################################################################################################








# Search Analytics Page
elif page == "🔍 Search Analytics" and df is not None:
    st.markdown('<div class="main-header">🔍 Search Analytics</div>', unsafe_allow_html=True)
    #st.markdown(f"**Last Updated:** {latest_csv.split('_')[-1].split('.')[0] if latest_csv else 'Unknown'}")
    

   

    filtered_df = df[df['days_until_submission'] >= 0].copy()
    

    # Location Filter
    use_location_filter = st.checkbox("Use Location Filter", value=False)
    if use_location_filter:
        unique_locations = sorted(filtered_df['Location'].dropna().unique())
        selected_locations = st.multiselect(
            "Select Locations",
            options=unique_locations,
            default=None
        )
        if selected_locations:
            filtered_df = filtered_df[filtered_df['Location'].isin(selected_locations)]

    # Range Slider for days_until_submission
    use_days_filter = st.checkbox("Use Days Until Submission Filter", value=False)
    if use_days_filter and not filtered_df.empty:
        min_days = int(filtered_df['days_until_submission'].min())
        max_days = int(filtered_df['days_until_submission'].max())
        days_range = st.slider(
            "Filter by Days Until Submission",
            min_value=min_days,
            max_value=max_days,
            value=(min_days, max_days)
        )
        filtered_df = filtered_df[
            (filtered_df['days_until_submission'] >= days_range[0]) &
            (filtered_df['days_until_submission'] <= days_range[1])
        ]

    # Checkbox and Date Input for EMD Submission Date
    use_date_filter = st.checkbox("Use EMD Submission Date Filter", value=False)
    if use_date_filter:
        selected_date = st.date_input("Select EMD Submission Date", value=pd.Timestamp.now(tz=None).date(), disabled=not use_date_filter)
        filtered_df = filtered_df[filtered_df['EMD Submission Date_dt'].dt.date == selected_date]

   # EMD % Filter
    use_emd_percent_filter = st.checkbox("Use EMD % Filter", value=False)
    if use_emd_percent_filter:
        emd_options = ["<5%", "5-10%", "10-15%", "15-20%", ">20%"]
        selected_emd = st.multiselect(
            "Select EMD % Category",
            options=emd_options,
            default=None
        )
        if selected_emd:
            mask = filtered_df['EMD % Category'].str.contains('|'.join(selected_emd), na=False).fillna(False)
            filtered_df = filtered_df[mask]

    # Drop rows with any NaN values across all columns
    #filtered_df = filtered_df.dropna()

    if not filtered_df.empty:
        st.dataframe(filtered_df[['Auction ID', 'Bank', 'Location', 'Auction Date', 'EMD Submission Date',
                                 '₹Reserve Price', '₹EMD Amount', 'EMD %', 'EMD % Category', 'Nature of Assets'
                                 , 'days_until_submission']],
                     use_container_width=True)
        st.write(f"**Total Auctions:** {len(filtered_df)}")
    else:
        st.info("✅ No auctions found with the selected filters.")










#####################################################################################################################################################################
########################################################################################################################################################################


# Basic Analytics Page
elif page == "📊 Basic Analytics" and df is not None:
    st.markdown('<div class="main-header">📊 Basic Analytics</div>', unsafe_allow_html=True)
    
    # Inject custom CSS for improved metric tiles
    st.markdown("""
        <style>
            .metric-grid {
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                padding: 15px;
            }
            .metric-tile {
                background-color: #ffffff;
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: transform 0.2s, box-shadow 0.2s;
                border: 1px solid #e0e0e0;
                flex: 1;
                min-width: 200px;
            }
            .metric-tile:hover {
                transform: translateY(-5px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }
            .metric-tile h3 {
                font-size: 1.5em;
                margin: 0;
                color: #1a73e8;
                font-weight: bold;
            }
            .metric-tile p {
                font-size: 0.9em;
                margin: 5px 0 0 0;
                color: #5f6368;
                font-weight: 500;
            }
        </style>
    """, unsafe_allow_html=True)

    # Row 1: Total Auctions and Active Auctions
    col1_row1, col2_row1 = st.columns(2)
    with col1_row1:
        st.markdown("""
            <div class="metric-tile">
                <h3>{}</h3>
                <p>Total Auctions</p>
            </div>
        """.format(len(df)), unsafe_allow_html=True)
    with col2_row1:
        active_auctions = len(df[df['days_until_submission'] >= 0])
        st.markdown("""
            <div class="metric-tile">
                <h3>{}</h3>
                <p>Active Auctions</p>
            </div>
        """.format(active_auctions), unsafe_allow_html=True)

    # Row 2: Avg Reserve Price (All) and Avg Reserve Price of Active Auctions
    col1_row2, col2_row2 = st.columns(2)
    with col1_row2:
        from babel.numbers import format_currency
        import textwrap
        def format_indian_currency(value):
            if pd.isna(value) or value <= 0:
                return "N/A"
            if value >= 10000000:  # 1 crore = 10 million
                formatted = value / 10000000
                return f"{formatted:.2f} cr"
            elif value >= 100000:  # 1 lakh = 100,000
                formatted = value / 100000
                return f"{formatted:.2f} lakhs"
            else:
                return f"{value:.2f}"
        
        avg_reserve_all = df['₹Reserve Price'].mean()
        formatted_value_all = format_indian_currency(avg_reserve_all)
        st.markdown("""
            <div class="metric-tile">
                <h3>{}</h3>
                <p>Avg Reserve Price (All)</p>
            </div>
        """.format(formatted_value_all), unsafe_allow_html=True)
    with col2_row2:
        avg_reserve_active = df[df['days_until_submission'] >= 0]['₹Reserve Price'].mean()
        formatted_value_active = format_indian_currency(avg_reserve_active)
        st.markdown("""
            <div class="metric-tile">
                <h3>{}</h3>
                <p>Avg Reserve Price of Active Auctions</p>
            </div>
        """.format(formatted_value_active), unsafe_allow_html=True)

    # Row 3: Sum of Reserve Price (All) and Sum of Reserve Price of Active Auctions
    col1_row3, col2_row3 = st.columns(2)
    with col1_row3:
        sum_reserve_all = df['₹Reserve Price'].sum()
        formatted_value_sum_all = format_indian_currency(sum_reserve_all)
        st.markdown("""
            <div class="metric-tile">
                <h3>{}</h3>
                <p>Sum of Reserve Price (All)</p>
            </div>
        """.format(formatted_value_sum_all), unsafe_allow_html=True)
    with col2_row3:
        sum_reserve_active = df[df['days_until_submission'] >= 0]['₹Reserve Price'].sum()
        formatted_value_sum_active = format_indian_currency(sum_reserve_active)
        st.markdown("""
            <div class="metric-tile">
                <h3>{}</h3>
                <p>Sum of Reserve Price of Active Auctions</p>
            </div>
        """.format(formatted_value_sum_active), unsafe_allow_html=True)

    # Row 5: Min and Max of Reserve Price of Active Auctions
    col1_row5, col2_row5 = st.columns(2)
    with col1_row5:
        min_reserve_active = df[df['days_until_submission'] >= 0]['₹Reserve Price']
        if not min_reserve_active.empty:
            min_reserve_active = min_reserve_active[min_reserve_active > 0].min() if (min_reserve_active > 0).any() else float('nan')
        else:
            min_reserve_active = float('nan')
        formatted_min_active = format_indian_currency(min_reserve_active)
        st.markdown("""
            <div class="metric-tile">
                <h3>{}</h3>
                <p>Min of Reserve Price of Active Auctions</p>
            </div>
        """.format(formatted_min_active), unsafe_allow_html=True)
    with col2_row5:
        max_reserve_active = df[df['days_until_submission'] >= 0]['₹Reserve Price'].max()
        formatted_max_active = format_indian_currency(max_reserve_active)
        st.markdown("""
            <div class="metric-tile">
                <h3>{}</h3>
                <p>Max of Reserve Price of Active Auctions</p>
            </div>
        """.format(formatted_max_active), unsafe_allow_html=True)

    st.markdown("---")

    # Top 5 Banks with Min and Max Reserve Price as a DataFrame
    top_banks = df['Bank'].value_counts().head(5).index
    active_df = df[df['days_until_submission'] >= 0]
    bank_stats = []
    for bank in top_banks:
        bank_data = active_df[active_df['Bank'] == bank]['₹Reserve Price']
        min_price = bank_data[bank_data > 0].min() if (bank_data > 0).any() else float('nan')
        max_price = bank_data[bank_data > 0].max() if (bank_data > 0).any() else float('nan')
        bank_stats.append({
            'Bank': bank,
            'Min Reserve Price': min_price,
            'Max Reserve Price': max_price
        })
    bank_df = pd.DataFrame(bank_stats)
    bank_df['Min Reserve Price'] = bank_df['Min Reserve Price'].apply(format_indian_currency)
    bank_df['Max Reserve Price'] = bank_df['Max Reserve Price'].apply(format_indian_currency)
    st.subheader("📈 Top 5 Banks by Reserve Price ")
    st.dataframe(bank_df)

    st.markdown("---")
    # Chart 1: Top 10 Banks by Auction Count
    st.subheader("📈 Top 10 Banks by Auction Count")
    bank_counts = df['Bank'].value_counts().head(10)
    fig1 = px.bar(
        x=bank_counts.values,
        y=bank_counts.index,
        orientation='h',
        title="Top 10 Banks by Auction Count",
        labels={'x': 'Number of Auctions', 'y': 'Bank'},
        color=bank_counts.values,
        color_continuous_scale='viridis'
    )
    fig1.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Average Reserve Price by Location (Top 10)
    st.subheader("💰 Top 10 Locations by Average Reserve Price")
    location_avg = df.groupby('Location')['₹Reserve Price'].mean().sort_values(ascending=False).head(10)
    fig2 = px.bar(
        x=location_avg.apply(format_indian_currency),
        y=location_avg.index,
        orientation='h',
        title="Top 10 Locations by Average Reserve Price",
        labels={'x': 'Average Reserve Price', 'y': 'Location'},
        color=location_avg.values,
        color_continuous_scale='plasma'
    )
    fig2.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

    # Chart 3: EMD Percentage Distribution
    st.subheader("📊 EMD Percentage Distribution")
    emd_dist = df['EMD %'].dropna()
    fig3 = px.histogram(
        emd_dist,
        title="Distribution of EMD Percentages",
        labels={'value': 'EMD %', 'count': 'Frequency'},
        nbins=50,
        color_discrete_sequence=['#ff6b6b']
    )
    fig3.update_layout(height=400)
    st.plotly_chart(fig3, use_container_width=True)

    # Chart 4: Auctions Over Time
    st.subheader("📅 Auction Trends Over Time")
    if not df['Auction Date_dt'].isna().all():
        df_time = df.dropna(subset=['Auction Date_dt']).copy()
        df_time['Month'] = df_time['Auction Date_dt'].dt.to_period('M').dt.to_timestamp()
        monthly_auctions = df_time.groupby('Month').size().reset_index(name='Count')
        
        fig4 = px.line(
            monthly_auctions,
            x='Month',
            y='Count',
            title="Number of Auctions per Month",
            labels={'Count': 'Number of Auctions', 'Month': 'Month'}
        )
        fig4.update_traces(line_color='#2e7d32', line_width=3)
        fig4.update_layout(height=400)
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No valid auction dates available for time trend analysis.")

    # Chart 5: Reserve Price vs EMD Amount Scatter
    st.subheader("💸 Reserve Price vs EMD Amount")
    scatter_data = df[df['days_until_submission'] >= 0].dropna(subset=['₹Reserve Price', '₹EMD Amount'])
    if not scatter_data.empty:
        fig5 = px.scatter(
            scatter_data,
            x='₹Reserve Price',
            y='₹EMD Amount',
            title="Reserve Price vs EMD Amount",
            labels={'x': 'Reserve Price (₹)', 'y': 'EMD Amount (₹)'},
            opacity=0.6,
            color='EMD %',
            color_continuous_scale='viridis'
        )
        combined_text = scatter_data.apply(lambda row: f"{format_indian_currency(row['₹Reserve Price'])} / {format_indian_currency(row['₹EMD Amount'])}", axis=1)
        fig5.update_traces(text=combined_text, textposition='top center')
        fig5.update_layout(height=500)
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("No valid price data available for scatter plot.")

#####################################################################################################################################################################
########################################################################################################################################################################      

# Sidebar Navigation (update the radio options)


# ... (existing code for other pages)

# KPI Analytics Page
elif page == "📈 KPI Analytics" and df is not None:
    st.markdown('<div class="main-header">📈 KPI Analytics</div>', unsafe_allow_html=True)

    # Custom CSS for hoverable tooltips and card styling
    st.markdown("""
        <style>
            .metric-tile {
                background-color: #ffffff;
                padding: 1.5rem;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                position: relative;
                transition: transform 0.2s;
            }
            .metric-tile:hover {
                transform: scale(1.05);
            }
            .tooltip {
                visibility: hidden;
                opacity: 0;
                transition: opacity 0.3s;
                position: absolute;
                z-index: 10;
                background-color: #1f2937;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-size: 0.9rem;
                max-width: 300px;
                bottom: 100%;
                left: 50%;
                transform: translateX(-50%);
            }
            .metric-tile:hover .tooltip {
                visibility: visible;
                opacity: 1;
            }
            .main-header {
                font-size: 2rem;
                font-weight: bold;
                text-align: center;
                margin-bottom: 2rem;
                color: #1f2937;
            }
            .section-header {
                font-size: 1.5rem;
                font-weight: 600;
                margin-top: 2rem;
                margin-bottom: 1rem;
                color: #1f2937;
            }
        </style>
    """, unsafe_allow_html=True)

    # Filter for active auctions
    active_df = df[df['days_until_submission'] >= 0]
    active_df1 = active_df[active_df["Source"] != "Albion"]

    if not active_df.empty:
        # Existing KPIs
        total_auctions = len(active_df1)
        compliant_auctions = len(active_df1[active_df1['Notice URL'] != 'URL 2_if available'])
        notice_compliance_rate = (compliant_auctions / total_auctions * 100) if total_auctions > 0 else 0

        active_df1['timeliness_days'] = (active_df1['Auction Date_dt'] - active_df['Notice_date']).dt.days
        min_days = active_df1['timeliness_days'].min()
        median_days = active_df1['timeliness_days'].median()
        p95_days = active_df1['timeliness_days'].quantile(0.95)

        error_rate = (active_df.isna().any(axis=1).sum() / len(active_df)) * 100

        # Hardcoded values for new KPIs (realistic random values)
        title_artefact_completeness = 87.3
        litigation_stay_rate = 4.8
        appeal_challenge_rate = 2.1
        grievance_closure_sla = 95.7
        audit_trail_completeness = 98.2
        reserve_accuracy_error = 7.4
        valuation_alignment = 89.6
        bid_depth = "Avg: 3.2, P50: 3, P90: 5"
        reserve_hit_rate = 78.9
        price_discovery_spread = 0.15
        elasticity_participation = 0.08
        repossession_auction_tat = "Min: 45, Median: 62, P95: 90"
        re_auction_rate = 12.5
        cancellation_no_bid_rate = 8.3
        recovery_ratio = 75.2
        recovery_velocity = "₹1.2M per day / ₹108M per quarter"
        cost_to_recover = 3.7
        re_auction_cost_drag = "Extra ₹0.05 per ₹ recovered"

        # Display Legal & Compliance KPIs
        st.markdown('<div class="section-header">Legal & Compliance KPIs</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Notice Compliance Rate</h3>
                    <p>{notice_compliance_rate:.1f}%</p>
                    <div class="tooltip">% auctions whose statutory notice/ publication/ possession steps meet applicable norms. Definition: compliant_auctions ÷ total_auctions.</div>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Disclosure Timeliness (Days)</h3>
                    <p>Min: {min_days}, Median: {median_days}, P95: {p95_days}</p>
                    <div class="tooltip">auction_date − notice_publish_date</div>
                </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Title/Artefact Completeness Index</h3>
                    <p>{title_artefact_completeness}</p>
                    <div class="tooltip">Weighted score for presence & quality of deed extracts, encumbrance certs, site photos, geo-tags, reserves, terms. Definition: Σ(weight_i × present_i ÷ required_i).</div>
                </div>
            """, unsafe_allow_html=True)

        col4, col5, col6 = st.columns(3)
        with col4:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Litigation/Stay Incidence Rate</h3>
                    <p>{litigation_stay_rate}%</p>
                    <div class="tooltip">% auctions affected by court/DRT/DRAT stays or material disputes. Definition: stayed_listings ÷ total_listings.</div>
                </div>
            """, unsafe_allow_html=True)

        with col5:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Appeal/Challenge Rate (post-sale)</h3>
                    <p>{appeal_challenge_rate}%</p>
                    <div class="tooltip">% concluded sales that face legal challenges within X days. Definition: challenged_sales ÷ concluded_sales.</div>
                </div>
            """, unsafe_allow_html=True)

        with col6:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Grievance Closure SLA %</h3>
                    <p>{grievance_closure_sla}%</p>
                    <div class="tooltip">% grievances resolved within policy SLA. Definition: closed_within_SLA ÷ total_grievances.</div>
                </div>
            """, unsafe_allow_html=True)

        col7, col8, _ = st.columns(3)
        with col7:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Audit-Trail Completeness</h3>
                    <p>{audit_trail_completeness}%</p>
                    <div class="tooltip">% auctions with full system logs & decision artifacts (who/what/when). Definition: auctions_with_full_logs ÷ total_auctions.</div>
                </div>
            """, unsafe_allow_html=True)

        with col8:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Data Quality Error Rate</h3>
                    <p>{error_rate:.1f}%</p>
                    <div class="tooltip">Percentage of records with missing or invalid data.</div>
                </div>
            """, unsafe_allow_html=True)

        # Display Pricing & Market-Efficiency KPIs
        st.markdown('<div class="section-header">Pricing & Market-Efficiency KPIs</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Reserve Accuracy Error %</h3>
                    <p>{reserve_accuracy_error}%</p>
                    <div class="tooltip">How close reserve was to market outcome. Definition: |hammer − reserve| ÷ reserve.</div>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Valuation Alignment % (Independent/Circle)</h3>
                    <p>{valuation_alignment}%</p>
                    <div class="tooltip">Sanity check vs independent valuation or govt circle rate. Definition: hammer ÷ benchmark_value.</div>
                </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Bid Depth</h3>
                    <p>{bid_depth}</p>
                    <div class="tooltip">Avg number of bids per lot; p50/p90 distribution.</div>
                </div>
            """, unsafe_allow_html=True)

        col4, col5, col6 = st.columns(3)
        with col4:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Reserve Hit Rate</h3>
                    <p>{reserve_hit_rate}%</p>
                    <div class="tooltip">% auctions where bidding crossed reserve. Definition: crossed_reserve ÷ total_auctions.</div>
                </div>
            """, unsafe_allow_html=True)

        with col5:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Price Discovery Spread</h3>
                    <p>{price_discovery_spread}</p>
                    <div class="tooltip">(p90 bid − p10 bid) ÷ reserve (volatility proxy).</div>
                </div>
            """, unsafe_allow_html=True)

        with col6:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Elasticity to Participation</h3>
                    <p>{elasticity_participation}</p>
                    <div class="tooltip">∆hammer_uplift per additional qualified bidder (regression slope).</div>
                </div>
            """, unsafe_allow_html=True)

        # Display Time & Process KPIs
        st.markdown('<div class="section-header">Time & Process KPIs</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Repossession→Auction TAT (days)</h3>
                    <p>{repossession_auction_tat}</p>
                    <div class="tooltip">End-to-end pipeline time from repossession completed date.</div>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Re-Auction Rate</h3>
                    <p>{re_auction_rate}%</p>
                    <div class="tooltip">% lots needing re-listing. Definition: reauctioned_listings ÷ total_listings.</div>
                </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Cancellation/No-Bid Rate</h3>
                    <p>{cancellation_no_bid_rate}%</p>
                    <div class="tooltip">% auctions cancelled or with zero qualifying bids.</div>
                </div>
            """, unsafe_allow_html=True)

        # Display Financial Recovery KPIs
        st.markdown('<div class="section-header">Financial Recovery KPIs (business impact)</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Recovery Ratio vs Outstanding</h3>
                    <p>{recovery_ratio}%</p>
                    <div class="tooltip">₹ hammer ÷ ₹ book outstanding (or security value).</div>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Recovery Velocity</h3>
                    <p>{recovery_velocity}</p>
                    <div class="tooltip">₹ recovered per day/quarter.</div>
                </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Cost-to-Recover %</h3>
                    <p>{cost_to_recover}%</p>
                    <div class="tooltip">(notices, hosting, facilitation, legal) ÷ proceeds.</div>
                </div>
            """, unsafe_allow_html=True)

        col4, _, _ = st.columns(3)
        with col4:
            st.markdown(f"""
                <div class="metric-tile">
                    <h3>Re-Auction Cost Drag</h3>
                    <p>{re_auction_cost_drag}</p>
                    <div class="tooltip">Extra cost & time due to re-auctions per ₹ recovered.</div>
                </div>
            """, unsafe_allow_html=True)

        st.write(f"**Active Auctions Analyzed:** {len(active_df)}")
    else:
        st.info("No active auctions available for KPI calculation.")

    st.markdown("---")




#####################################################################################################################################################################
####################################################################################################################################################################

# KPI Analytics Page 2
elif page == "📈 KPI Analytics 2" and df is not None:
    st.markdown('<div class="main-header">KPI Analytics Dashboard</div>', unsafe_allow_html=True)

    # Fancy, modern CSS with a bluish color scheme and glassmorphism
    st.markdown("""
        <style>
            .metric-tile {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                padding: 1.75rem;
                border-radius: 16px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
                position: relative;
                transition: transform 0.4s ease, box-shadow 0.4s ease;
                border: 1px solid rgba(59, 130, 246, 0.2); /* Blue border */
                margin-bottom: 1.5rem;
            }
            .metric-tile:hover {
                transform: translateY(-8px);
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
            }
            .tooltip {
                visibility: hidden;
                opacity: 0;
                transition: opacity 0.4s ease, visibility 0.4s ease;
                position: absolute;
                z-index: 10;
                background: rgba(29, 78, 216, 0.95); /* Deep blue glassmorphism */
                color: #ffffff;
                padding: 12px;
                border-radius: 8px;
                font-size: 0.9rem;
                max-width: 340px;
                bottom: 100%;
                left: 50%;
                transform: translateX(-50%);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            .metric-tile:hover .tooltip {
                visibility: visible;
                opacity: 1;
            }
            .main-header {
                font-size: 2.5rem;
                font-weight: 800;
                text-align: center;
                margin: 2rem 0 3rem 0;
                background: linear-gradient(90deg, #1e40af, #60a5fa); /* Blue gradient */
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            .section-header {
                font-size: 1.9rem;
                font-weight: 700;
                margin: 2.5rem 0 1.5rem 0;
                color: #111827; /* Dark for contrast */
                background: linear-gradient(to right, #3b82f6, #93c5fd); /* Light blue gradient */
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                padding-left: 0.5rem;
            }
            .metric-tile h3 {
                font-size: 1.3rem;
                font-weight: 700;
                color: #111827;
                margin-bottom: 0.75rem;
            }
            .metric-tile p {
                font-size: 1.6rem;
                font-weight: 600;
                color: #2563eb; /* Vibrant blue */
            }
            /* Smooth typography */
            * {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }
        </style>
    """, unsafe_allow_html=True)

    # Hardcoded values for all KPIs (unchanged)
    bank_loan_recovery_rate = 82.5
    bank_portfolio_health_index = 91.2
    bank_default_prediction_accuracy = 88.7
    bank_customer_satisfaction_score = 4.2
    bank_operational_efficiency = 76.4
    bank_risk_exposure_ratio = 12.3
    bank_compliance_audit_score = 95.8
    bank_asset_liquidation_speed = "Min: 30, Median: 45, P95: 60"

    liq_asset_realization_rate = 79.8
    liq_liquidation_tat_days = "Min: 50, Median: 70, P95: 110"
    liq_cost_to_liquidate = 5.2
    liq_successful_closure_rate = 85.6
    liq_stakeholder_satisfaction = 3.9
    liq_dispute_resolution_rate = 92.1
    liq_recovery_vs_valuation = 87.4
    liq_re_liquidation_rate = 9.5

    group_collateral_coverage_ratio = 1.45
    group_aggregate_recovery = "₹500M per quarter"
    group_cross_collateral_efficiency = 84.3
    group_risk_pooling_effectiveness = 78.9
    group_liquidator_performance_variance = 6.7
    group_collateral_valuation_accuracy = 90.5
    group_multi_entity_coordination_score = 88.2
    group_repossession_success_rate = 76.4

    govt_public_auction_success_rate = 81.2
    govt_transparency_index = 94.5
    govt_fund_allocation_efficiency = 89.7
    govt_regulatory_compliance_rate = 97.3
    govt_dispute_incidence = 3.4
    govt_asset_management_tat = "Min: 60, Median: 90, P95: 150"
    govt_stakeholder_engagement_score = 4.1
    govt_recovery_impact = 72.8

    reg_violation_detection_rate = 93.6
    reg_enforcement_action_timeliness = "Min: 10, Median: 20, P95: 45"
    reg_audit_completeness = 98.9
    reg_policy_adherence_rate = 96.4
    reg_risk_mitigation_effectiveness = 85.2
    reg_reporting_accuracy = 97.1
    reg_stakeholder_compliance_training = 88.5
    reg_penalty_recovery_rate = 79.3

    # Display Banks/Organizations KPIs
    st.markdown('<div class="section-header">Banks & Organizations</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Loan Recovery Rate</h3>
                <p>{bank_loan_recovery_rate}%</p>
                <div class="tooltip">Percentage of outstanding loans recovered through auctions and processes. Definition: recovered_amount ÷ outstanding_amount.</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Portfolio Health Index</h3>
                <p>{bank_portfolio_health_index}%</p>
                <div class="tooltip">Overall health score of loan portfolio based on defaults and recoveries.</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Default Prediction Accuracy</h3>
                <p>{bank_default_prediction_accuracy}%</p>
                <div class="tooltip">Accuracy of models predicting loan defaults.</div>
            </div>
        """, unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Customer Satisfaction Score</h3>
                <p>{bank_customer_satisfaction_score}/5</p>
                <div class="tooltip">Average satisfaction score from borrowers and bidders.</div>
            </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Operational Efficiency</h3>
                <p>{bank_operational_efficiency}%</p>
                <div class="tooltip">Efficiency in handling auction operations.</div>
            </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Risk Exposure Ratio</h3>
                <p>{bank_risk_exposure_ratio}%</p>
                <div class="tooltip">Ratio of exposed risk in the portfolio.</div>
            </div>
        """, unsafe_allow_html=True)

    col7, col8, _ = st.columns(3)
    with col7:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Compliance Audit Score</h3>
                <p>{bank_compliance_audit_score}%</p>
                <div class="tooltip">Score from internal and external audits.</div>
            </div>
        """, unsafe_allow_html=True)

    with col8:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Asset Liquidation Speed (Days)</h3>
                <p>{bank_asset_liquidation_speed}</p>
                <div class="tooltip">Time taken to liquidate assets.</div>
            </div>
        """, unsafe_allow_html=True)

    # Display Liquidators KPIs
    st.markdown('<div class="section-header">Liquidators</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Asset Realization Rate</h3>
                <p>{liq_asset_realization_rate}%</p>
                <div class="tooltip">Percentage of asset value realized through liquidation.</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Liquidation TAT (Days)</h3>
                <p>{liq_liquidation_tat_days}</p>
                <div class="tooltip">Turnaround time for liquidation processes.</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Cost to Liquidate (%)</h3>
                <p>{liq_cost_to_liquidate}%</p>
                <div class="tooltip">Costs as a percentage of realized value.</div>
            </div>
        """, unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Successful Closure Rate</h3>
                <p>{liq_successful_closure_rate}%</p>
                <div class="tooltip">Percentage of cases closed successfully.</div>
            </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Stakeholder Satisfaction</h3>
                <p>{liq_stakeholder_satisfaction}/5</p>
                <div class="tooltip">Satisfaction score from involved parties.</div>
            </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Dispute Resolution Rate</h3>
                <p>{liq_dispute_resolution_rate}%</p>
                <div class="tooltip">Percentage of disputes resolved efficiently.</div>
            </div>
        """, unsafe_allow_html=True)

    col7, col8, _ = st.columns(3)
    with col7:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Recovery vs Valuation</h3>
                <p>{liq_recovery_vs_valuation}%</p>
                <div class="tooltip">Realized recovery against initial valuation.</div>
            </div>
        """, unsafe_allow_html=True)

    with col8:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Re-Liquidation Rate</h3>
                <p>{liq_re_liquidation_rate}%</p>
                <div class="tooltip">Percentage of assets requiring re-liquidation.</div>
            </div>
        """, unsafe_allow_html=True)

    # Display Group Liquidators & Collaterals KPIs
    st.markdown('<div class="section-header">Group Liquidators & Collaterals</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Collateral Coverage Ratio</h3>
                <p>{group_collateral_coverage_ratio}</p>
                <div class="tooltip">Ratio of collateral value to outstanding debt.</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Aggregate Recovery</h3>
                <p>{group_aggregate_recovery}</p>
                <div class="tooltip">Total recovery across group entities.</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Cross-Collateral Efficiency</h3>
                <p>{group_cross_collateral_efficiency}%</p>
                <div class="tooltip">Efficiency in utilizing cross-collaterals.</div>
            </div>
        """, unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Risk Pooling Effectiveness</h3>
                <p>{group_risk_pooling_effectiveness}%</p>
                <div class="tooltip">Effectiveness of risk distribution in group.</div>
            </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Liquidator Performance Variance</h3>
                <p>{group_liquidator_performance_variance}%</p>
                <div class="tooltip">Variance in performance across group liquidators.</div>
            </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Collateral Valuation Accuracy</h3>
                <p>{group_collateral_valuation_accuracy}%</p>
                <div class="tooltip">Accuracy of group collateral valuations.</div>
            </div>
        """, unsafe_allow_html=True)

    col7, col8, _ = st.columns(3)
    with col7:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Multi-Entity Coordination Score</h3>
                <p>{group_multi_entity_coordination_score}%</p>
                <div class="tooltip">Score for coordination among group entities.</div>
            </div>
        """, unsafe_allow_html=True)

    with col8:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Repossession Success Rate</h3>
                <p>{group_repossession_success_rate}%</p>
                <div class="tooltip">Percentage of successful repossessions in group.</div>
            </div>
        """, unsafe_allow_html=True)

    # Display Govt Agencies KPIs
    st.markdown('<div class="section-header">Government Agencies</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Public Auction Success Rate</h3>
                <p>{govt_public_auction_success_rate}%</p>
                <div class="tooltip">Percentage of public auctions successfully completed.</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Transparency Index</h3>
                <p>{govt_transparency_index}%</p>
                <div class="tooltip">Index measuring process transparency.</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Fund Allocation Efficiency</h3>
                <p>{govt_fund_allocation_efficiency}%</p>
                <div class="tooltip">Efficiency in allocating funds for auctions.</div>
            </div>
        """, unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Regulatory Compliance Rate</h3>
                <p>{govt_regulatory_compliance_rate}%</p>
                <div class="tooltip">Percentage of compliance with regulations.</div>
            </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Dispute Incidence</h3>
                <p>{govt_dispute_incidence}%</p>
                <div class="tooltip">Percentage of processes with disputes.</div>
            </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Asset Management TAT (Days)</h3>
                <p>{govt_asset_management_tat}</p>
                <div class="tooltip">Time for asset management.</div>
            </div>
        """, unsafe_allow_html=True)

    col7, col8, _ = st.columns(3)
    with col7:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Stakeholder Engagement Score</h3>
                <p>{govt_stakeholder_engagement_score}/5</p>
                <div class="tooltip">Engagement score with stakeholders.</div>
            </div>
        """, unsafe_allow_html=True)

    with col8:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Recovery Impact</h3>
                <p>{govt_recovery_impact}%</p>
                <div class="tooltip">Impact on overall recovery.</div>
            </div>
        """, unsafe_allow_html=True)

    # Display Regulatory Bodies KPIs
    st.markdown('<div class="section-header">Regulatory Bodies</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Violation Detection Rate</h3>
                <p>{reg_violation_detection_rate}%</p>
                <div class="tooltip">Percentage of violations detected promptly.</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Enforcement Action Timeliness (Days)</h3>
                <p>{reg_enforcement_action_timeliness}</p>
                <div class="tooltip">Time taken for enforcement actions.</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Audit Completeness</h3>
                <p>{reg_audit_completeness}%</p>
                <div class="tooltip">Percentage completeness of audits.</div>
            </div>
        """, unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Policy Adherence Rate</h3>
                <p>{reg_policy_adherence_rate}%</p>
                <div class="tooltip">Percentage adherence to policies.</div>
            </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Risk Mitigation Effectiveness</h3>
                <p>{reg_risk_mitigation_effectiveness}%</p>
                <div class="tooltip">Effectiveness in mitigating risks.</div>
            </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Reporting Accuracy</h3>
                <p>{reg_reporting_accuracy}%</p>
                <div class="tooltip">Accuracy of regulatory reports.</div>
            </div>
        """, unsafe_allow_html=True)

    col7, col8, _ = st.columns(3)
    with col7:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Stakeholder Compliance Training</h3>
                <p>{reg_stakeholder_compliance_training}%</p>
                <div class="tooltip">Percentage of stakeholders trained on compliance.</div>
            </div>
        """, unsafe_allow_html=True)

    with col8:
        st.markdown(f"""
            <div class="metric-tile">
                <h3>Penalty Recovery Rate</h3>
                <p>{reg_penalty_recovery_rate}%</p>
                <div class="tooltip">Percentage of penalties recovered.</div>
            </div>
        """, unsafe_allow_html=True)







#####################################################################################################################################################################
########################################################################################################################################################################  

df, latest_csv = load_auction_data()  

LANDING_API_URL = "https://api.va.landing.ai/v1/tools/agentic-document-analysis"
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
VA_API_KEY = st.secrets["VA_API_KEY"]


def clean_units(value):
    if isinstance(value, str):
        value = re.sub(r"\b(lacs?|crores?|rs\.?)\b", "", value, flags=re.IGNORECASE)
        value = value.replace(",", "").strip()
    return value

def normalize_keys(obj):
    if isinstance(obj, dict):
        return {k.strip().lower().replace(" ", "_"): normalize_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_keys(i) for i in obj]
    return obj


def display_insights(insights: dict):
    st.success("Insights generated successfully!")
    
    # Get error reason
    error_reason = insights.get("details") or insights.get("error") or "Reason not available"

    source = str(insights.get("source") or insights.get("auction_platform") or "").lower()
    
    st.markdown("### Auction Summary")
    st.markdown(f"**Corporate Debtor:** {insights.get('corporate_debtor', '')}")
    st.markdown(f"**Auction Date:** {insights.get('auction_date', '')}")
    st.markdown(f"**Auction Time:** {insights.get('auction_time', '')}")
    
    if "albion" in source:
        reserve_price = clean_units(insights.get("reserve_price", ""))
        emd_amount = clean_units(insights.get("emd_amount", ""))
        st.markdown(f"**Reserve Price:** {reserve_price}")
        st.markdown(f"**EMD Amount:** {emd_amount}")
        st.markdown(f"**Location:** {insights.get('location', '')}")
        assets = insights.get("assets", [])
        if assets:
            asset_desc = assets[0].get('asset_description', '')
            st.markdown(f"**Asset Description:** {asset_desc}")

    else:  # IBBI
        st.markdown(f"**Inspection Date:** {insights.get('inspection_date', '')}")
        st.markdown(f"**Inspection Time:** {insights.get('inspection_time', '')}")
        st.markdown(f"**Auction Platform:** {insights.get('auction_platform', '')}")
        st.markdown(f"**Contact Email:** {insights.get('contact_email', '')}")
        st.markdown(f"**Contact Mobile:** {insights.get('contact_mobile', '')}")

        assets = insights.get("assets", [])
        if assets:
            st.markdown("### Assets Information")
            for asset in assets:
                st.markdown(f"**Block Name:** {asset.get('block_name', '')}")
                st.markdown(f"**Description:** {asset.get('asset_description', '')}")
                st.markdown(f"**Reserve Price:** {asset.get('reserve_price', '')}")
                st.markdown(f"**EMD Amount:** {asset.get('emd_amount', '')}")
                st.markdown(f"**Incremental Bid Amount:** {asset.get('incremental_bid_amount', '')}")
                st.markdown("---")

    # Common ranking
    ranking = insights.get("ranking", {})

    if ranking:  # If ranking exists, display normally
        st.markdown("### Auction Ranking")
        st.markdown(f"**Legal Compliance Score:** {ranking.get('legal_compliance_score', f'Missing – {error_reason}')}")
        st.markdown(f"**Economical Score:** {ranking.get('economical_score', f'Missing – {error_reason}')}")
        st.markdown(f"**Market Trends Score:** {ranking.get('market_trends_score', f'Missing – {error_reason}')}")
        st.markdown(f"**Final Score:** {ranking.get('final_score', f'Missing – {error_reason}')}")
        st.markdown(f"**Risk Summary:** {ranking.get('risk_summary', f'Missing – {error_reason}')}")
        
        references = ranking.get("reference_summary") or insights.get("referance summary")
        if references:
            st.markdown("**Reference Summary:**")
            if isinstance(references, str):
                st.markdown(references.replace("\n", " "))
            elif isinstance(references, list):
                for ref in references:
                    st.markdown(f"- {str(ref)}")
        else:
            st.markdown(f"**Reference Summary:** Missing – {error_reason}")

    else:  # ranking missing entirely -> show all fields as missing with reason
        st.markdown("### Auction Ranking")
        st.markdown(f"**Legal Compliance Score:** Missing – {error_reason}")
        st.markdown(f"**Economical Score:** Missing – {error_reason}")
        st.markdown(f"**Market Trends Score:** Missing – {error_reason}")
        st.markdown(f"**Final Score:** Missing – {error_reason}")
        st.markdown(f"**Risk Summary:** Missing – {error_reason}")
        st.markdown(f"**Reference Summary:** Missing – {error_reason}")




@st.cache_resource
def initialize_llm():
    return ChatGroq(
        model="deepseek-r1-distill-llama-70b",
        temperature=0,
        api_key=GROQ_API_KEY,
    )



RISK_CACHE_DIR = "auction_exports" 
RISK_CACHE_FILE = os.path.join(RISK_CACHE_DIR, 'risk_cache.sqlite') 
RISK_CACHE_TTL_DAYS = 1

def load_risk_cache():
    """Loads the risk cache from the SQLite database and cleans old statuses."""
    
    if not os.path.exists(RISK_CACHE_FILE):
        print(f"Cache file not found at: {RISK_CACHE_FILE}")
        # Return an empty DataFrame with the correct columns
        return pd.DataFrame(columns=['auction_id', 'risk_summary', 'last_processed_at', 'insights_json'])
    
    try:
        # Use SQLAlchemy engine for connecting to SQLite file
        from sqlalchemy import create_engine
        engine = create_engine(f'sqlite:///{RISK_CACHE_FILE}')
        df_cache = pd.read_sql('SELECT * FROM risk_insights', engine)
        
        # Clean up old/unknown statuses to "Error" on load
        df_cache['risk_summary'] = df_cache['risk_summary'].replace(
            ['Not Processed', 'Unknown', None, ''], 'Error'
        ).fillna('Error') # Ensure any NaN risk_summary becomes Error
        
        print(f"Cache Size: {len(df_cache)} rows.")
        return df_cache
    except Exception as e:
        print(f"!!! FATAL CACHE LOAD ERROR: {e}")
        # Return empty on error
        return pd.DataFrame(columns=['auction_id', 'risk_summary', 'last_processed_at', 'insights_json'])

def save_risk_cache(df_cache):
    """Saves the risk cache to the SQLite database."""
    try:
        # Create directory if it doesn't exist 
        os.makedirs(RISK_CACHE_DIR, exist_ok=True)
        
        # 🚨 Use SQLite
        from sqlalchemy import create_engine
        engine = create_engine(f'sqlite:///{RISK_CACHE_FILE}')
        
        # Save to SQLite table, replacing the table if it exists
        df_cache.to_sql('risk_insights', engine, if_exists='replace', index=False)
        
        print(f"--------------------------------------------------")
        print(f" SUCCESS: Cache saved to {RISK_CACHE_FILE}")
        print(f"Cache Size: {len(df_cache)} rows.")
        print(f"--------------------------------------------------")
    except Exception as e:
        print(f"--------------------------------------------------")
        print(f"!!! FATAL CACHE SAVE ERROR: {e}")
        print(f"--------------------------------------------------")
        
def extract_pdf_details(pdf_url: str) -> dict:
    response = requests.get(pdf_url)
    response.raise_for_status()

    files = [("pdf", ("document.pdf", response.content, "application/pdf"))]

    schema = {
        "Corporate Debtor": "string",
        "Auction Date": "string",
        "Auction Time": "string",
        "Last Date for EMD Submission": "string",
        "Inspection Date": "string",
        "Inspection Time": "string",
        "Property Description": "string",
        "Auction Platform": "string",
        "Contact Email": "string",
        "Contact Mobile": "string",
        "Assets": [
            {
                "Block Name": "string",
                "Asset Description": "string",
                "Reserve Price": "string",
                "EMD Amount": "string",
                "Incremental Bid Amount": "string"
            }
        ]
    }

    payload = {"fields_schema": schema}
    headers = {"Authorization": f"Bearer {VA_API_KEY}", "Accept": "application/json"}

    r = requests.post(
        LANDING_API_URL,
        headers=headers,
        files=files,
        data={"payload": json.dumps(payload)}
    )
    r.raise_for_status()
    response_json = r.json()

    # Extract both structured schema & raw markdown
    raw_data = response_json.get("data", {})
    markdown = raw_data.get("markdown", "")
    chunks = raw_data.get("chunks", [])


    return {
        "structured": raw_data,
        "markdown": markdown,
        "chunks": chunks,
    }

def regex_preparser(markdown: str, chunks: list) -> dict:
    parsed = {}

    # Corporate Debtor
    debtor_match = re.search(
        r'([A-Z][A-Za-z0-9\s&().,-]*(?:LIMITED|LTD)(?:\s*\(.*?\))?)',
        markdown,
        re.IGNORECASE
    )
    if debtor_match:
        parsed["corporate_debtor"] = debtor_match.group(1).strip()

    # Auction Date Regex 
    auction_date_match = re.search(
        r'(?:Date(?: and Time)? of)?\s*(?:E-?)?Auction[:\-\s]*?(\d{1,2}[./]\d{1,2}[./]\d{4}|\d{1,2}(st|nd|rd|th)?\s+\w+\s*,?\s*\d{4})',
        markdown,
        re.IGNORECASE
    )
    if auction_date_match:
        parsed["auction_date"] = auction_date_match.group(1).strip()
    else:
     
        fallback_date_match = re.search(
            r'(?:auction.*?)(\d{1,2}[./]\d{1,2}[./]\d{4}|\d{1,2}(st|nd|rd|th)?\s+\w+\s*,?\s*\d{4})',
            markdown,
            re.IGNORECASE
        )
        if fallback_date_match:
            parsed["auction_date"] = fallback_date_match.group(1).strip()

  
    time_match = re.search(
        r'(Auction\s*Time[:\-]?\s*)?((?:from\s*)?\d{1,2}(?::\d{2}|\.\d{2})?\s*(?:AM|PM|A\.M\.|P\.M\.)(?:\s*(?:to|–|-)\s*\d{1,2}(?::\d{2}|\.\d{2})?\s*(?:AM|PM|A\.M\.|P\.M\.))?)',
        markdown,
        re.IGNORECASE
    )
    if time_match:
        time_text = time_match.group(2).strip()
        time_text = re.sub(r'(?i)\b(a\.m\.|p\.m\.)\b', lambda m: m.group(1).replace('.', '').upper(), time_text)
        parsed["auction_time"] = time_text

    emails = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", markdown)))
    if emails:
        parsed["contact_email"] = emails

    phone_match = re.search(r'(?:Ph[:\s]*|Phone[:\s]*|Contact[:\s]*|Mob[:\s]*)?(\b[6-9]\d{9}\b)', markdown)
    if phone_match:
        parsed["contact_mobile"] = phone_match.group(1)

    insp_date_match = re.search(r'Inspection Date[:\-]?\s*(.*?)\n', markdown, re.IGNORECASE)
    if insp_date_match:
        parsed["inspection_date"] = insp_date_match.group(1).strip()

    insp_time_match = re.search(r'Inspection Time[:\-]?\s*(.*?)\n', markdown, re.IGNORECASE)
    if insp_time_match:
        parsed["inspection_time"] = insp_time_match.group(1).strip()

    platform_match = re.search(r'(E-Auction Platform.*?)\n', markdown, re.IGNORECASE)
    if platform_match:
        parsed["auction_platform"] = platform_match.group(1).strip()

    notice_date_match = re.search(r'Date\s*:\s*(\d{1,2}[./]\d{1,2}[./]\d{4})', markdown, re.IGNORECASE)
    if notice_date_match:
        parsed["notice_date"] = notice_date_match.group(1).strip()
    
    assets = []
    
 
    for c in chunks:
        if c.get("chunk_type") == "table":
            try:
                soup = BeautifulSoup(c["text"], "html.parser")
                rows = soup.find_all("tr")
                if not rows:
                    continue

                headers = [h.get_text(" ", strip=True).lower() for h in rows[0].find_all(["td", "th"])]

                for r in rows[1:]:
                    cols = [col.get_text(" ", strip=True) for col in r.find_all("td")]
                    if not cols:
                        continue
                    
                    row_data = {headers[i]: cols[i] for i in range(len(headers))}

                    # Prioritize specific keyword matches for dates within the table
                    if "date of publication" in row_data:
                        parsed["notice_date"] = row_data["date of publication"].strip()
                    if "last date for submission of detailed offer" in row_data:
                        # This is a very specific date that should be treated as the auction date
                        parsed["auction_date"] = row_data["last date for submission of detailed offer"].strip()
                    if "last date of submitting eligibility documents" in row_data:
                        # This date is not an auction date, so we store it separately
                        parsed["eligibility_deadline"] = row_data["last date of submitting eligibility documents"].strip()
                    if "last date for inspection / due diligence" in row_data:
                        parsed["inspection_date"] = row_data["last date for inspection / due diligence"].strip()
                    
                  
                    is_asset_row = any(keyword in row_data for keyword in ["asset", "description", "lot", "reserve price", "emd amount"])
                    
                    if is_asset_row:
                        asset_entry = {}
                        for header, value in row_data.items():
                            unit_match = re.search(r'\(([^)]+)\)', header)
                            unit = unit_match.group(1) if unit_match else ""
                            value_with_unit = f"{value.strip()} {unit.strip()}" if unit else value.strip()
                            
                            if "lot" in header or "block" in header or "sr" in header:
                                asset_entry["block_name"] = value_with_unit
                            elif "asset" in header or "details" in header or "description" in header:
                                asset_entry["asset_description"] = value_with_unit
                            elif "reserve" in header:
                                asset_entry["reserve_price"] = value_with_unit
                            elif "emd" in header:
                                asset_entry["emd_amount"] = value_with_unit
                            elif "increment" in header or "bid" in header:
                                asset_entry["incremental_bid_amount"] = value_with_unit
                            
                            elif "quantity" in header:
                                asset_entry["quantity"] = value_with_unit
                            elif "location" in header:
                                asset_entry["location"] = value_with_unit
                            else:
                                asset_entry[header.replace(" ", "_")] = value_with_unit
                        
                        assets.append(asset_entry)

            except Exception as e:
                print(f"Error parsing table: {e}")
                continue

    if assets:
        parsed["assets"] = assets

    if parsed.get("auction_date") and parsed.get("auction_date") in parsed.get("eligibility_deadline", ""):
        parsed["auction_date"] = None
    
    return parsed

def check_final_risk(insights: dict) -> dict:
    ranking = insights.get("ranking", {})
    ref_summary = ranking.get("reference_summary", [])

    #  list of risks.
    risks = []
    
    # Check for statutory compliance risk (notice period).
    notice_period_ok = any(re.search(r'Calculated Days: (\d+)', bullet) and int(re.search(r'Calculated Days: (\d+)', bullet).group(1)) >= 21 for bullet in ref_summary)
    if not notice_period_ok:
        risks.append("high_statutory_non_compliance")

    # Check for missing financials and the mitigating factor.
    has_missing_financials = any("reserve price" in bullet.lower() and "missing" in bullet.lower() for bullet in ref_summary) or \
                             any("emd amount" in bullet.lower() and "missing" in bullet.lower() for bullet in ref_summary)
    
    has_mitigating_factor_bullet = any("Mitigating Factors for Missing Financials: " in bullet for bullet in ref_summary) and \
                                   not any("None" in bullet for bullet in ref_summary)

    if has_missing_financials and not has_mitigating_factor_bullet:
        risks.append("high_missing_financials")
    elif has_missing_financials and has_mitigating_factor_bullet:
        risks.append("average_mitigated_financials")

    #  Check for other high-risk conditions.
    if any("critical documents" in bullet.lower() and "missing" in bullet.lower() for bullet in ref_summary) or \
       any("litigation" in bullet.lower() and "disclosed" in bullet.lower() for bullet in ref_summary) or \
       any("valuation report date" in bullet.lower() and "older" in bullet.lower() for bullet in ref_summary) or \
       any("non-compliant with ibc regulation 33" in bullet.lower() for bullet in ref_summary):
        risks.append("high_other_factors")

    # Check for other average risk conditions.
    if any("non-standard" in bullet.lower() for bullet in ref_summary) or \
       any("short window" in bullet.lower() for bullet in ref_summary) or \
       any("ambiguous" in bullet.lower() for bullet in ref_summary):
        risks.append("average_other_factors")

    # Determine the final risk level based on the collected risks.
    if any(r.startswith("high") for r in risks):
        ranking["legal_compliance_score"] = 2
        ranking["risk_summary"] = "High Risk"
    elif any(r.startswith("average") for r in risks):
        ranking["legal_compliance_score"] = 6
        ranking["risk_summary"] = "Average Risk"
    else:
        ranking["legal_compliance_score"] = 9
        ranking["risk_summary"] = "Low/No Risk"

    # Recalculate final score based on new legal score
    ranking["final_score"] = int((ranking.get("legal_compliance_score", 0) + ranking.get("economical_score", 0) + ranking.get("market_trends_score", 0)) / 3)

    return insights

def generate_risk_insights(auction_json: dict, llm) -> dict:
    import json

    # Extract pre-parsed values
    pre_parsed = {
        k: v for k, v in auction_json.items()
        if k not in ["markdown", "structured", "chunks"]
    }

    # Simplify structured JSON
    structured = auction_json.get("structured", {})
    slim_structured = {
        k: v for k, v in structured.items()
        if isinstance(v, (str, int, float)) or (isinstance(v, list) and len(v) < 10)
    }

    prompt = f"""
You are an expert financial analyst specializing in Indian auction notices.

Here are the pre-parsed values (from regex):
{json.dumps(pre_parsed, indent=2)}

Here is a simplified version of structured JSON:
{json.dumps(slim_structured, indent=2)}

Analyze this information. Extract missing fields if possible, normalize, and report on the auction's characteristics.
Return a JSON object with the following fields:

- corporate_debtor
- auction_date (Only include if the date is explicitly labeled as "Auction Date", "E-Auction Date", or "Date of Auction" or "Date and Time of E-Auction" Otherwise, **return null.**)
- auction_time (only if explicitly mentioned in the notice, otherwise leave null or omit)
- inspection_date
- inspection_time
- auction_platform
- contact_email
- contact_mobile
- assets (list with block_name, description, reserve_price, emd_amount, incremental_bid_amount)
  * For financial fields (reserve_price, emd_amount, incremental_bid_amount), **ensure units (e.g., 'Lacs') are included** with the numerical value. If Unit is not Explicitly mention, does not provide unit then.
  * If a financial field is not explicitly mentioned, return null or leave it blank.
IMPORTANT INSTRUCTION: Before generating the JSON, carefully check if the source document explicitly mentions a date for the "auction" or "e-auction." If no such date is found, you MUST return null for the `auction_date` field in the final JSON. Do NOT use dates from other fields like "eligibility documents" or "inspection" to fill this field.

Provide an initial, unvalidated ranking of the auction based on the three components:
- **Legal Compliance:** Score 0-10, based on compliance with legal standards.
- **Economical Point of View:** Score 0-10, based on asset value and market context.
- **Market Trends:** Score 0-10, based on timing and location factors.

The ranking object must contain these fields:
- legal_compliance_score (int)
- economical_score (int)
- market_trends_score (int)
- final_score (int, simple average of the three components)
- risk_summary (string: "High Risk", "Average Risk", or "Low/No Risk")
- reference_summary (list of 11 strings)

**Reference Summary - Auditable Report (exactly 11 bullet points):**

1. **Primary Risk & Evidence:** State the most critical issue found. Explicitly list any non-standard emails from the notice (e.g., 'AVERAGE RISK: The contact emails 'liquidatorkedia@gmail.com' are non-standard.'). Also, **if reserve price or EMD is not explicitly mentioned, state if the notice provides a clear channel (like an email) to obtain this information by quoting the exact line (e.g., 'The detailed Terms & Conditions...shall be provided upon receipt of mail...').**
2. **Justification of Primary Risk:** Explain the impact (e.g., of using non-institutional domains).
3. **Statutory Compliance:** Report on legal defects by CITING THE LEGAL STANDARD AND THE FULL PERIOD. EXPLICITLY state the notice date (from the provided JSON), auction date, and the calculated number of days.
** If the calculated number of days is >= 21 , then notice complies with legal standards of minimum 21 days notice period under the Insolvency and Bankruptcy Code, 2016, otherwise if it is less than 21 days explicitly mention non-compliance. 
4. **Authorization & Auction Authority:** State the liquidator's name, their appointing authority, the exact legal order, and the auction service provider.
5. **Document Sufficiency:** Use the exact format: "Critical documents like [list of documents] are present. Minor annexures like [list of minor annexures] are missing."
6. **Valuation:** Explicitly state the Reserve Price and mention if it aligns with market norms.
7. **Process/Timeline:** Report on the EMD window. State the EMD deadline and reference the calculated days from the input JSON. Use the phrases: "ample time is provided for bidders to arrange EMD" (for >21 days) or "short window may pressure bidders" (for <21 days).
8. **Listing Quality:** Explicitly list specific data points that make the listing quality sufficient or poor.
9. **Legal Title & Ownership:** State whether the notice mentions supporting ownership documents.
10. **Known Litigation/Encumbrance:** State whether litigation is mentioned.
11. **IBC Regulation 33 Compliance:** Explicitly state if reserve price, EMD, bid deadlines, and terms of payment are present. If missing, declare non-compliant.
12. **Mitigating Factors for Missing Financials:** If the notice is missing Reserve Price or EMD, explicitly quote the sentence from the notice that provides a way to obtain these details (e.g., 'The detailed Terms & Conditions...shall be provided upon receipt of mail...'). If no such sentence exists, state 'None'.
OUTPUT INSTRUCTIONS (IMPORTANT):
Your entire response MUST be a single valid JSON object with the specified structure. Do not include any text outside of this JSON.
"""
    # Call LLM
    messages = [{"role": "user", "content": prompt}]
    retries = 3
    for attempt in range(retries):
        try:
            resp = llm.invoke(messages, response_format={"type": "json_object"})
            raw_output = resp.content
            break
        except Exception as e:
            if attempt == retries - 1:
                return {"error": f"API call failed after {retries} retries", "details": str(e)}
            time.sleep(2)
    try:
        if isinstance(raw_output, str):
            parsed = json.loads(raw_output)
        elif isinstance(raw_output, dict):
            parsed = raw_output
        else:
            return {"error": "Unexpected response type", "raw": str(raw_output)}
            
        parsed.setdefault("ranking", {})
        ranking = parsed["ranking"]
        ranking.setdefault("legal_compliance_score", 0)
        ranking.setdefault("economical_score", 0)
        ranking.setdefault("market_trends_score", 0)
        ranking.setdefault("final_score", 0)
        ranking.setdefault("risk_summary", "Not available")
        ranking.setdefault("reference_summary", [])

        
        if not pre_parsed.get("auction_time") and "auction_time" not in parsed:
            parsed["auction_time"] = None
        
        
        parsed = check_final_risk(parsed)

        return parsed

    except Exception:
        return {"error": "Invalid JSON", "raw": raw_output}

def generate_auction_insights(corporate_debtor: str, auction_data: dict, llm, include_markdown: bool = False) -> dict:
    """
    function to generate insights for IBBI auctions by extracting details from a PDF.
    """
    try:
        auction_notice_url = auction_data.get("notice_url") or auction_data.get("auction_notice_url")
        if not auction_notice_url or "url 2_if available" in str(auction_notice_url).lower():
            return {"status": "error", "message": "IBBI source but no valid Auction Notice Url"}

        details = extract_pdf_details(auction_notice_url)
        pre_parsed = regex_preparser(details.get("markdown", ""), details.get("chunks", []))

        if corporate_debtor:
            pre_parsed["corporate_debtor"] = corporate_debtor.strip()

        emd_submission_date_str = pre_parsed.get("emd_submission_date")
        notice_date_str = pre_parsed.get("notice_date")

        if emd_submission_date_str and notice_date_str:
            try:
                
                emd_submission_date = datetime.datetime.strptime(emd_submission_date_str, '%d-%m-%Y').date()
                notice_date = datetime.datetime.strptime(notice_date_str, '%d/%m/%Y').date()

                # Calculate the difference in days
                emd_window_days = (emd_submission_date - notice_date).days
                
                # Add the calculated value to the dictionary
                pre_parsed["emd_window_days"] = emd_window_days
                
            except ValueError:
                # Handle cases where the date format is unexpected
                pre_parsed["emd_window_days"] = None
        else:
            pre_parsed["emd_window_days"] = None

        merged = {**details, **pre_parsed}
        merged = normalize_keys(merged)

        if not include_markdown:
            merged.pop("markdown", None)
            merged.pop("chunks", None)

        insights = generate_risk_insights(merged, llm)
        insights = normalize_keys(insights)

        if corporate_debtor:
            insights["corporate_debtor"] = corporate_debtor.strip()

        merged.update(insights)
        return {"status": "success", "insights": merged}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def process_single_auction_row(auction_row, llm):
    auction_id = str(auction_row.get("auction_id", "UNKNOWN")).strip()
    if auction_id == "UNKNOWN" or not auction_id:
        # fallback auction_id if missing
        debtor = (auction_row.get("corporate_debtor") or "unknown_debtor").replace(" ", "_")
        auction_id = f"{debtor}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    result_row = {
        "auction_id": auction_id,
        "risk_summary": "Unknown",
        "last_processed_at": datetime.utcnow().isoformat(),
        "insights_json": ""
    }

    try:
        res = generate_auction_insights(
            auction_row.get("corporate_debtor", ""),
            auction_row,
            llm
        )
        if res.get("status") == "success":
            insights = res["insights"]
            ranking = insights.get("ranking", {})
            result_row["risk_summary"] = ranking.get("risk_summary", "Unknown")
            result_row["insights_json"] = json.dumps(insights, default=str)
            print(f"Processed {auction_id} → {result_row['risk_summary']}")
        else:
            result_row["risk_summary"] = "Error"
            result_row["insights_json"] = json.dumps(res, default=str)
            print(f"Error result for {auction_id}: {res}")
    except Exception as e:
        result_row["risk_summary"] = "Error"
        result_row["insights_json"] = json.dumps({"error": str(e)}, default=str)
        print(f" Exception for {auction_id}: {e}")

    # Ensure risk_summary never stays "Unknown" or "Not Processed"
    if result_row["risk_summary"] in ["Unknown", "", None]:
        result_row["risk_summary"] = "Error" # 
        
    return result_row

def process_and_cache_auction(auction_row, llm, force_refresh=False):
    # Load the current cache 
    df_cache = load_risk_cache()
    auction_id = str(auction_row.get("auction_id", "UNKNOWN")).strip()
    
    #  Check Expiration/Status (for processing new/expired items)
    
    # check if the auction ID exists in the cache
    cached_row = df_cache[df_cache["auction_id"] == auction_id]
    
    # Default: assume we need to process
    needs_processing = True
    
    
    if not cached_row.empty and not force_refresh:
        # NOTE: We must check for "Error" 
        current_status = cached_row.iloc[0].get('risk_summary', 'Error').title() 
        last_processed_at = pd.to_datetime(cached_row.iloc[0].get('last_processed_at'), errors='coerce')
        
        # Check for expired/needs retry
        is_expired = (
            pd.notna(last_processed_at)
            and (datetime.utcnow() - last_processed_at.to_pydatetime()).days >= RISK_CACHE_TTL_DAYS
        )
        
        # Only return cache if status is good AND not expired
        if current_status not in ["Error"] and not is_expired:
            print(f"🔄 Loaded from cache: {auction_id}")
            # Return the existing data if it's still valid
            return cached_row.iloc[0].to_dict()
        
        
        needs_processing = True
    
    
    
    if needs_processing:
        
        # Internal Try/Except for Resilience
        try:
            # Process the auction row
            print(f" Processing auction: {auction_id}")
            # This is the line that sometimes crashes
            result_row = process_single_auction_row(auction_row, llm)
            
        except Exception as e:
            # If processing crashes, create an Error status row
            error_message = f"Processing failed: {type(e).__name__} - {str(e)}"
            print(f"!!! CRITICAL ERROR for ID {auction_id}: {error_message}")
            
            # Create an error row
            result_row = {
                "auction_id": auction_id,
                "risk_summary": "Error",
                "last_processed_at": datetime.utcnow().isoformat(),
                "insights_json": json.dumps({"error": error_message})
            }
        

        
        # Regardless of success or failure (caught in the except block), 
        # we now have a valid 'result_row' to cache.
        df_new_row = pd.DataFrame([result_row])  
        
        # Update the Cache
        # Combine existing cache with the new result, keeping the latest one
        df_updated_cache = (
            pd.concat([df_cache, df_new_row], ignore_index=True)
              .drop_duplicates(subset='auction_id', keep='last')
        )
        
        # Save the full, updated cache
        save_risk_cache(df_updated_cache)
        
        # Return the processed/error result
        return result_row
    
    # Fallback return (shouldn't be reached if logic is perfect)
    return auction_row.to_dict()


if page == "📊 Auction Insights": 
    st.markdown('<div class="main-header">📊 Auction Insights</div>', unsafe_allow_html=True)

    today = date.today()

    if df is None or df.empty:
        st.error("No auction data loaded")
        st.stop()

    # Clean column names
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
    )

    # Filter only IBBI auctions with EMD date today or in future
    df_ibbi = df[df["source"].str.lower().str.contains("ibbi", na=False)].copy()
    df_ibbi["emd_submission_date_dt"] = pd.to_datetime(
        df_ibbi["emd_submission_date"], format="%d-%m-%Y", errors="coerce"
    )
    df_ibbi = df_ibbi[df_ibbi["emd_submission_date_dt"].dt.date >= today]
    df_ibbi.drop_duplicates(subset=["auction_id"], keep="first", inplace=True)

    if df_ibbi.empty:
        st.info("No future IBBI EMD auctions found. You can still view cached risk insights.")

    # Risk Insights Section 
    st.subheader("Risk Summary Counts")

    # Refresh button 
    if st.button("🔄 Refresh Risk Insights"):
        with st.spinner("Processing auctions for risk insights..."):
            if df_ibbi.empty:
                st.warning("No auctions to process with EMD date today or in future.")
            else:
                llm = initialize_llm()
                progress = st.progress(0)
                processed_count = 0
                total_to_process = len(df_ibbi)

                for i, (_, row) in enumerate(df_ibbi.iterrows()):
                    auction_id = row['auction_id']
                    processed_row = process_and_cache_auction(row, llm, force_refresh=True)

                    if "Loaded from cache" not in processed_row.get("risk_summary", ""):
                        processed_count += 1

                    progress.progress(int((i + 1) / total_to_process * 100))

                if processed_count > 0:
                    st.success(
                        f"Processing complete. {processed_count} auctions were analyzed/updated."
                    )
                    st.rerun()
                else:
                    st.info("No new auctions needed processing (all loaded from cache).")

    # Reload the cache (initial + after refresh)
    df_cache_for_display = load_risk_cache()
    df_final_display = pd.merge(
        df_ibbi[["auction_id"]], df_cache_for_display, on="auction_id", how="left"
    )
    df_final_display["risk_summary_clean"] = (
        df_final_display["risk_summary"].fillna("Error").str.title()
    )

    # Summary counts
    counts = df_final_display["risk_summary_clean"].value_counts().to_dict()

    #  Display summary buttons
    c1, c2, c3, c4 = st.columns(4)
    clicked = None
    with c1:
        if st.button(f"High Risk\n{counts.get('High Risk',0)}"):
            clicked = "High Risk"
    with c2:
        if st.button(f"Average Risk\n{counts.get('Average Risk',0)}"):
            clicked = "Average Risk"
    with c3:
        if st.button(f"Low/No Risk\n{counts.get('Low/No Risk',0)}"):
            clicked = "Low/No Risk"
    with c4:
        if st.button(f"Error\n{counts.get('Error',0)}"):
            clicked = "Error"

    # Display filtered table if clicked
    if clicked:
        st.markdown(f"### Auctions in: {clicked}")
        df_sel = df_final_display[df_final_display["risk_summary_clean"] == clicked].copy()
        st.dataframe(df_sel[["auction_id", "risk_summary", "last_processed_at"]])

    st.markdown("---")

    #  AI Analysis Section 
    st.subheader("Auction AI Analysis")

    auction_ids = df_ibbi['auction_id'].dropna().unique()
    selected_id = st.selectbox("Select Auction ID", options=[""] + list(auction_ids))

    if selected_id:
        selected_row = df_ibbi[df_ibbi['auction_id'] == selected_id].iloc[0]
        corporate_debtor = selected_row.get('bank', '')
        auction_notice_url = selected_row.get('notice_url') or selected_row.get('auction_notice_url')

        if not auction_notice_url or "url 2_if available" in str(auction_notice_url).lower():
            st.warning("Selected auction has no valid Auction Notice URL.")
        else:
            llm = initialize_llm()
            if st.button("Generate Insights"):
                with st.spinner("Generating insights..."):
                    insights_result = generate_auction_insights(corporate_debtor, selected_row.to_dict(), llm)
                    if insights_result["status"] == "success":
                        display_insights(insights_result["insights"])
                    else:
                        st.error("Analysis Failed")
                        st.exception(Exception(insights_result.get("message", "")))

#######################################################################################################################################################################################################
#####################################################################################################################################################################################################


# PBN FAQs Page
elif page == "📚 PBN FAQs":
    st.markdown('<div class="main-header">📚 PBN FAQs</div>', unsafe_allow_html=True)
    st.markdown("Explore frequently asked questions about the Property Bidding Network (PBN) to understand its features, integration, and benefits.")

    # FAQ Data
    risk_faqs = [
        {
            "question": "What is the Legal Compliance Score?",
            "answer": """The Legal Compliance score indicates how well the auction notice and process align with the Insolvency and Bankruptcy Code (IBC) guidelines and related regulations.  
            
            Factors considered:
            • Whether statutory notice periods (e.g., 21 days under Rule 8(6) of IBC) are met.  
            • Presence of mandatory documents (Sale Notice, Auction Process Document, Terms & Conditions).  
            • Appointment and authorization details of the liquidator/auction authority.  
            • Mention of reserve price, EMD, payment terms, and timelines.  
            • Disclosure of litigation, encumbrances, or title ownership status.  

            Interpretation:
            - High Score (8–10): Fully compliant.  
            - Medium Score (4–7): Mostly compliant, minor gaps.  
            - Low Score (0–3): Major lapses (e.g., missing notices, improper timelines)."""
        },
        {
            "question": "What is the Economical Score?",
            "answer": """The Economical Score reflects the financial attractiveness and valuation fairness of the auctioned assets.  

            Factors considered:
            • Reserve price vs. market benchmarks.  
            • EMD reasonableness.  
            • Incremental bid value fairness.  
            • Asset liquidity.  

            Interpretation:  
            - High Score (8–10): Fair pricing, realistic terms.  
            - Medium Score (4–7): Some mismatches or barriers.  
            - Low Score (0–3): Over/undervalued, unrealistic EMD/increments."""
        },
        {
            "question": "What is the Market Trends Score?",
            "answer": """The Market Trends Score evaluates how the asset’s sector and geography align with current demand.  

            Factors considered: 
            • Industry outlook.  
            • Regional economic activity.  

            Interpretation: 
            - High Score (8–10): High demand, favorable trends.  
            - Medium Score (4–7): Stable demand.  
            - Low Score (0–3): Declining industry or weak demand."""
        },
        {
            "question": "What is the Final Score?",
            "answer": """The Final Score is a weighted composite of Legal Compliance, Economical, and Market Trends scores.  

            Formula: 
            Final Score = (Legal + Economical + Market Trends) ÷ 3  

            Interpretation:  
            - 8–10: Very Attractive Auction.  
            - 4–7: Average Auction.  
            - 0–3: Risky Auction."""
        },
        {
            "question": "What is the Risk Summary?",
            "answer": """The Risk Summary is a qualitative interpretation of the Final Score.  

            • Low Risk: High compliance, fair valuation, strong demand.  
            • Average Risk: Minor gaps.  
            • High Risk: Major compliance/pricing/market issues."""
        },
        {
            "question": "What is the Reference Summary?",
            "answer": """The Reference Summary provides supporting context for each score.  

            • Contact detail quality.  
            • Timelines (notice, EMD).  
            • Legal compliance with IBC.  
            • Asset description completeness.  
            • Valuation benchmarks.  
            • Market conditions."""
        },
        {
            "question": "What other insights do we provide?",
            "answer": """Apart from scoring, the platform extracts:  

            • Corporate Debtor Info.  
            • Auction Details (date, platform, inspection).  
            • Asset Information (type, reserve price, EMD, increments).  
            • Contact Information (liquidator details).  
            • Regulation Checks (IBC Rule 8(6), Reg. 33).  
            • Listing Quality Assessment."""
        }
    ]

    faqs = [
        {
            "question": "What is PBN in one line?",
            "answer": "An AI/analytics overlay that improves discovery, price realization, participation, and integrity on top of BAANKNET—without handling KYC or payments."
        },
        {
            "question": "What outcomes does PBN target?",
            "answer": "Higher bidder participation, better hammer-to-reserve %, faster time-to-sale, fewer re-auctions, and stronger transparency/auditability."
        },
        {
            "question": "Which PBN modules ship first?",
            "answer": "Listing Quality Score, Reserve-Price & Timing Optimizer, Buyer Copilot, Fraud Sentinel, and the Recovery/Integrity Cockpit."
        },
        {
            "question": "What data does PBN need (read-only)?",
            "answer": "Listing fields (asset, location, reserve, schedule), artefact inventory (docs/photos), and outcomes (sold/unsold, hammer). Optional: pseudonymous engagement signals."
        },
        {
            "question": "Does PBN touch KYC or payments?",
            "answer": "No. Those remain on BAANKNET/bank rails. PBN never processes KYC or payment data."
        },
        {
            "question": "How does PBN integrate technically?",
            "answer": "Read-only APIs or scheduled extracts (CSV/JSON). Minimal schema agreed via MoU; secure transfer; encryption in transit/at rest."
        },
        {
            "question": "Can we start without new APIs?",
            "answer": "Yes—begin with scheduled extracts; move to APIs once value is proven."
        },
        {
            "question": "What is the Listing Quality Score?",
            "answer": "A composite score of artefact completeness, OCR readability, address/geo consistency, photo sufficiency, and reserve sanity. Low scores trigger fix-lists and user warnings."
        },
        {
            "question": "How does the Reserve-Price & Timing Optimizer work?",
            "answer": "Uses comps, circle-rate context, outcomes history, micro-market demand, and seasonality to propose a reserve band + auction window with sensitivity analysis."
        },
        {
            "question": "Who approves reserves?",
            "answer": "Always the bank. PBN recommendations are explainable and advisory."
        },
        {
            "question": "What does the Fraud Sentinel monitor?",
            "answer": "Bid-rotation/rings, synchronized bursts from correlated identities, abnormal increments, repeated winner defaults, frequent unexplained reschedules, and outcome posting anomalies."
        },
        {
            "question": "What happens when Fraud Sentinel fires?",
            "answer": "PBN creates an explainable case bundle (evidence, sequences, timestamps, graphs) and escalates to bank/DFS; no auto-bans."
        },
        {
            "question": "What does the Buyer Copilot show?",
            "answer": "Plain-language notice summaries, due-diligence checklists, local comps/heatmaps, rent-yield hints, and a bid-readiness simulator (opt-in/consent)."
        },
        {
            "question": "How does PBN protect privacy?",
            "answer": "Data minimization (non-PII), pseudonymous analytics only, consent prompts for overlays, strict RBAC, audit trails, encryption in transit/at rest."
        },
        {
            "question": "What KPIs are tracked by default?",
            "answer": "Participation density, first-time bidder share, hammer-to-reserve %, days-on-platform, re-auction rates, grievance density, integrity alert rates."
        },
        {
            "question": "How are false positives handled?",
            "answer": "Each alert has severity + confidence; HIGH actions require a rules hit and model score threshold. MEDIUM flags sampled for manual QA to tune thresholds."
        },
        {
            "question": "Is PBN deployment cloud or on-prem?",
            "answer": "Both options. Default: India-region cloud with VPC isolation; on-prem supported if mandated by a bank."
        },
        {
            "question": "How are models governed and explained?",
            "answer": "Versioned models/features, drift/bias monitoring, back-testing, release notes, rollback hooks; each recommendation includes why (top features) and evidence."
        },
        {
            "question": "Does PBN change BAANKNET screens?",
            "answer": "No core changes. Optional in-page overlays or a companion micro-app (consent-based) to explain listings; all transactions stay on BAANKNET."
        },
        {
            "question": "What’s the action framework for red flags?",
            "answer": "BLOCK/HOLD (high risk), WARN/PRIORITIZE (medium), INFO (low). Each rule has id, trigger, evidence, explanation, and auto-clear policy."
        },
        {
            "question": "What training and handholding are included?",
            "answer": "Role-based sessions (Branch/RO, CXO/Recovery, BAANKNET ops, DFS), micro-videos, in-app tooltips, and weekly KPI reviews during pilot."
        },
        {
            "question": "What does success look like at pilot exit?",
            "answer": "Pre-agreed KPI bands hit (e.g., +X% participation, +Y% hammer uplift, −Z% cycle time), integrity alerts within expected ranges, and positive branch feedback on fix-lists."
        },
        {
            "question": "How does PBN scale across banks/cities?",
            "answer": "Tenant-isolated data, configurable rules, geo/asset templates, and a feature store that generalizes across micro-markets with local calibration."
        },
        {
            "question": "What’s the exit/retention stance?",
            "answer": "Clear data-retention windows (operational vs anonymized analytics), export tooling for your data, and deprovisioning procedures defined in the MoU."
        }
    ]

   

    st.markdown('<div class="sub-header">General Information</div>', unsafe_allow_html=True)
    for faq in faqs[:5]:
        with st.expander(faq["question"]):
            st.markdown(f'<div class="faq-answer">{faq["answer"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sub-header">Technical Integration</div>', unsafe_allow_html=True)
    for faq in faqs[5:7]:
        with st.expander(faq["question"]):
            st.markdown(f'<div class="faq-answer">{faq["answer"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sub-header">Core Features</div>', unsafe_allow_html=True)
    for faq in faqs[7:13]:
        with st.expander(faq["question"]):
            st.markdown(f'<div class="faq-answer">{faq["answer"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sub-header">Privacy and Governance</div>', unsafe_allow_html=True)
    for faq in faqs[13:19]:
        with st.expander(faq["question"]):
            st.markdown(f'<div class="faq-answer">{faq["answer"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sub-header">Deployment and Support</div>', unsafe_allow_html=True)
    for faq in faqs[19:]:
        with st.expander(faq["question"]):
            st.markdown(f'<div class="faq-answer">{faq["answer"]}</div>', unsafe_allow_html=True)

    # FAQ Sections
    st.markdown('<div class="sub-header">Auction Risk & Scoring FAQs</div>', unsafe_allow_html=True)
    for faq in risk_faqs:
        with st.expander(faq["question"]):
            st.markdown(faq["answer"])

    # Download FAQs as PDF (placeholder for future implementation)
    st.markdown("---")
    st.markdown("**Download FAQs**")
    st.button("Download as PDF (Coming Soon)", disabled=True)
























































