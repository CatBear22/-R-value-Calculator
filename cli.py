import argparse
from core import sum_r, effective_r, biometric_defaults, heat_loss_per_hr, load_setups, save_setups, list_brands

def cli():
    parser = argparse.ArgumentParser(description='ColdCheck CLI')
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

    args = parser.parse_args()

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

if __name__ == '__main__':
    cli()
