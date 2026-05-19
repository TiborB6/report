# Analyst Report

This is a project to automatically create a analyst report based on data from alpha vantage and yahoo finance. This is only for a university project not a full scale report.
The script is best used with S&P 500 companies and with dividend based stocks.

# Usage
```commandline
python3 generate_report.py [-l] [-c] <TICKER>
```

positional arguments: <br>
  ticker         Stock ticker symbol

optional arguments: <br>
  -l set local no fresh data fetched <br>
  -c deletes local data

output: report.pdf

# Install
1. Get repo
2. Install requirements
3. Add .env file
```commandline
git clone https://github.com/TiborB6/report.git 
pip install -r requirements.txt
touch .env
```

Add your keys to .env
```commandline
API_KEY = "YOU_ALPHAVANTAGE_KEY"
GOOGLE_API_KEY = "YOUR_GOOGLE_AI_LAB_KEY"
FINNHUB_API_KEY="YOUR_FINNHUB_KEY"
```