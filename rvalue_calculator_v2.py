"""
rvalue_calculator_v2.py

Updated: seeded brand DB, biometric heights (short/regular/tall), improved CLI options.

Usage:
  CLI: python rvalue_calculator_v2.py --help
  Streamlit: streamlit run rvalue_calculator_v2.py

Seeded brand R-values (pads) are taken from manufacturer specs and reviews (examples: Therm-a-Rest NeoAir XTherm, NEMO Tensor, Sea to Summit Ultralight).
"""

import json
import argparse
import os
from math import isfinite

SETUP_FILE = 'saved_setups.json'
BRAND_FILE = 'brand_db.json'

# --- Seeded brand DB (pads) ---
# These are example R-values gathered from manufacturer pages and reviews (treat as starting points).
BRANDS = {
    'thermarest_neoair_xtherm': {'type':'pad','r':5.7,'note':'NeoAir XTherm — review consensus R≈5.7'},
    'thermarest_neoair_xlite': {'type':'pad','r':4.2,'note':'NeoAir XLite — reported R≈4.2'},
    'nemo_tensor_allseason': {'type':'pad','r':5.4,'note':'NEMO Tensor All-Season — spec R≈5.4'},
    'seatosummit_ultralight': {'type':'pad','r':3.1,'note':'Sea to Summit Ultralight Insulated — tested R≈3.1'},
    'thermarest_trailpro': {'type':'pad','r':4.4,'note':'Therm-a-Rest Trail Pro — spec R≈4.4'}
}

# write brand file if missing
if not os.path.exists(BRAND_FILE):
    with open(BRAND_FILE,'w') as f:
        json.dump(BRANDS,f,indent=2)

# --- Core math -------------------------------------------------

def sum_r(values):
    return sum(float(v or 0) for v in values)


def effective_r(R, wind=5, cond='calm'):
    wind_reduction = min(0.6, wind / 60.0)
    if cond == 'light':
        wind_reduction *= 0.5
    if cond == 'gale':
        wind_reduction = min(0.8, wind / 40.0)
    r1 = R * (1 - wind_reduction)
    if cond in ('rain','wet_cold'):
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
        if weight:
            metabolic *= max(0.8, min(1.2, float(weight) / 170.0))
        return area, metabolic
    if profile == 'senior':
        area = 21.0 if height == 'tall' else 18.0 if height == 'regular' else 16.0
        metabolic = 200.0 if sex == 'male' else 180.0
        if weight:
            metabolic *= max(0.8, min(1.2, float(weight) / 150.0))
        return area, metabolic
    return 20.0, 200.0


def heat_loss_per_hr(t_body, t_out, area, R_eff):
    return (t_body - t_out) * area / R_eff


# --- Persistence ------------------------------------------------

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
    try:
        with open(BRAND_FILE,'r') as f:
            return json.load(f)
    except Exception:
        return BRANDS


# --- CLI --------------------------------------------------------

def cli():
    parser = argparse.ArgumentParser(description='R-value heat-balance CLI (v2)')
    parser.add_argument('--jacket', type=float, default=0.0)
    parser.add_argument('--bag', type=float, default=0.0)
    parser.add_argument('--pad', type=float, default=0.0)
    parser.add_argument('--layers', type=float, default=0.0)
    parser.add_argument('--extremities', type=float, default=0.0)
    parser.add_argument('--shelter', type=float, default=0.0)
    parser.add_argument('--duration', type=float, default=12)
    parser.add_argument('--condition', type=str, default='calm')
    parser.add_argument('--wind', type=float, default=5)
    parser.add_argument('--tout', type=float, default=32.0)
    parser.add_argument('--tbody', type=float, default=98.6)
    parser.add_argument('--profile', choices=['kid','adult','senior'], default='adult')
    parser.add_argument('--height', choices=['short','regular','tall'], default='regular')
    parser.add_argument('--sex', choices=['male','female'], default='male')
    parser.add_argument('--weight', type=float, default=None)
    parser.add_argument('--save', type=str, default=None, help='Save this setup by name')
    parser.add_argument('--list', action='store_true', help='List saved setups')
    parser.add_argument('--load', type=str, default=None, help='Load a named setup and run it')
    parser.add_argument('--list-brands', action='store_true', help='List seeded brands')
    parser.add_argument('--brand', type=str, default=None, help='Apply seeded brand (pads) e.g. thermarest_neoair_xtherm')

    args = parser.parse_args()

    if args.list:
        s = load_setups()
        if not s:
            print('No saved setups.')
            return
        for k in sorted(s.keys()):
            print(k)
        return

    if args.list_brands:
        b = list_brands()
        for k,v in b.items():
            print(k, '->', v)
        return

    if args.load:
        s = load_setups().get(args.load)
        if not s:
            print('No such setup:', args.load)
            return
        for k,v in s.items():
            if hasattr(args, k):
                setattr(args, k, v)
        print('Loaded setup:', args.load)

    # apply brand if requested
    if args.brand:
        b = list_brands().get(args.brand)
        if not b:
            print('Unknown brand key:', args.brand)
        else:
            if b.get('type') == 'pad':
                args.pad = b.get('r', args.pad)
                print('Applied brand pad R =', args.pad)

    values = [args.jacket, args.bag, args.pad, args.layers, args.extremities, args.shelter]
    R_total = sum_r(values)
    area, metabolic = biometric_defaults(args.profile, args.height, args.sex, args.weight)
    R_eff = effective_r(R_total, wind=args.wind, cond=args.condition)
    q = heat_loss_per_hr(args.tbody, args.tout, area, R_eff)
    total_q = q * args.duration
    total_met = metabolic * args.duration
    net = total_met - total_q

    print(f'Total R: {R_total:.2f} (effective: {R_eff:.2f})')
    print(f'Hourly heat loss: {q:.1f} BTU/hr')
    print(f'Total heat loss for {args.duration} hr: {total_q:.0f} BTU')
    print(f'Metabolic: {metabolic:.0f} BTU/hr ({total_met:.0f} total)')
    print(f'Net over trip: {net:+.0f} BTU')

    if args.save:
        setups = load_setups()
        setups[args.save] = vars(args)
        if 'list' in setups[args.save]: del setups[args.save]['list']
        save_setups(setups)
        print('Saved setup as:', args.save)


