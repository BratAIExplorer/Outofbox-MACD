
def current_style(name, curr_high, target):
    return f"""🎯 **TARGET HIT: {name}**
Price touched {curr_high:.2f}
Target: {target:.2f}

If entering a Day or Swing trade, make sure to use the specified Stoploss."""

def proposed_style(name, curr_high, target):
    return f"""Stock: {name}
Status: Target Achieved 🎯
Price Hit: {curr_high:.2f}
Target: {target:.2f}
Result: Profit Booked ✅

If entering a Day or Swing trade, make sure to use the specified Stoploss."""

name = "Tata Steel"
curr_high = 155.50
target = 155.00

print("=== CURRENT STYLE ===")
print(current_style(name, curr_high, target))
print("\n=== PROPOSED STYLE ===")
print(proposed_style(name, curr_high, target))
