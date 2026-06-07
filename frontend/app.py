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
st.success(
    "📜 Based on Kerala Government Auto Fare Notification (2022)"
)

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

col1, col2, col3 = st.columns(3)

with col1:
    distance = st.number_input(
        "Distance (km)",
        min_value=0.5,
        step=0.1,
        help="Distance from pickup location to destination in kilometers."
    )

with col2:
    journey_time = st.radio(
        "Journey Time",
        [
            "Day (5:00 AM – 10:00 PM)",
            "Night (10:00 PM – 5:00 AM)"
        ],
        help="Select day or night travel. Night journeys (10 PM–5 AM) have additional charges under Kerala rules."
    )
    time_of_day = (
        "night"
        if journey_time.startswith("Night")
        else "day"
    )

with col3:
    quoted_fare = st.number_input(
        "Quoted Fare (₹)",
        min_value=0.0,
        step=1.0,
        help="Fare quoted by the auto driver. Used to determine whether the fare appears reasonable."
    )

col4, col5, col6 = st.columns(3)

with col4:
    waiting_minutes = st.number_input(
        "Waiting Time(min)",
        min_value=0,
        step=5,
        help="Total waiting time during the trip. Kerala rules permit a detention charge of ₹10 per 15 minutes."
    )

with col5:
    return_journey_choice = st.radio(
        "Return Journey",
        ["No", "Yes"],
        horizontal=True,
        help="Kerala rules allow an additional 50% return journey charge in non-major city areas."
    )
    return_journey = return_journey_choice == "Yes"

with col6:
    journey_area = st.radio(
        "Journey Area",
        ["Major City", "Non-Major City"],
        horizontal=True,
        help="Major Cities: Kollam, Kochi, Thiruvananthapuram, Thrissur, Kozhikode, Kannur, Palakkad, Kottayam"
    )
    major_city = journey_area == "Major City"

if major_city and return_journey:
    st.warning(
        "Return journey charges are not applicable in Kerala major city areas and will not be included in the fare calculation."
    )

st.markdown("")

if "checked" not in st.session_state:
    st.session_state.checked = False

# Action button
if st.button("📋 Generate Transparency Report", use_container_width=True):
    st.session_state.checked = True

st.divider()

