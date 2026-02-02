import json
import argparse
import os
import sys

SETUP_FILE = 'saved_setups.json'
BRAND_FILE = 'brand_db.json'

BRANDS = {
    'thermarest_neoair_xtherm': {'type': 'pad', 'r': 5.7, 'note': 'NeoAir XTherm — review consensus R≈5.7'},
    'thermarest_neoair_xlite': {'type': 'pad', 'r': 4.2, 'note': 'NeoAir XLite — reported R≈4.2'},
    'nemo_tensor_allseason': {'type': 'pad', 'r': 5.4, 'note': 'NEMO Tensor All-Season — spec R≈5.4'},
    'seatosummit_ultralight': {'type': 'pad', 'r': 3.1, 'note': 'Sea to Summit Ultralight Insulated — tested R≈3.1'},
    'thermarest_trailpro': {'type': 'pad', 'r': 4.4, 'note': 'Therm-a-Rest Trail Pro — spec R≈4.4'}
}


def sum_r(values):
    return sum(float(v or 0.0) for v in values)


def effective_r(R, wind=5.0, cond='calm'):
    wind_reduction = min(0.6, wind / 60.0)
    if cond == 'light':
        wind_reduction *= 0.5
    if cond in ('windy', 'gale'):
        wind_reduction = min(0.8, wind / 40.0)
    r1 = R * (1.0 - wind_reduction)
    if cond in ('rain', 'wet_cold'):
        r1 *= 0.8
    if cond == 'snow':
        r1 *= 0.95
    return max(0.01, r1)


def biometric_defaults(profile='adult', height='regular', sex='male', weight=None):
    if profile == 'kid':
        return 14.0, 160.0
    if profile == 'adult':
        area = 22.0 if height == 'tall' else 19.0 if height == 'regular' else 17.0
        metabolic = 220.0 if sex == 'male' else 200.0
        if weight is not None:
            metabolic *= max(0.8, min(1.2, float(weight) / 170.0))
        return area, metabolic
    if profile == 'senior':
        area = 21.0 if height == 'tall' else 18.0 if height == 'regular' else 16.0
        metabolic = 200.0 if sex == 'male' else 180.0
        if weight is not None:
            metabolic *= max(0.8, min(1.2, float(weight) / 150.0))
        return area, metabolic
    return 20.0, 200.0


def heat_loss_per_hr(t_body, t_out, area, R_eff):
    return (t_body - t_out) * area / R_eff


def load_setups():
    if not os.path.exists(SETUP_FILE):
        return {}
    try:
        with open(SETUP_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_setups(obj):
    with open(SETUP_FILE, 'w') as f:
        json.dump(obj, f, indent=2)


def list_brands():
    if not os.path.exists(BRAND_FILE):
        return BRANDS
    try:
        with open(BRAND_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return BRANDS


def cli():
    parser = argparse.ArgumentParser(description='ColdCheck CLI')
    parser.add_argument('--ui', action='store_true')
    parser.add_argument('--jacket', type=float, default=0.0)
    parser.add_argument('--bag', type=float, default=0.0)
    parser.add_argument('--pad', type=float, default=0.0)
    parser.add_argument('--layers', type=float, default=0.0)
    parser.add_argument('--extremities', type=float, default=0.0)
    parser.add_argument('--shelter', type=float, default=0.0)
    parser.add_argument('--duration', type=float, default=12.0)
    parser.add_argument('--condition', type=str, default='calm')
    parser.add_argument('--wind', type=float, default=5.0)
    parser.add_argument('--tout', type=float, default=32.0)
    parser.add_argument('--tbody', type=float, default=98.6)
    parser.add_argument('--profile', choices=['kid', 'adult', 'senior'], default='adult')
    parser.add_argument('--height', choices=['short', 'regular', 'tall'], default='regular')
    parser.add_argument('--sex', choices=['male', 'female'], default='male')
    parser.add_argument('--weight', type=float, default=None)
    parser.add_argument('--save', type=str, default=None)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--load', type=str, default=None)
    parser.add_argument('--list-brands', action='store_true')
    parser.add_argument('--brand', type=str, default=None)

    args = parser.parse_args()

    if args.ui:
        run_streamlit_app()
        return

    if args.list:
        for k in sorted(load_setups().keys()):
            print(k)
        return

    if args.list_brands:
        for k, v in list_brands().items():
            print(k, '->', v)
        return

    if args.load:
        setup = load_setups().get(args.load)
        if setup is None:
            print('No such setup:', args.load)
            return
        for k, v in setup.items():
            if hasattr(args, k):
                setattr(args, k, v)

    if args.brand:
        brand = list_brands().get(args.brand)
        if brand and brand.get('type') == 'pad':
            args.pad = brand.get('r', args.pad)

    values = [args.jacket, args.bag, args.pad, args.layers, args.extremities, args.shelter]
    R_total = sum_r(values)
    area, metabolic = biometric_defaults(args.profile, args.height, args.sex, args.weight)
    R_eff = effective_r(R_total, wind=args.wind, cond=args.condition)
    q = heat_loss_per_hr(args.tbody, args.tout, area, R_eff)

    total_q = q * args.duration
    total_met = metabolic * args.duration

    print(f'Total R: {R_total:.2f} (effective: {R_eff:.2f})')
    print(f'Hourly heat loss: {q:.1f} BTU/hr')
    print(f'Total heat loss: {total_q:.0f} BTU')
    print(f'Metabolic: {metabolic:.0f} BTU/hr ({total_met:.0f} total)')
    print(f'Net: {total_met - total_q:+.0f} BTU')

    if args.save:
        setups = load_setups()
        setups[args.save] = vars(args)
        setups[args.save].pop('list', None)
        save_setups(setups)


def run_streamlit_app():
    import streamlit as st

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


if __name__ == '__main__':
    cli()
