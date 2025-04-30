import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai

# --- Load environment variables ---
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_api_key)

# --- Constants ---
CARBON_EMISSION_FACTOR_INDIA = 0.716  # kg CO2 per kWh
EFFICIENCY = 0.06  # Base efficiency from experiment
PERFORMANCE_RATIO = 0.70  # Base performance ratio

# Relative efficiency multipliers from experiment (vs base case)
RELATIVE_EFFICIENCY = {
    'water': 1.10,     # Near water case ~10% higher
    'plants': 0.88     # Near vegetation ~12% lower
}

# --- BIPV Estimation Function ---
def estimate_bipv_output(area_m2, irradiance_kwh_per_m2, surface_type):
    rel_eff = RELATIVE_EFFICIENCY.get(surface_type, 1.0)
    adjusted_efficiency = EFFICIENCY * rel_eff
    return area_m2 * irradiance_kwh_per_m2 * adjusted_efficiency * PERFORMANCE_RATIO


def total_energy_from_all_areas(area_dict):
    irradiance_map = {
        'south': 1350,
        'west': 1070,
        'east': 1000,
        'north': 800,
        'water': 1400,
        'plants': 1200
    }
    total_energy = 0
    detailed_breakdown = {}
    for key, area in area_dict.items():
        irradiance = irradiance_map.get(key, 1000)
        energy = estimate_bipv_output(area, irradiance, key)
        total_energy += energy
        detailed_breakdown[key] = energy
    return total_energy, detailed_breakdown

# --- Streamlit UI ---
st.title("NZEB Planner with BIPV Analysis")

st.header("Building Energy Inputs")
energy_consumption = st.number_input("Annual Energy Consumption (kWh)", min_value=0)
current_solar_production = st.number_input("Current Rooftop Solar Production (kWh/year)", min_value=0)

st.header("Available Area for BIPV Installation")
south_area = st.number_input("South-facing Area (m²)", min_value=0)
west_area = st.number_input("West-facing Area (m²)", min_value=0)
east_area = st.number_input("East-facing Area (m²)", min_value=0)
north_area = st.number_input("North-facing Area (m²)", min_value=0)
water_area = st.number_input("Near Water Area (m²)", min_value=0)
plants_area = st.number_input("Near Vegetation Area (m²)", min_value=0)

area_inputs = {
    'south': south_area,
    'west': west_area,
    'east': east_area,
    'north': north_area,
    'water': water_area,
    'plants': plants_area
}

if st.button("Generate NZEB Plan"):
    total_energy, breakdown = total_energy_from_all_areas(area_inputs)
    net_total = current_solar_production + total_energy
    nzeb_possible = net_total >= energy_consumption
    carbon_emission_reduction = total_energy * CARBON_EMISSION_FACTOR_INDIA

    st.session_state['total_energy'] = total_energy
    st.session_state['net_total'] = net_total
    st.session_state['breakdown'] = breakdown
    st.session_state['nzeb_possible'] = nzeb_possible
    st.session_state['energy_consumption'] = energy_consumption
    st.session_state['current_solar_production'] = current_solar_production
    st.session_state['area_inputs'] = area_inputs
    st.session_state['carbon_emission_reduction'] = carbon_emission_reduction

if 'total_energy' in st.session_state:
    total_energy = st.session_state['total_energy']
    net_total = st.session_state['net_total']
    breakdown = st.session_state['breakdown']
    nzeb_possible = st.session_state['nzeb_possible']
    energy_consumption = st.session_state['energy_consumption']
    current_solar_production = st.session_state['current_solar_production']
    area_inputs = st.session_state['area_inputs']
    carbon_emission_reduction = st.session_state['carbon_emission_reduction']

    st.subheader("Energy Analysis")
    st.write(f"Total BIPV Energy Generation: {total_energy:.2f} kWh/year")
    st.write(f"Including Rooftop Solar: {net_total:.2f} kWh/year")
    st.write(f"Building Demand: {energy_consumption:.2f} kWh/year")
    st.write(f"NZEB Achievable: {'Yes' if nzeb_possible else 'No'}")
    st.write(f"Estimated Annual Carbon Reduction: {carbon_emission_reduction:.2f} kg CO₂")

    st.subheader("Orientation-wise Energy Contribution")
    for k, v in breakdown.items():
        st.write(f"{k.capitalize()}: {v:.2f} kWh/year")

    if gemini_api_key:
        if st.button("Get AI-Generated NZEB Plan"):
            with st.spinner("Generating plan using Gemini..."):
                if nzeb_possible:
                    prompt = f"""
You are an expert in sustainable building design. Given the following building energy data, generate a strategy to achieve Net Zero Energy:

- Annual Energy Consumption: {energy_consumption:.2f} kWh
- Current Rooftop Solar: {current_solar_production:.2f} kWh
- BIPV Energy Potential: {total_energy:.2f} kWh
- Combined Solar Potential: {net_total:.2f} kWh
- Carbon Emission Reduction: {carbon_emission_reduction:.2f} kg CO₂
- Area Availability (m²): South={area_inputs['south']}, West={area_inputs['west']}, East={area_inputs['east']}, North={area_inputs['north']}, Water={area_inputs['water']}, Plants={area_inputs['plants']}

Provide a structured plan to implement BIPVs for NZEB achievement with Summary, Orientation Strategy, Hardware Recommendations, Energy Efficiency Recommendations, and Carbon Impact.
"""
                else:
                    prompt = f"""
You are an expert in sustainable building design. The following building data was provided for Net Zero Energy Building (NZEB) evaluation, but the target could not be achieved:

- Annual Energy Consumption: {energy_consumption:.2f} kWh
- Current Rooftop Solar: {current_solar_production:.2f} kWh
- BIPV Energy Potential: {total_energy:.2f} kWh
- Combined Solar Potential: {net_total:.2f} kWh
- Carbon Emission Reduction: {carbon_emission_reduction:.2f} kg CO₂
- Area Availability (m²): South={area_inputs['south']}, West={area_inputs['west']}, East={area_inputs['east']}, North={area_inputs['north']}, Water={area_inputs['water']}, Plants={area_inputs['plants']}

Recommend strategies to move toward NZEB compliance. Include suggestions on:
1. Increasing BIPV surface area or output
2. Reducing energy consumption
3. Adding energy storage or demand management
4. Efficient hardware choices
5. Passive and active design improvements
"""
                try:
                    model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
                    response = model.generate_content(prompt)
                    plan = response.text
                    st.success("NZEB Plan Generated")
                    st.markdown(plan)
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.warning("Please set your GEMINI_API_KEY in the .env file.")
