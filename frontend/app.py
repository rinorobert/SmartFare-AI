import streamlit as st
import requests
import pandas as pd
import time

# Page config
st.set_page_config(
    page_title="SmartFare-AI",
    page_icon="🚕",
    layout="centered"
)

# Header
st.markdown("## 🚕 SmartFare-AI")
st.markdown(
    "<p style='color:gray;'>A data-driven tool to understand auto fare fairness using government rules and real-world pricing patterns.</p>",
    unsafe_allow_html=True
)

st.info(
    "ℹ️ First request may take 30–60 seconds while the backend wakes up from inactivity."
)

st.divider()

# Input section
st.markdown("### 🧾 Trip Details")

col1, col2 = st.columns(2)

with col1:
    distance = st.number_input(
        "Distance (km)",
        min_value=0.5,
        step=0.1,
        help="Distance from pickup point to destination"
    )

with col2:
    time_of_day = st.selectbox(
        "Time of Travel",
        ["day", "night"],
        help="Night time usually has additional charges"
    )

st.markdown("")

if "checked" not in st.session_state:
    st.session_state.checked = False

# Action button
if st.button("🔍 Check Fare Transparency", use_container_width=True):
    st.session_state.checked = True

st.divider()

# API call
if st.session_state.checked:
    payload = {
        "distance_km": distance,
        "time_of_day": time_of_day
    }

    try:
        response = requests.post(
            "https://smartfare-ai-backend.onrender.com/predict",
            json=payload,
            timeout=20
        )

        if response.status_code == 200:
            data = response.json()

            st.success("Fare analysis completed successfully")

            # Fare comparison section
            st.markdown("### 💰 Fare Breakdown")

            c1, c2 = st.columns(2)

            with c1:
                st.metric(
                    "Government Expected Fare (₹)",
                    data["government_expected_fare"]
                )

            with c2:
                st.metric(
                    "Typical Real-World Fare (₹)",
                    data["ml_estimated_real_world_fare"]
                )
            
            with st.expander("🤔 What do these fare amounts mean?"):
                explanation = """
                • **Government Fare** ~ Official fare calculated using Kerala government auto fare rules.
            
                • **Typical Fare** ~ ML-based estimate of what passengers are commonly charged for similar trips in real-world conditions.
            
                • **Quoted Fare** ~ Fare entered by the user or quoted by the driver for the trip.
            
                📌 **Example:**
            
                If the government fare for a 3 km trip is ₹50, but passengers are usually charged around ₹70, this tool helps you understand that difference and shows whether the quoted fare is reasonable.
            
                • **Overcharge Risk** indicates whether the quoted fare appears fair, slightly higher, or significantly higher than expected.
                """
            
                if time_of_day.lower() == "night":
                    explanation += """
            
                    • **Night-time Travel (10 PM – 5 AM)** includes a legally permitted surcharge as per Kerala government rules.
                    """
            
                st.markdown(explanation)

            #Bar Chart
            st.markdown("### 📊 Fare Comparison")

            chart_data = pd.DataFrame({
                "Fare Type": [
                    "Government Fare",
                    "Typical Fare",
                    "Quoted Fare"
                ],
                "Amount (₹)": [
                    data["government_expected_fare"],
                    data["ml_estimated_real_world_fare"],
                    data["simulated_quoted_fare"]
                ]
            })

            st.bar_chart(chart_data.set_index("Fare Type"))
            
            #Risk Badge
            st.markdown("### 🚦 Overcharge Risk Indicator")

            risk = data["overcharge_risk"]

            if risk == "High":
                st.error("🚨 High Risk: Fare is significantly above expected range")
            elif risk == "Medium":
                st.warning("⚠️ Medium Risk: Fare is slightly higher than usual")
            else:
                st.success("✅ Low Risk: Fare appears reasonable")
            
            #Progress Indicator
            st.markdown("### 📈 Fare Deviation Level")

            deviation_ratio = (
                data["simulated_quoted_fare"] /
                data["government_expected_fare"]
            )

            progress_value = min(deviation_ratio / 2, 1.0)

            st.progress(progress_value)

            st.caption(
                "This bar represents how far the quoted fare deviates from official pricing norms."
            )

            deviation_percent = (
                    (data["simulated_quoted_fare"] - data["government_expected_fare"])
                    / data["government_expected_fare"]
            ) * 100
            if deviation_percent > 0:
                st.markdown(
                f"**📈 Fare Deviation:** {deviation_percent:.1f}% higher than the government expected fare"
                )
            elif deviation_percent < 0:
                st.markdown(
                    f"**📉 Fare Deviation:** {abs(deviation_percent):.1f}% lower than the government expected fare"
                )
            else:
                st.markdown(
                    "**⚖️ Fare Deviation:** Exactly matches the government expected fare"
                )

            st.divider()

            st.caption(
                "⚠️ **Disclaimer**: Government fare calculations are based on officially published Kerala "
                "auto-rickshaw fare rules. Real-world fare estimates are indicative and may vary depending "
                "on location, demand, waiting time, and driver discretion. This tool is intended for "
                "informational and transparency purposes only."
            )
            st.divider()

            st.markdown(
                "<p style='text-align: center; color: gray; font-size: 0.85em;'>"
                "© Rino Robert • 2026 • SmartFare-AI • Educational project"
                "</p>",
                unsafe_allow_html=True
            )

        else:
            st.error("Unable to fetch fare details from the backend.")

    except Exception:
            with st.spinner("Waking up the server..."):
                 time.sleep(2)
            st.caption(
                "Tip: Free servers go to sleep when idle. First request may be slow."
            )
            st.warning(
                "⏳ The backend is waking up. On free hosting, this may take up to a minute. "
                "Please wait and try again."
            )
