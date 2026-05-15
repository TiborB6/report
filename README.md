# Analyst Report

This is a project to automatically create a analyst report based on data from alpha vantage and yahoo finance. This is only for a university project not a full scale report.
The script is best used with S&P 500 companies and with dividend based stocks.
# Usage

Get repo
```commandline
git clone https://github.com/TiborB6/report.git 
```

Install requirements
```commandline
pip install -r requirements.txt
```

Add .env file
```commandline
touch .env
nano .env
```

Add your keys
```commandline
API_KEY = "YOU_ALPHAVANTAGE_KEY"
GOOGLE_API_KEY = "YOUR_GOOGLE_AI_LAB_KEY"
```

Run report generation
```commandline
quarto render report.qmd --to pdf --execute-params '{"ticker":"YOUR_COMPANY_TICKER"}'
```