import streamlit as st
import pandas as pd
import numpy as np
import datetime
import random
import altair as alt

st.set_page_config(
    page_title="FinPulse | High-Throughput Clearing & Telemetry Engine",
    page_icon="⚡",
    layout="wide"
)

# Custom Styling
st.markdown("""
    <style>
    .metric-box {
        background-color: #0E1117;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #30363D;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("⚡ FinPulse: Transaction Rails & Log Telemetry Engine")
st.markdown("""
**Production telemetry, error isolation, and root-cause analysis (RCA) platform.**  
Simulating high-concurrency payment clearing, NAV computation feeds, and automated SLA breach detection.
""")

# --- SYNTHETIC ENGINE WITH INJECTED EDGE CASES ---
@st.cache_data
def load_telemetry_stream():
    endpoints = [
        "/api/v2/nav/feed/eod-calculate",
        "/api/v1/clearing/mandate/settle",
        "/api/v3/portfolio/realtime-valuation",
        "/api/v1/escrow/split-disbursement"
    ]
    status_distribution = [200, 200, 200, 200, 400, 404, 500, 502, 504]
    weights = [70, 10, 5, 5, 3, 1, 3, 1, 2]
    
    error_catalog = {
        500: "DB_WRITE_LOCK_TIMEOUT",
        502: "UPSTREAM_EXCHANGE_FEED_DISCONNECT",
        504: "GATEWAY_TIMEOUT_CLEARING_HOUSE",
        400: "ISO20022_SCHEMA_VALIDATION_FAILED",
        404: "VIRTUAL_ACCOUNT_NOT_FOUND"
    }

    records = []
    base_time = datetime.datetime.now() - datetime.timedelta(hours=4)
    
    for i in range(500):
        t = base_time + datetime.timedelta(seconds=i * 28)
        status = random.choices(status_distribution, weights=weights)[0]
        reason = error_catalog.get(status, "NONE")
        
        # Latency anomaly simulation
        if status in [502, 504]:
            latency = int(np.random.normal(3200, 450))
        elif status == 500:
            latency = int(np.random.normal(1800, 300))
        else:
            latency = max(25, int(np.random.normal(110, 25)))

        records.append({
            "timestamp": t,
            "correlation_id": f"TXN-99{random.randint(10000, 99999)}",
            "endpoint": random.choice(endpoints),
            "status_code": status,
            "latency_ms": latency,
            "error_tag": reason,
            "retry_count": random.choice([0, 0, 0, 1, 2, 3]) if status >= 500 else 0
        })
    return pd.DataFrame(records)

df = load_telemetry_stream()

# --- TOP KPI TELEMETRY ---
c1, c2, c3, c4, c5 = st.columns(5)
total_requests = len(df)
failed_txns = len(df[df["status_code"] >= 400])
error_rate = (failed_txns / total_requests) * 100
avg_lat = df["latency_ms"].mean()
p99_lat = df["latency_ms"].quantile(0.99)

c1.metric("Ingested Events (4h)", f"{total_requests:,}")
c2.metric("SLA Breach / Failures", f"{failed_txns}", delta=f"{error_rate:.2f}% Error Rate", delta_color="inverse")
c3.metric("Avg Latency", f"{avg_lat:.0f} ms")
c4.metric("P99 Latency Spike", f"{p99_lat:.0f} ms")
c5.metric("System Uptime", "99.28%", delta="Warning", delta_color="off")

st.divider()

# --- SEARCH & SPLUNK-STYLE PIPELINE ---
st.subheader("🛠️ SPL Log Triage & Root Cause Terminal")
q_col1, q_col2 = st.columns([3, 1])

with q_col1:
    query = st.text_input(
        "SPL Filter Expression",
        value='status_code>=500 | stats count by error_tag',
        help="Simulates Splunk pipe syntax. Type status_code>=500, status_code==200, or filter by keyword."
    )

with q_col2:
    selected_ep = st.selectbox("API Rail Endpoint", ["ALL"] + sorted(list(df["endpoint"].unique())))

# Dynamic Filtering
filtered = df.copy()
if selected_ep != "ALL":
    filtered = filtered[filtered["endpoint"] == selected_ep]

if "status_code>=500" in query:
    filtered = filtered[filtered["status_code"] >= 500]
elif "status_code==200" in query or "status_code=200" in query:
    filtered = filtered[filtered["status_code"] == 200]
elif "status_code>=400" in query:
    filtered = filtered[filtered["status_code"] >= 400]

# Analytics Visuals
ch1, ch2 = st.columns(2)

with ch1:
    st.markdown("**Incident Count by Error Tag (Root Cause Distribution)**")
    err_df = filtered[filtered["error_tag"] != "NONE"]["error_tag"].value_counts().reset_index()
    err_df.columns = ["Error Tag", "Occurrences"]
    if not err_df.empty:
        chart1 = alt.Chart(err_df).mark_bar(color="#FF4B4B").encode(
            x=alt.X("Occurrences:Q"),
            y=alt.Y("Error Tag:N", sort="-x")
        ).properties(height=240)
        st.altair_chart(chart1, use_container_width=True)
    else:
        st.info("No failure events detected under current filter.")

with ch2:
    st.markdown("**Latency Spike Timeline (ms)**")
    chart2 = alt.Chart(filtered).mark_line(color="#00FFAA").encode(
        x="timestamp:T",
        y="latency_ms:Q",
        tooltip=["timestamp", "endpoint", "status_code", "latency_ms", "correlation_id"]
    ).properties(height=240)
    st.altair_chart(chart2, use_container_width=True)

# Raw Logs
st.markdown(f"**Filtered Distributed Traces ({len(filtered)} records):**")
st.dataframe(
    filtered.sort_values(by="timestamp", ascending=False),
    use_container_width=True,
    hide_index=True
)