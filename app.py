import streamlit as st
from core import sum_r, effective_r, biometric_defaults, heat_loss_per_hr, list_brands

st.set_page_config(page_title='ColdCheck', layout='wide')
st.title('ColdCheck')

with st.sidebar:
    st.header('Seeded brands')
    for k, v in list_brands().items():
        st.write(f"{k}: R={v['r']} — {v.get('note', '')}")

col1, col2 = st.columns(2)

with col1:
    jacket = st.number_input('Jacket R', value=0.5)
    bag = st.number_input('Sleeping bag R', value=4.0)
    pad = st.number_input('Sleeping pad R', value=3.5)
    layers = st.number_input('Base and mid layers R', value=1.0)
    extremities = st.number_input('Hat and gloves R', value=0.4)
    shelter = st.number_input('Shelter R', value=0.5)

with col2:
    duration_label = st.selectbox(
        'Trip duration',
        ['Overnight (12 hr)', 'Short trip (72 hr)', 'Extended trip (336 hr)', 'Long thru-hike (504 hr)']
    )
    duration = {'Overnight (12 hr)': 12, 'Short trip (72 hr)': 72, 'Extended trip (336 hr)': 336, 'Long thru-hike (504 hr)': 504}[duration_label]

    condition = st.selectbox('Weather condition', ['calm', 'light', 'windy', 'gale', 'rain', 'snow', 'wet_cold'])
    wind = st.number_input('Wind (mph)', value=5)
    tout = st.number_input('Ambient temperature (°F)', value=32.0)
    tbody = st.number_input('Body temperature (°F)', value=98.6)
    profile = st.radio('Age group', ['kid', 'adult', 'senior'], index=1)

    if profile in ('adult', 'senior'):
        height = st.selectbox('Height', ['short', 'regular', 'tall'])
        sex = st.selectbox('Sex', ['male', 'female'])
        weight = st.number_input('Weight (lb)', value=170 if profile == 'adult' else 150)
    else:
        height = 'regular'
        sex = 'male'
        weight = None

values = [jacket, bag, pad, layers, extremities, shelter]
R_total = sum_r(values)
area, metabolic = biometric_defaults(profile, height, sex, weight)
R_eff = effective_r(R_total, wind=wind, cond=condition)
q = heat_loss_per_hr(tbody, tout, area, R_eff)

st.subheader('Results')
st.write(f'Total R: {R_total:.2f} (effective: {R_eff:.2f})')
st.write(f'Hourly heat loss: {q:.1f} BTU/hr')
st.write(f'Total heat loss: {q * duration:.0f} BTU')
st.write(f'Metabolic: {metabolic:.0f} BTU/hr ({metabolic * duration:.0f} total)')
st.write(f'Net: {metabolic * duration - q * duration:+.0f} BTU')
