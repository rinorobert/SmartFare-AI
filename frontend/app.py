import streamlit as st
import requests
import pandas as pd

# Page config
st.set_page_config(
    page_title="SmartFare-AI",
    page_icon="🚕",
    layout="centered"
)

if "page" not in st.session_state:
    st.session_state["page"] = "analyzer"

if "distance" not in st.session_state:
    st.session_state.distance = 0.5

if "quoted_fare" not in st.session_state:
    st.session_state.quoted_fare = 0.0

if "waiting_minutes" not in st.session_state:
    st.session_state.waiting_minutes = 0


# Header
st.markdown("## 🚕 SmartFare-AI")

c1, c2, c3, c4 = st.columns(4)

with c1:
    if st.button("🏠 Fare Analyzer"):
        st.session_state["page"] = "analyzer"

with c2:
    if st.button("📋 Fare Breakdown"):
        st.session_state["page"] = "breakdown"

with c3:
    if st.button("📖 Auto Fare Rules"):
        st.session_state["page"] = "rules"

with c4:
    if st.button("ℹ️ About"):
        st.session_state["page"] = "about"

data = st.session_state.get("fare_data")
analysis_complete = st.session_state.get(
    "analysis_complete",
    False
)

if st.session_state["page"] == "analyzer":
    last_trip = st.session_state.get(
        "last_trip",
        {}
    )
    # Input section
    st.markdown("### 🧾 Trip Details")
    st.success(
        "📜 Based on Kerala Government Auto Fare Notification (2022)"
    )

    st.markdown(
        "<p style='color:gray;'>A data-driven tool to understand auto fare fairness using government rules and real-world pricing patterns.</p>",
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        distance = st.number_input(
            "Distance (km)",
            min_value=0.5,
            step=0.1,
            value=last_trip.get("distance", 0.5),
            help="Distance from pickup location to destination in kilometers."
        )

    with col2:
        journey_time = st.radio(
            "Journey Time",
            [
                "Day (5:00 AM – 10:00 PM)",
                "Night (10:00 PM – 5:00 AM)"
            ],
            index=0 if last_trip.get(
                "journey_time",
                "Day (5:00 AM – 10:00 PM)"
            ).startswith("Day") else 1,
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
            value=last_trip.get("quoted_fare", 0.0),
            help="Fare quoted by the auto driver. Used to determine whether the fare appears reasonable."
        )

        if quoted_fare < 30:
            st.info(
               "ℹ️ Kerala Government rules specify a minimum fare of ₹30 for the first 1.5 km."
            )

    col4, col5, col6 = st.columns(3)

    with col4:
        waiting_minutes = st.number_input(
            "Waiting Time(min)",
            min_value=0,
            step=5,
            value=last_trip.get("waiting_minutes", 0),
            help="Total waiting time during the trip. Kerala rules permit a detention charge of ₹10 per 15 minutes."
        )

    with col5:
        return_journey_choice = st.radio(
            "Return Journey",
            ["No", "Yes"],
            horizontal=True,
            key="return_journey_choice",
            help="Return journey charges are not applicable in major cities like Thiruvananthapuram, Kollam, Kochi, Thrissur, Kozhikode, Kannur, Palakkad, Kottayam"
        )
        return_journey = return_journey_choice == "Yes"
        st.session_state["return_journey"] = return_journey

    with col6:
        journey_area = st.radio(
            "Journey Area",
            ["Major City", "Non-Major City"],
            horizontal=True,
            key="journey_area",
            help="Major cities include Thiruvananthapuram, Kollam, Kochi, Thrissur, Kozhikode, Kannur, Palakkad, Kottayam"
        )
        major_city = journey_area == "Major City"
        st.session_state["major_city"] = major_city

    if major_city and return_journey:
        st.warning(
            "Return journey charges are not applicable in Kerala major city areas and will not be included in the fare calculation."
        )

    st.markdown("")

    current_trip = {
        "distance": distance,
        "quoted_fare": quoted_fare,
        "waiting_minutes": waiting_minutes,
        "journey_time": journey_time,
        "return_journey_choice": return_journey_choice,
        "journey_area": journey_area
    }
    trip_changed = (
        "last_trip" in st.session_state
        and current_trip != st.session_state["last_trip"]
    )

    if trip_changed:
        st.session_state["analysis_complete"] = False

    if "checked" not in st.session_state:
        st.session_state.checked = False

    if "analysis_complete" not in st.session_state:
        st.session_state["analysis_complete"] = False

    if "fare_data" not in st.session_state:
        st.session_state["fare_data"] = None

    # Action button
    if st.button("🔍 Analyze Fare Transparency", use_container_width=True):
        if quoted_fare <= 0:

            st.session_state["analysis_complete"] = False
            st.session_state["fare_data"] = None
            st.session_state["checked"] = False

            st.warning(
                "⚠️ Please enter a valid quoted fare."
            )

            st.stop()
        else:
            st.session_state["last_trip"] = {
                "distance": distance,
                "quoted_fare": quoted_fare,
                "waiting_minutes": waiting_minutes,
                "journey_time": journey_time,
                "return_journey_choice": return_journey_choice,
                "journey_area": journey_area
            }
            st.session_state.checked = True
    if analysis_complete and data:

        st.success(
            "Fare analysis completed successfully"
            )

        difference = (
            data["quoted_fare"]
                - data["government_expected_fare"]
            )

        if difference > 0:
            difference_text = (
                f"Additional Amount Above Government Fare: ₹{difference:.2f}"
            )

        elif difference < 0:
            difference_text = (
                f"Amount Below Government Fare: ₹{abs(difference):.2f}"
            )

        else:
            difference_text = (
                "Matches Government Fare Exactly"
            )
                        
        journey_period = (
            "Night (10:00 PM – 5:00 AM)"
                if data["time_of_day"].lower() == "night"
                else "Day (5:00 AM – 10:00 PM)"
            ) 
        
        from datetime import datetime

        generated_time = datetime.now().strftime(
            "%d %b %Y, %I:%M %p"
        )

        if data["overcharge_risk"] == "High":
            risk_display = "🔴 High Risk"

        elif data["overcharge_risk"] == "Medium":
            risk_display = "🟡 Medium Risk"

        else:
            risk_display = "🟢 Low Risk"

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
            🧾 Fare Transparency Receipt
            </h2>

            <p style="text-align:center;color:gray;">
            Generated on: {generated_time}
            </p>

            <hr>

            <h4>🚕 Trip Details</h4>

            <b>Distance:</b> {data['distance_km']} km<br>
            <b>Journey Period:</b> {journey_period}<br>
            <b>Waiting Time:</b> {st.session_state['last_trip']['waiting_minutes']} min<br>
            <b>Return Journey:</b> {st.session_state['last_trip']['return_journey_choice']}<br>
            <b>Journey Area:</b> {st.session_state['last_trip']['journey_area']}<br>

            <hr>

            <h4>💰 Fare Summary</h4>

            <b>Government Fare:</b> ₹{data['government_expected_fare']:.2f}<br>
            <b>Quoted Fare:</b> ₹{data['quoted_fare']:.2f}<br>

            <hr>

            <h4>📊 Analysis</h4>

            <b>{difference_text}</b><br>
            <b>Risk Level:</b> {risk_display}<br>

            <hr>

            </div>
            """,
            unsafe_allow_html=True
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
                    
        # Fare deviation
        st.markdown("### 📈 Fare Deviation")

        deviation_percent = (
            (data["quoted_fare"] - data["government_expected_fare"])
                / data["government_expected_fare"]
            ) * 100

        if deviation_percent > 0:
            st.warning(
                f"The quoted fare is {deviation_percent:.1f}% higher than the government fare."
            )
        elif deviation_percent < 0:
            st.success(
                f"The quoted fare is {abs(deviation_percent):.1f}% lower than the government fare."
            )
        else:
            st.info(
                "The quoted fare exactly matches the government fare."
            )
          
if st.session_state["page"] == "breakdown":
    if analysis_complete and data:

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
                        
if st.session_state["page"] == "rules":

    st.header("📖 Kerala Auto Fare Rules (2022)")

    st.markdown("""
        ### 🚕 Minimum Fare
        ₹30 for the first 1.5 km

        ---

        ### 📏 Distance Charge
        ₹15 per km after the first 1.5 km

        ---

        ### 🌙 Night Travel
        50% surcharge between 10 PM and 5 AM

        ---

        ### ⏳ Waiting Charge
        ₹10 for every 15 minutes

        ---

        ### 🔄 Return Journey
        50% additional fare

        ---

        ### 🏙 Major City Exception

        Return journey charges are not applicable in:

        - Thiruvananthapuram
        - Kollam
        - Kochi
        - Thrissur
        - Kozhikode
        - Kannur
        - Palakkad
        - Kottayam
        """)
    st.divider()

    st.subheader("📜 Official Government Notification")

    st.markdown(
        """
    Kerala auto-rickshaw fare rules used in this project are based on the official Government Order:

    https://mvd.kerala.gov.in/sites/default/files/Downloads/G.O.P.No_.14-2022-TRANS.pdf
    """
    )       

if st.session_state["page"] == "about":

    st.header("ℹ️ About SmartFare-AI")

    st.markdown("""
        SmartFare-AI is a fare transparency tool designed to help passengers understand whether an auto-rickshaw fare appears reasonable.

        ### Features

        - Kerala Government Fare Rules
        - Fare Transparency Reports
        - Fare Breakdown Analysis
        - Overcharge Risk Assessment

        ### Why was it built?

        Many passengers are unsure whether a quoted fare is fair.

        SmartFare-AI helps by comparing:

        - Government fare rules
        - Typical fare estimates
        - Driver quoted fares

        ### Built By

        **Rino Robert**        
        **B Tech Student**
        """)
    
    st.divider()

    st.subheader("🔗 Connect With Me")

    st.markdown(
            """
        - GitHub: https://github.com/rinorobert
        - LinkedIn: https://linkedin.com/in/rino-robert
        """
    )

# API call
if st.session_state.checked:

    payload = {
    "distance_km": st.session_state["last_trip"]["distance"],

    "time_of_day": (
        "night"
        if st.session_state["last_trip"]["journey_time"].startswith("Night")
        else "day"
    ),

    "quoted_fare": st.session_state["last_trip"]["quoted_fare"],

    "waiting_minutes": st.session_state["last_trip"]["waiting_minutes"],

    "return_journey": (
        st.session_state["last_trip"]["return_journey_choice"] == "Yes"
    ),

    "major_city": (
        st.session_state["last_trip"]["journey_area"] == "Major City"
    )
}

    try:
        response = requests.post(
            "https://smartfare-ai-backend.onrender.com/predict",
            json=payload,
            timeout=35
        )

        if response.status_code == 200:
            data = response.json()

            st.session_state["fare_data"] = data
            st.session_state["analysis_complete"] = True

            # Prevent repeated API calls
            st.session_state.checked = False
            st.rerun()

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

            
st.divider()

st.markdown(
        "<p style='text-align: center; color: gray; font-size: 0.85em;'>"
        "© Rino Robert • 2026 • SmartFare-AI • Educational project"
        "</p>",
        unsafe_allow_html=True
    )