# API call
if st.session_state.checked:
    if quoted_fare <= 19:
        st.warning(
            "⚠️ Please enter the fare quoted by the auto driver."
        )
        st.stop()

    payload = {
        "distance_km": distance,
        "time_of_day": time_of_day,
        "quoted_fare": quoted_fare,
        "waiting_minutes": waiting_minutes,
        "return_journey": return_journey,
        "major_city": major_city
    }

    try:
        response = requests.post(
            "http://127.0.0.1:8000/predict",
            json=payload,
            timeout=20
        )

        if response.status_code == 200:
            data = response.json()

            st.success("Fare analysis completed successfully")

            difference = data["quoted_fare"] - data["government_expected_fare"]

            if difference > 0:
                verdict = "⚠️ Higher Than Government Fare"
            elif difference < 0:
                verdict = "✅ Lower Than Government Fare"
            else:
                verdict = "✔ Matches Government Fare"

            st.markdown(
                f"""
                <div style="
                    border:2px solid #444;
                    border-radius:12px;
                    padding:25px;
                    background-color:#111827;
                    margin-bottom:20px;
                ">

                <h2 style="text-align:center;">
                🧾 SmartFare Transparency Receipt
                </h2>

                <hr>

                <b>Distance:</b> {data['distance_km']} km<br>
                <b>Journey Time:</b> {data['time_of_day'].title()}<br>

                <hr>

                <b>Government Fare:</b> ₹{data['government_expected_fare']:.2f}<br>
                <b>Quoted Fare:</b> ₹{data['quoted_fare']:.2f}<br>

                <hr>

                <b>Difference:</b> ₹{difference:.2f}<br>
                <b>Risk Level:</b> {data['overcharge_risk']}<br>

                <hr>

                <b>{verdict}</b>

                </div>
                """,
                unsafe_allow_html=True
            )

            # Fare comparison section
            st.markdown("### 📋 Kerala Government Fare Breakdown")

            breakdown_df = pd.DataFrame({
                "Fare Component": [
                    "Minimum Fare",
                    "Distance Charge",
                    "Waiting Charge",
                    "Return Charge",
                    "Night Charge"
                ],
                "Amount (₹)": [
                    data["minimum_fare"],
                    data["distance_charge"],
                    data["waiting_charge"],
                    data["return_charge"],
                    data["night_charge"]
                ]
            })

            st.dataframe(
                breakdown_df,
                hide_index=True,
                use_container_width=True
            )

            st.success(
                f"Total Government Fare: ₹{data['government_expected_fare']:.2f}"
            )
            
                
            #Risk Badge
            st.markdown("### 🚦 Overcharge Risk Indicator")

            risk = data["overcharge_risk"]

            if risk == "High":
                st.error(
                    "🚨 High Risk: The quoted fare is significantly higher than expected."
                )

            elif risk == "Medium":
                st.warning(
                    "⚠️ Medium Risk: The quoted fare is slightly above the expected range."
                )

            else:
                st.success(
                    "✅ Low Risk: The quoted fare appears reasonable."
                )

            #Bar Chart
            st.markdown("### 📊 Compare the Three Fare Estimates")

            chart_data = pd.DataFrame({
                "Fare Type": [
                    "Government Fare",
                    "Typical Fare",
                    "Quoted Fare"
                ],
                "Amount (₹)": [
                    data["government_expected_fare"],
                    data["ml_estimated_real_world_fare"],
                    data["quoted_fare"]
                ]
            })

            st.bar_chart(chart_data.set_index("Fare Type"))
            st.caption(
                "Compare the official government fare, the ML-estimated typical fare, and the quoted fare used for risk assessment."
            )

            with st.expander("🤔 What do these fare amounts mean?"):
                st.markdown("""
                    ### Government Fare 🚕
                    The official fare calculated using Kerala Government auto-rickshaw fare rules.

                    It includes applicable charges such as:

                    - Distance travelled
                    - Waiting time
                    - Night surcharge (10 PM – 5 AM)
                    - Return journey charge (where permitted)

                    ---

                    ### Typical Fare 📊
                    An estimate of what passengers are commonly charged for similar trips.

                    This reflects real-world pricing patterns and may differ from the official government fare.

                    ---

                    ### Quoted Fare 💰
                    The amount quoted by the auto driver for your trip.

                    Enter the fare shown on the meter, pre-paid slip, or the amount requested by the driver.

                    ---

                    ### What does the Risk Indicator mean?

                    🟢 Low Risk  
                    The quoted fare is close to expected values.

                    🟡 Medium Risk  
                    The fare is slightly higher than expected.

                    🔴 High Risk  
                    The fare is significantly higher than expected and may deserve closer attention.

                    ---

                    ### Example

                    Suppose your trip is:

                    - Distance: 3.5 km
                    - Day travel
                    - No waiting time

                    Government Fare: ₹60

                    If a driver asks for ₹80, the tool compares that amount against government rules and typical charging patterns to help you understand whether the fare appears reasonable.
                    """)            
            
            
            #Progress Indicator
            st.markdown("### 📈 Difference from Government Fare")

            deviation_ratio = (
                data["quoted_fare"] /
                data["government_expected_fare"]
            )

            progress_value = min(deviation_ratio / 2, 1.0)

            st.progress(progress_value)

            st.caption(
                "Shows how much the quoted fare differs from the official government fare."
            )

            deviation_percent = (
                    (data["quoted_fare"] - data["government_expected_fare"])
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
                "⚠️ This tool is for informational purposes only. "
                "Government fares follow official Kerala auto-rickshaw fare rules. "
                "Typical fares are ML-based estimates derived from sample trip data and may vary due to traffic, waiting time, route conditions, demand, and local pricing practices."
            )
            
            st.divider()

            st.markdown(
                "<p style='text-align: center; color: gray; font-size: 0.85em;'>"
                "© Rino Robert • 2026 • SmartFare-AI • Educational project"
                "</p>",
                unsafe_allow_html=True
            )

        else:
            st.error(f"Status Code: {response.status_code}")
            st.write(response.text)

    except requests.exceptions.Timeout:
        st.warning(
            "⏳ Backend is waking up. Free-tier hosting may take 30–60 seconds after inactivity. Please try again shortly."
        )
    
    except requests.exceptions.ConnectionError:
        st.warning(
            "🔌 Unable to connect to the backend right now. The server may still be starting."
        )
    
    except Exception as e:
        st.error(f"Unexpected error: {e}")
