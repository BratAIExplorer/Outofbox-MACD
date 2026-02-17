import sys
sys.stdout.reconfigure(encoding='utf-8')

def format_report(fundamental, technical):
    # Clean Stoploss/Target text (Rounded)
    try:
       sl = f"{float(technical['Support'].split('(')[0].strip()):.2f}"
       tgt = f"{float(technical['Resistance'].split('(')[0].strip()):.2f}"
       cmp_val = f"{float(technical['Price']):.2f}"
    except:
       sl = technical['Support'].split('(')[0].strip()
       tgt = technical['Resistance'].split('(')[0].strip()
       cmp_val = technical['Price']

    # Clean Name (Remove .NS)
    clean_name = fundamental['name'].replace('.NS', '')

    msg = f"""Stock: {clean_name}
Recommendation: Buy
CMP: {cmp_val}
Short term target: {tgt}
Stoploss: {sl}

If entering a Day or Swing trade, make sure to use the specified Stoploss."""
    return msg.strip()

def current_style_target_hit(name, curr_high):
    return f"""Stock: {name}
Status: Target Achieved 🎯
Price Hit: {curr_high:.2f}
"""

print("=== NEW STOCK ALERT (e.g. from Scanner) ===")
fundamental = {'name': 'Tata Motors'}
technical = {'Price': '150.00', 'Resistance': '160.00', 'Support': '140.00'}
print(format_report(fundamental, technical))

print("\n\n=== TARGET MET ALERT ===")
print(current_style_target_hit("Tata Motors", 160.50))