# --- Streamlit app ---------------------------------------------

def run_streamlit_app():
    try:
        import streamlit as st
    except Exception:
        raise RuntimeError('Streamlit not installed. pip install streamlit')

    st.set_page_config(page_title='R-value Pro')
    st.title('R‑Value Pro — Outdoor Insulation Calculator')

    # sidebar: brands + saved setups
    with st.sidebar:
        st.header('Seeded brands')
        b = list_brands()
        for k,v in b.items():
            st.write(f"{k}: R={v['r']} — {v.get('note','')}")
        st.header('Saved setups')
        name = st.text_input('Name to save')
        if st.button('Save current setup'):
            s = { 'jacket': st.session_state.get('jacket',0), 'bag': st.session_state.get('bag',0), 'pad': st.session_state.get('pad',0), 'layers': st.session_state.get('layers',0), 'extremities': st.session_state.get('extremities',0), 'shelter': st.session_state.get('shelter',0), 'duration': st.session_state.get('duration',12), 'condition': st.session_state.get('condition','calm'), 'wind': st.session_state.get('wind',5), 'tout': st.session_state.get('tout',32), 'tbody': st.session_state.get('tbody',98.6), 'profile': st.session_state.get('profile','adult'), 'height': st.session_state.get('height','regular'), 'sex': st.session_state.get('sex','male'), 'weight': st.session_state.get('weight',None) }
            if not name:
                st.warning('Provide a name to save.')
            else:
                s_all = load_setups()
                s_all[name] = s
                save_setups(s_all)
                st.success('Saved as ' + name)

    col1, col2 = st.columns(2)
    with col1:
        jacket = st.number_input('Jacket R', value=0.5, format='%.2f', key='jacket')
        bag = st.number_input('Sleeping bag R', value=4.0, format='%.2f', key='bag')
        pad = st.number_input('Sleeping pad R', value=3.5, format='%.2f', key='pad')
        layers = st.number_input('Base+mid layers R', value=1.0, format='%.2f', key='layers')
        extremities = st.number_input('Hat & gloves R', value=0.4, format='%.2f', key='extremities')
        shelter = st.number_input('Shelter R', value=0.5, format='%.2f', key='shelter')

    with col2:
        duration = st.selectbox('Duration', [('Overnight (~12 hr)',12), ('1 day (24 hr)',24), ('2–7 days (3 days default)',72), ('Thru-hike (~2 weeks)',336), ('Extended (~3 weeks)',504)], index=0, key='duration')
        condition = st.selectbox('Weather condition', ['calm','light','windy','gale','rain','snow','wet_cold'], index=0, key='condition')
        wind = st.number_input('Wind (mph)', value=5, step=1, key='wind')
        tout = st.number_input('Ambient temp (°F)', value=32.0, key='tout')
        tbody = st.number_input('Body temp (°F)', value=98.6, key='tbody')
        profile = st.radio('Biometric profile', ['kid','adult','senior'], index=1, key='profile')
        if profile == 'adult':
            height = st.selectbox('Height', ['short','regular','tall'], key='height')
            sex = st.selectbox('Sex', ['male','female'], key='sex')
            weight = st.number_input('Weight (lbs)', value=170, key='weight')
        elif profile == 'senior':
            height = st.selectbox('Height', ['short','regular','tall'], key='height')
            sex = st.selectbox('Sex', ['male','female'], key='sex')
            weight = st.number_input('Weight (lbs)', value=150, key='weight')
        else:
            height='regular'; sex='male'; weight=None

    # brand quick-apply
    st.subheader('Brands (quick-fill)')
    brands = list_brands()
    sel = st.selectbox('Apply product', [''] + list(brands.keys()))
    if sel:
        if st.button('Apply selected product'):
            prod = brands[sel]
            if prod.get('type') == 'pad':
                st.session_state['pad'] = prod.get('r', st.session_state.get('pad',3.5))
                st.experimental_rerun()

    # compute
    values = [jacket, bag, pad, layers, extremities, shelter]
    R_total = sum_r(values)
    area, metabolic = biometric_defaults(profile, height, sex, weight)
    R_eff = effective_r(R_total, wind=wind, cond=condition)
    q = heat_loss_per_hr(tbody, tout, area, R_eff)

    st.markdown('**Results**')
    st.write(f'Total R: {R_total:.2f} (effective: {R_eff:.2f})')
    st.write(f'Area used (ft²): {area:.1f}')
    st.write(f'Hourly heat loss: {q:.1f} BTU/hr')
    st.write(f'Total heat loss ({duration} hr): {q*duration:.0f} BTU')
    st.write(f'Metabolic: {metabolic:.0f} BTU/hr ({metabolic*duration:.0f} total)')
    st.write(f'Net: {metabolic*duration - q*duration:+.0f} BTU')


if __name__ == '__main__':
    cli()
