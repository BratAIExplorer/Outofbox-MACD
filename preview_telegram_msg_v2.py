from telegram_bot import ResearchBot

# Dummy Technical Data
tech_data = {
    'Symbol': 'MOCKSTOCK.NS',
    'Price': 1450.50,
    'Above_20DMA': True,
    'Resistance': '1550 (Blue Sky)',
    'Support': '1420 (20 DMA)',
    'MACD_Cross_Date': '25-Jan-2026',
    'RSI': 62.50,
    'SMA_20': 1420.00,
    'SMA_50': 1380.00
}

# Dummy Fundamental Data
fund_data = {
    'name': 'Mock Reliance Ind',
    'sector': 'Oil & Gas',
    'q_results': 'Rev Growth 12.5%',
    'actions': 'Upcoming Div 10.0 (Ex: 05-Feb)'
}

# Use the actual bot formatter
bot = ResearchBot()
formatted_msg = bot.format_report(tech_data, fund_data)

print("-" * 30)
print(formatted_msg)
print("-" * 30)
