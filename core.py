import json
import os

BRANDS = {
    'thermarest_neoair_xtherm': {'type': 'pad', 'r': 5.7, 'note': 'NeoAir XTherm — review consensus R≈5.7'},
    'thermarest_neoair_xlite': {'type': 'pad', 'r': 4.2, 'note': 'NeoAir XLite — reported R≈4.2'},
    'nemo_tensor_allseason': {'type': 'pad', 'r': 5.4, 'note': 'NEMO Tensor All-Season — spec R≈5.4'},
    'seatosummit_ultralight': {'type': 'pad', 'r': 3.1, 'note': 'Sea to Summit Ultralight Insulated — tested R≈3.1'},
    'thermarest_trailpro': {'type': 'pad', 'r': 4.4, 'note': 'Therm-a-Rest Trail Pro — spec R≈4.4'}
}

SETUP_FILE = 'saved_setups.json'
BRAND_FILE = 'brand_db.json'


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
