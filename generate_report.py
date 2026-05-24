import pandas as pd
from dotenv import load_dotenv
import os
from utils.fetch_data import fetch_financial_data_yfinance, fetch_financial_data, cleanup, fetch_and_save_single_endpoint
from utils.fin.ddm import get_ddm_valuation
from utils.load_data import load_stock_data, load_fundamental_data, load_overview_data
from utils.fin.key_metrics import calculate_financial_metrics
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from utils.gemini import query_gemini
from utils.fin.financial_data import key_figures, key_growth_rates, per_share_values, income_statement_overview, balance_sheet_overview, cashflow_overview
from utils.competitors import get_competitors
from utils.news import get_latest_news
import subprocess
import time
from utils.latex import LatexTable, format_address, latex_escape
import argparse

load_dotenv(".env")

# ------------------- Get ticker from command line -------------------
parser = argparse.ArgumentParser()
parser.add_argument("ticker", help="Stock ticker symbol")
parser.add_argument("-l", "--local", action="store_true", help="Set local mode")
parser.add_argument("-c", "--clean", action="store_true", help="Set clean mode")
args = parser.parse_args()

TICKER = args.ticker.upper()
BENCHMARK = "SPY"
local = args.local
clean = args.clean

# ------------------- Data fetching ---------------------------------
competitors = get_competitors(TICKER, use_top_n=5)
if not local:
    for competitor in competitors:
        fetch_and_save_single_endpoint(
            symbol=competitor,
            endpoint_name='overview',
            endpoint_params={'function': 'OVERVIEW', 'file_suffix': 'overview', 'full_history': False},
            api_key=os.getenv("API_KEY")
        )

        time.sleep(2)

    fetch_financial_data(TICKER, api_key=os.getenv("API_KEY"))
    fetch_financial_data_yfinance(TICKER)
    fetch_financial_data_yfinance(BENCHMARK)

# ------------------- Data loading (parameterized) -------------------
overview_data_list = []
for competitor in competitors:
    data = load_overview_data(competitor)
    overview_data_list.append(data)

if not local:
    if overview_data_list:
        fetch_financial_data_yfinance(overview_data_list[0]['Symbol'])

stock = load_stock_data(TICKER).reset_index().rename(columns={"index": "fiscalDateEnding"})
balance = load_fundamental_data(TICKER, type="balance").reset_index().rename(columns={"index": "fiscalDateEnding"})
earnings = load_fundamental_data(TICKER, type="earnings").reset_index().rename(columns={"index": "fiscalDateEnding"})
cash = load_fundamental_data(TICKER, type="cash").reset_index().rename(columns={"index": "fiscalDateEnding"})
spy = load_stock_data(BENCHMARK).reset_index().rename(columns={"index": "fiscalDateEnding"})
overview = load_overview_data(TICKER)

competitor_stock = pd.DataFrame()
if overview_data_list:
    competitor_stock = load_stock_data(overview_data_list[0]['Symbol']).reset_index().rename(columns={"index": "fiscalDateEnding"})

def normalize_datetime_column(df, col='fiscalDateEnding'):
    df[col] = pd.to_datetime(df[col])
    if df[col].dt.tz is not None:
        df[col] = df[col].dt.tz_localize(None)
    return df

balance = normalize_datetime_column(balance)
earnings = normalize_datetime_column(earnings)
cash = normalize_datetime_column(cash)
stock = normalize_datetime_column(stock)
spy = normalize_datetime_column(spy)
if not competitor_stock.empty:
    competitor_stock = normalize_datetime_column(competitor_stock)

fundamental = pd.merge(balance, earnings, on='fiscalDateEnding', how='inner')
fundamental = pd.merge(fundamental, cash, on='fiscalDateEnding', how='inner')
stock_sorted = stock.sort_values('fiscalDateEnding')
fundamental_sorted = fundamental.sort_values('fiscalDateEnding')
fundamental_stock = pd.merge_asof(fundamental_sorted, stock_sorted, on='fiscalDateEnding', direction='backward')

ddm = get_ddm_valuation(fundamental, overview)
forward_target = ddm.iloc[1]['Target Price per Share']
curr_price = stock.iloc[-1]['close']

if curr_price * 1.10 < forward_target:
    evaluation = "BUY"
elif curr_price * 0.90 > forward_target:
    evaluation = "SELL"
else:
    evaluation = "HOLD"

# ------------------- Helper: write LaTeX to file -------------------
tex_lines = []
def tex_print(*args, end='\n'):
    tex_lines.append(' '.join(str(a) for a in args) + end)

# ------------------- LaTeX preamble -------------------
company_name = overview['Name'].replace('&', '\\&')
tex_print(r"\documentclass[11pt]{article}")
tex_print(r"\usepackage[utf8]{inputenc}")
tex_print(r"\usepackage[T1]{fontenc}")
tex_print(r"\usepackage{geometry}")
tex_print(r"\geometry{left=0.5in, right=0.5in, top=0.8in, bottom=0.8in}")
tex_print(r"\usepackage{fancyhdr}")
tex_print(r"\pagestyle{fancy}")
tex_print(f"\\fancyhead[L]{{{company_name}}}")
tex_print(r"\fancyhead[R]{\thepage}")
tex_print(r"\renewcommand{\headrulewidth}{0.4pt}")
tex_print(r"\usepackage{titlesec}")
tex_print(r"\titleformat{\section}{\Large\bfseries\sffamily}{}{0em}{}")
tex_print(r"\titleformat{\subsection}{\large\bfseries\sffamily}{}{0em}{}")
tex_print(r"\usepackage{graphicx}")
tex_print(r"\usepackage{booktabs}")
tex_print(r"\usepackage{enumitem}")
tex_print(r"\usepackage{longtable}")
tex_print(r"\usepackage{parskip}")
tex_print(r"\usepackage{wrapfig}")
tex_print(r"\usepackage{tabularx}")
tex_print(r"\usepackage{url}")
tex_print(r"\usepackage{xcolor}")
tex_print(r"\usepackage{multicol}")
tex_print(r"\renewcommand{\familydefault}{\sfdefault}")
tex_print(r"\begin{document}")
tex_print(r"\titlespacing{\section}{0pt}{0.6ex}{0.6ex}")
tex_print(r"\titlespacing{\subsection}{0pt}{0.2ex}{0.2ex}")
tex_print(r"\thispagestyle{plain}")

# ------------------- Header section -------------------
tex_print(r"\noindent")
tex_print(r"{\Large \textbf{Financial Report - " + company_name + r" (" + overview['Symbol'] + r")}}\\")
tex_print(r"\noindent\textcolor{blue}{\rule{\linewidth}{1.pt}}")
tex_print(r"\vspace{0.3cm}")
tex_print(r"\noindent")
tex_print(r"\begin{minipage}{0.45\linewidth}")
tex_print(r"\textbf{Sector:} " + overview['Sector'].lower())
tex_print(r"\end{minipage}")
tex_print(r"\hfill")
tex_print(r"\begin{minipage}{0.45\linewidth}")
tex_print(r"\textbf{Industry:} " + overview['Industry'].lower())
tex_print(r"\end{minipage}")
tex_print(r"\vspace{0.5cm}")
tex_print(r"\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}} l l l l @{}}")
tex_print(r"\textbf{Recommendation} & \textbf{Price} & \textbf{12-Month Target Price} & \textbf{Investment Style} \\")
tex_print(f"{evaluation} & \\${stock.iloc[-1]['close']:.2f} & \\${forward_target} & {overview['AssetType']} \\\\")
tex_print(r"\end{tabular*}")
tex_print(fr"{overview['Description']}")

# ------------------- Key Metrics -------------------
tex_print(r"\section*{Key Metrics}")
metrics_dict = calculate_financial_metrics(stock, fundamental_stock, overview)
items = list(metrics_dict.items())
n = len(items)
col_size = (n + 2) // 3
col1_items = items[:col_size]
col2_items = items[col_size:2*col_size]
col3_items = items[2*col_size:]
tex_print(r"\noindent")
tex_print(r"\begin{minipage}{0.32\linewidth}")
tex_print(r"\raggedright")
for key, value in col1_items:
    tex_print(f"{key}: {value}\\\\")
tex_print(r"\end{minipage}")
tex_print(r"\hfill")
tex_print(r"\begin{minipage}{0.32\linewidth}")
tex_print(r"\raggedright")
for key, value in col2_items:
    tex_print(f"{key}: {value}\\\\")
tex_print(r"\end{minipage}")
tex_print(r"\hfill")
tex_print(r"\begin{minipage}{0.32\linewidth}")
tex_print(r"\raggedright")
for key, value in col3_items:
    tex_print(f"{key}: {value}\\\\")
tex_print(r"\end{minipage}")
tex_print(r"\vspace{0.5cm}")

# ------------------- Stock price development (figure) -------------------
stock['fiscalDateEnding'] = pd.to_datetime(stock['fiscalDateEnding'])
stock = stock[stock['volume'] > 1000]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 4.5),
                               gridspec_kw={'height_ratios': [2, 1]},
                               sharex=True)
ax1.plot(stock['fiscalDateEnding'], stock['close'], color='#0000FF', linewidth=1.5, label='Close Price')
ax1.set_ylabel('Price ($)', fontsize=11)
ax1.set_title(f'{company_name} ({TICKER}) – Stock Price & Volume', fontsize=14, fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.legend(loc='upper left')
ax2.bar(stock['fiscalDateEnding'], stock['volume'], color="#0000FF", width=1, alpha=0.7)
ax2.set_xlabel('Date', fontsize=11)
ax2.set_ylabel('Volume', fontsize=11)
ax2.grid(True, linestyle='--', alpha=0.3, axis='y')
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
fig.autofmt_xdate(rotation=45)
plt.tight_layout()
price_vol_pdf = f"{TICKER.lower()}_price_volume.pdf"
plt.savefig(price_vol_pdf, bbox_inches='tight')
plt.close()

tex_print(r"\section*{Stock Price Development}")
tex_print(r"\begin{figure}[!htb]")
tex_print(r"\centering")
tex_print(f"\\includegraphics[width=\\linewidth]{{{price_vol_pdf}}}")
tex_print(r"\end{figure}")

# ------------------- Highlights (Gemini) -------------------
tex_print(r"\begin{minipage}[t]{0.48\textwidth}")
tex_print(r"\section*{Highlights}")
highlights_prompt = f"""
 Der Umsatz des 4. Quartals 2007 stieg auf $44.1 Milliarden, bei
Weitem mehr als die erwarteten rund $38.4 Milliarden.
▫ Nach monatelangen Verhandlungen verkündete die indische
Tata Motors Ltd am 26. März 2008 die Übernahme der beiden
Ford Marken Jaguar und Land Rover. Der Verkauf der
defizitären Luxus Marke Jaguar und der ebenfalls rote Zahlen
schreibenden Tochter Land Rover soll die Kassen von Ford MC
mit ungefähr $2.3 Mrd. füllen. Ford sollte es dadurch möglich
sein, sich auf den wichtigen Massenmarkt zu konzentrieren, um
so einen Weg aus der Verlustzone zu finden. (Kombinierter
Verlust von $15,393 Millionen in den Jahren 2006 & 2007)
▫ Der US Automarkt stellt aufgrund stetiger Marktanteilsverluste
aktuell das größte Problem für Ford dar. (Fords US Marktanteil
sank allein im 4. Quartal 2007 um 0.7 Prozentpunkte auf
14.1%.)

Write company highlights like this in English for {TICKER}.
Use recent data (not older than 3 months). Format each bullet point with "▫" at the beginning.
Please keep it shorter the n the original about approx. 70 words.
Do not add any extra commentary or meta-instructions – only output the bullet points.
"""
highlights_text = query_gemini(highlights_prompt)
tex_print(latex_escape(highlights_text).replace('\n', '\\\\'))
tex_print(r"\end{minipage}")
tex_print(r"\hfill")

# ------------------- Risk Assessment -------------------
tex_print(r"\begin{minipage}[t]{0.48\textwidth}")
tex_print(r"\section*{Risk Assessment}")
risk_prompt = f"""
ngesichts der aktuellen wirtschaftlichen 
Lage in den USA lässt sich feststellen, dass 
die Aufgabe, Ford MC zu reorganisieren 
und zu restrukturieren, sicher nicht 
einfacher geworden ist und dass Ford die 
Suche nach Einsparungsmaßnahmen 
fortsetzen wird.
Das Abschwächen der US-Wirtschaft und 
die immer noch bestehende Möglichkeit 
einer Rezession führten bereits zu 
schwächeren US Verkaufszahlen (-4.1%)
im Januar 08.
Based on this the risk assesment is: HIGH.

Write a risk assesment like this in English for {TICKER}.
Include 2-3 key risks and conclude with a risk level: LOW, MEDIUM, or HIGH.
Keep the text length similar to the example (approx 70).
Do not add any extra commentary or meta-instructions
"""
risk_text = query_gemini(risk_prompt)
tex_print(latex_escape(risk_text).replace('\n', '\\\\'))
tex_print(r"\end{minipage}")
tex_print(r"\newpage")

# ------------------- DDM -------------------
tex_print(r"\section*{Dividend Discount Model}")
tex_print(LatexTable(ddm.set_index("Year").T.to_latex(float_format="%.2f")).fit_to_width())
tex_print(r"\vspace{0.5cm}")

# ------------------- Company Overview (Gemini) -------------------
tex_print(r"\section*{Company Overview}")
overview_prompt = f"""
Die Ford Motor Company (FMC) ist ein global tätiges Unternehmen, mit den
Kerngeschäftsbereichen Automobile und Finanzdienstleistungen. Das
Automobilsegment beinhaltet folgende Kernaufgaben: Design, Entwicklung,
Herstellung, Verkauf und Service von PKWs, LKWs und Ersatzteilen. Die Ford Motor
Credit Company stellt ein ganzes Portfolio von Finanzdienstleistungen zur
Verfügung, konzentriert sich dabei jedoch hauptsächlich auf Finanzierung, Leasing
und Versicherung von Kraftfahrzeugen.
Ford ist der zweitgrößte Automobil- und Lastkraftwagenhersteller der Welt mit den
Hauptmarken Aston Martin, Ford, Jaguar, Land Rover, Lincoln, Mercury und Volvo.
Außerdem ist Ford mit 34% der Mehrheitseigentümer von Mazda. Ungefähr 80% des
Konzernumsatzes generiert Ford aus dem Verkauf von Automobilen, 2/3 davon in
Nordamerika. Die restlichen 20% werden mit den Finanzdienstleistungen der Ford
Motor Credit Company erzielt, hauptsächlich durch die Finanzierung der Ford
Vertragshändler aber auch durch die Inanspruchnahme verschiedenster
Finanzservices durch Firmen- und Privatkunden. The Autovermietung Hertz ist
ebenfalls Bestandteil der FMC. Nach der Gründung im Jahr 1903 fand Fords IPO im
Jahr 1956 statt.
Im Jahr 2006 fuhr Ford den größten Jahresverlust ($12.6 Mrd) in der
Firmengeschichte ein. Trotz eines Gewinns in der Höhe von $750 Millionen im
zweiten Quartal 2007 schloss die FMC auch das Geschäftsjahr 2007 mit einem
negativen Ergebnis ab ($2.7 Mrd). Dieser Verlust ist allerdings zum Großteil den
notwendigen Umstrukturierungen bei Volvo zuzuschreiben. Um die Betriebskosten
zu reduzieren und die Profitabilität des Unternehmens in Nordamerika zu erhöhen,
entwickelte die FMC eine langfristige Strategie, die neben einigen weiteren
Veränderungen die Schließung von 16 Standorten in den USA (bis zum Jahr 2012)
und die Reduzierung der Betriebskosten um jährlich $5 Mrd. bis 2008 umfasst.
Weiters werden Verkaufssteigerungen der neueren, bereits am Markt befindlichen
Modelle (US: Ford Expedition, Edge, Lincoln Navigator, Lincoln; Europa: Ford S-MAX,
Transit, Galaxy) anvisiert. Zusätzlich werden starke Wachstumsmärkte (Indien,
China) in Zukunft stärker in den Fokus der FMC rücken.
MARKTPROFIL. Ford hat weiterhin, sowohl am US-Heimmarkt als auch auf den
Überseemärkten, mit harter Konkurrenz zu kämpfen. Bis inklusive des 3. Quartals
2007 musste die FMC Marktanteilsverluste in den USA hinnehmen, hauptsächlich
aufgrund von Einbrüchen im Flottenvertrieb. Hinzu kommt, dass vor allem
japanische Unternehmen wie Toyota, Honda oder Nissan in zunehmendem Maße
auch den US Markt bearbeiten und in der Lage sind, Marktanteile zu gewinnen. Die
hohen Zugewinne dieser Konkurrenten beruhen u.A. darauf, dass
kraftstoffsparendere Autos nun auch in den USA gefragt sind und Ford ebenso wie
z.B. GM bis jetzt diesen Wünschen nur unzureichend nachgekommen ist. Weitere
Risikobereiche für Ford sind steigende Rohstoffpreise, härterer Preiswettbewerb
und Wechselkursschwankungen.

Write a company overview like this in English for {TICKER}.
Include: main business segments, key markets, recent strategic initiatives, and competitive positioning.
Keep the length similar to the original example.
Do not add any extra commentary or meta-instructions.
Do not use headers just flow text.
"""
overview_text = query_gemini(overview_prompt)
tex_print(latex_escape(overview_text).replace('\n', '\\\\'))
tex_print(r"\vspace{0.5cm}")

formatted_address = format_address(overview['Address'])
tex_print(r"\begin{description}")
tex_print(r"    \item[Address:] " + formatted_address)
tex_print(r"    \item[Website:] \url{" + overview['OfficialSite'] + "}")
tex_print(r"    \item[Exchange:] " + overview['Exchange'])
tex_print(r"    \item[Dividend Date:] " + str(overview['DividendDate']))
tex_print(r"\end{description}")
tex_print(r"\newpage")

# ------------------- Net Income (horizontal bar chart) -------------------
start_date = '2015-01-01'
filtered = earnings[earnings['fiscalDateEnding'] >= start_date].copy()
fig, ax = plt.subplots(figsize=(10, 6))
filtered = filtered.sort_values('netIncome')
ax.barh(filtered['fiscalDateEnding'].dt.year, filtered['netIncome'] / 1e9, color='#0000FF')
ax.set_xlabel('Net Income ($ Billions)')
ax.set_title(f'{company_name} – Net Income by Year', fontsize=24, fontweight='bold')
plt.tight_layout()
netincome_pdf = f"{TICKER.lower()}_netincome.pdf"
plt.savefig(netincome_pdf, bbox_inches='tight')
plt.close()

tex_print(r"\noindent")
tex_print(r"\begin{minipage}{0.45\linewidth}")
tex_print(r"\centering")
tex_print(f"\\includegraphics[width=\\linewidth]{{{netincome_pdf}}}")
tex_print(r"\end{minipage}")
tex_print(r"\hfill")
tex_print(r"\begin{minipage}{0.53\linewidth}")

tex_print(r"\subsubsection*{Key Figures}")
kz = (LatexTable(key_figures(fundamental_stock, n=4).to_latex(float_format="%.2f"))
      .remove_separators()
      .set_small_font(size=r'\small')
      .bold_headers()
      .fit_to_width())
tex_print(kz)

tex_print(r"\vspace{0.2cm}")
tex_print(r"\subsubsection*{Key Growth Rates}")
kz2 = (LatexTable(key_growth_rates(fundamental_stock).rename(columns={'PE_Ratio':'PE ratio'}).to_latex(float_format="%.2f"))
       .remove_separators()
       .set_small_font(size=r'\small')
       .bold_headers()
       .fit_to_width())
tex_print(kz2)
tex_print(r"\end{minipage}")
tex_print(r"\vspace{0.5cm}")

# ------------------- Financial Figures -------------------
tex_print(r"\section*{Financial Figures}")
tex_print(r"\subsubsection*{Per share values}")
ps = (LatexTable(per_share_values(fundamental_stock).to_latex(float_format="%.02f"))
      .remove_separators()
      .set_small_font()
      .bold_headers()
      .set_equal_column_widths(align="r", stretch_first=True))
tex_print(ps)

tex_print(r"\subsubsection*{Income statement overview (USD)}")
inc = (LatexTable(income_statement_overview(fundamental_stock).to_latex(header=False, float_format="%.f"))
       .remove_separators()
       .set_small_font()
       .set_equal_column_widths(align="r", stretch_first=True))
tex_print(inc)

tex_print(r"\subsubsection*{Balance sheet overview (USD)}")
bal = (LatexTable(balance_sheet_overview(fundamental_stock).to_latex(header=False, float_format="%.f"))
       .remove_separators()
       .set_small_font()
       .set_equal_column_widths(align="r", stretch_first=True))
tex_print(bal)

tex_print(r"\subsubsection*{Cashflow overview (USD}")
cf = (LatexTable(cashflow_overview(fundamental_stock).to_latex(header=False, float_format="%.f"))
      .remove_separators()
      .set_small_font()
      .set_equal_column_widths(align="r", stretch_first=True))
tex_print(cf)
tex_print(r"\newpage")

# ------------------- Industry Outlook & SWOT (two columns) -------------------
tex_print(r"\noindent")
tex_print(r"\begin{minipage}[t]{0.48\textwidth}")
tex_print(r"\section*{Industry Outlook}")
industry_prompt = f"""
Die Ford Motor Company (FMC) ist ein global tätiges Unternehmen, mit den
Kerngeschäftsbereichen Automobile und Finanzdienstleistungen. Das
Automobilsegment beinhaltet folgende Kernaufgaben: Design, Entwicklung,
Herstellung, Verkauf und Service von PKWs, LKWs und Ersatzteilen. Die Ford Motor
Credit Company stellt ein ganzes Portfolio von Finanzdienstleistungen zur
Verfügung, konzentriert sich dabei jedoch hauptsächlich auf Finanzierung, Leasing
und Versicherung von Kraftfahrzeugen.
Ford ist der zweitgrößte Automobil- und Lastkraftwagenhersteller der Welt mit den
Hauptmarken Aston Martin, Ford, Jaguar, Land Rover, Lincoln, Mercury und Volvo.
Außerdem ist Ford mit 34% der Mehrheitseigentümer von Mazda. Ungefähr 80% des
Konzernumsatzes generiert Ford aus dem Verkauf von Automobilen, 2/3 davon in
Nordamerika. Die restlichen 20% werden mit den Finanzdienstleistungen der Ford
Motor Credit Company erzielt, hauptsächlich durch die Finanzierung der Ford
Vertragshändler aber auch durch die Inanspruchnahme verschiedenster
Finanzservices durch Firmen- und Privatkunden. The Autovermietung Hertz ist
ebenfalls Bestandteil der FMC. Nach der Gründung im Jahr 1903 fand Fords IPO im
Jahr 1956 statt.
Im Jahr 2006 fuhr Ford den größten Jahresverlust ($12.6 Mrd) in der
Firmengeschichte ein. Trotz eines Gewinns in der Höhe von $750 Millionen im
zweiten Quartal 2007 schloss die FMC auch das Geschäftsjahr 2007 mit einem
negativen Ergebnis ab ($2.7 Mrd). Dieser Verlust ist allerdings zum Großteil den
notwendigen Umstrukturierungen bei Volvo zuzuschreiben. Um die Betriebskosten
zu reduzieren und die Profitabilität des Unternehmens in Nordamerika zu erhöhen,
entwickelte die FMC eine langfristige Strategie, die neben einigen weiteren
Veränderungen die Schließung von 16 Standorten in den USA (bis zum Jahr 2012)
und die Reduzierung der Betriebskosten um jährlich $5 Mrd. bis 2008 umfasst.
Weiters werden Verkaufssteigerungen der neueren, bereits am Markt befindlichen
Modelle (US: Ford Expedition, Edge, Lincoln Navigator, Lincoln; Europa: Ford S-MAX,
Transit, Galaxy) anvisiert. Zusätzlich werden starke Wachstumsmärkte (Indien,
China) in Zukunft stärker in den Fokus der FMC rücken.
MARKTPROFIL. Ford hat weiterhin, sowohl am US-Heimmarkt als auch auf den
Überseemärkten, mit harter Konkurrenz zu kämpfen. Bis inklusive des 3. Quartals
2007 musste die FMC Marktanteilsverluste in den USA hinnehmen, hauptsächlich
aufgrund von Einbrüchen im Flottenvertrieb. Hinzu kommt, dass vor allem
japanische Unternehmen wie Toyota, Honda oder Nissan in zunehmendem Maße
auch den US Markt bearbeiten und in der Lage sind, Marktanteile zu gewinnen. Die
hohen Zugewinne dieser Konkurrenten beruhen u.A. darauf, dass
kraftstoffsparendere Autos nun auch in den USA gefragt sind und Ford ebenso wie
z.B. GM bis jetzt diesen Wünschen nur unzureichend nachgekommen ist. Weitere
Risikobereiche für Ford sind steigende Rohstoffpreise, härterer Preiswettbewerb
und Wechselkursschwankungen.

Write a brief industry outlook for the sector for {TICKER} and in english.
Highlight current trends, challenges, and opportunities. Keep the length similar to the original example.
Keep it around 300 words.
Do not add any extra commentary or meta-instructions. And do not add extra formatting escept for breaks.
"""
industry_text = query_gemini(industry_prompt)
tex_print(latex_escape(industry_text).replace('\n', '\\\\'))
tex_print(r"\end{minipage}")
tex_print(r"\hfill")
tex_print(r"\begin{minipage}[t]{0.48\textwidth}")
tex_print(r"\section*{SWOT Analysis}")
swot_prompt = f"""
Provide a SWOT analysis for {company_name} ({TICKER}) in the following format:
STRENGHTS. Ford ist einer der größten Autohersteller der
Welt und weist ein Portfolio mehrerer Marken auf. Fords R&D
Abteilung konzentriert Ressourcen derzeit auf die
Verbesserung von Performance und Sicherheit, der
Treibstoffeffizienz und der Kundenzufriedenheit.
WEAKNESSES. Obwohl namhafte Konkurrenten längst mit
umweltschonenden und treibstoffsparenden Autos auf dem
US-Markt sind, legte Ford auch in den vergangenen Jahren
sein Hauptaugenmerk vor allem auf SUVs. Durch die
Preissteigerungen bei Treibstoffen und Energie im
Allgemeinen könnte die Profitabilität dieses Marktes
allerdings noch weiter einbrechen.
OPPORTUNITIES. Präsenz in neuen Märkten: In Indien und
China rechnet sich Ford starke Wachstumschancen aus.
THREATS. Härtere Konkurrenten: Toyota, Honda und Nissan
konnten ihre US Marktanteile ausbauen. Weitere Risiken:
steigende Kosten für Rohmaterialien, stärkerer
Preiswettbewerb und ungünstige Wechselkursfluktuationen.

Write such a SWOT analysis for {TICKER} and in enlish.
Keep the length shorter then the original baout 100 words.
Do not add any extra commentary or meta-instructions
"""
swot_text = query_gemini(swot_prompt)
tex_print(latex_escape(swot_text).replace('\n', '\\\\'))
tex_print(r"\vspace{0.5cm}")

# ------------------- Stock Performance (normalized) -------------------
stock['normalized'] = (stock['close'] / stock['close'].iloc[0] * 100) - 100
spy['normalized'] = (spy['close'] / spy['close'].iloc[0] * 100) - 100
if not competitor_stock.empty:
    competitor_stock['normalized'] = (competitor_stock['close'] / competitor_stock['close'].iloc[0] * 100) - 100

fig, ax1 = plt.subplots()
ax1.plot(stock['fiscalDateEnding'], stock['normalized'], color='#0000FF', linewidth=1, label=TICKER)
ax1.plot(spy['fiscalDateEnding'], spy['normalized'], color='#ff7f0e', linewidth=1, label=BENCHMARK)
if not competitor_stock.empty and overview_data_list:
    ax1.plot(competitor_stock['fiscalDateEnding'], competitor_stock['normalized'], color='#2ca02c', linewidth=1, label=overview_data_list[0]['Symbol'])
ax1.set_ylabel('Relative Performance (%)', fontsize=11)
title = f'5 year performance: {TICKER} vs. {BENCHMARK}'
if not competitor_stock.empty and overview_data_list:
    title += f' vs. {overview_data_list[0]["Symbol"]}'
ax1.set_title(title, fontsize=14, fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.legend(loc='upper left')
fig.autofmt_xdate(rotation=45)
plt.tight_layout()
perf_pdf = f"{TICKER.lower()}_performance.pdf"
plt.savefig(perf_pdf, bbox_inches='tight')
plt.close()

tex_print(r"\section*{Stock Performance}")
tex_print(r"\centering")
tex_print(f"\\includegraphics[width=\\linewidth]{{{perf_pdf}}}")
tex_print(r"\end{minipage}")

# ------------------- Industry (competitor table) -------------------
def format_market_cap(value_str):
    try:
        val = float(value_str)
        return f"{val / 1e6:.0f}"
    except:
        return "n.v."

def format_number(value_str, decimals=2, missing="n.v."):
    try:
        if value_str in (None, "None", ""):
            return missing
        val = float(value_str)
        return f"{val:.{decimals}f}"
    except:
        return missing

headers = ["Stock", "Symbol", "Mkt.Cap. (Mil.$)", "Recent Stk. Price($)", "P/E Ratio", "Beta", "EPS ($)", "Dividend ($)"]
rows = []
for item in overview_data_list:
    stock_name = item.get('Name', item.get('Symbol', 'N/A'))
    symbol = item.get('Symbol', 'N/A')
    mkt_cap = format_market_cap(item.get('MarketCapitalization', 'n.v.'))
    recent_price = format_number(item.get('AnalystTargetPrice', 'n.v.'))
    pe_ratio = format_number(item.get('PERatio'), decimals=2)
    beta = format_number(item.get('Beta'), decimals=2)
    eps = format_number(item.get('EPS'), decimals=2)
    dividend = format_number(item.get('DividendPerShare'), decimals=2)
    rows.append([stock_name, symbol, mkt_cap, recent_price, pe_ratio, beta, eps, dividend])

tex_print(r"\section*{Industry}")
tex_print(r"\setlength{\LTleft}{0pt}")
tex_print(r"\setlength{\LTright}{0pt}")
tex_print(r"\begin{longtable}{@{\extracolsep{\fill}} l l r r r r r r @{}}")
tex_print(r"\toprule")
tex_print(" & ".join(headers) + r" \\")
tex_print(r"\midrule")
for row in rows:
    tex_print(" & ".join(row) + r" \\")
tex_print(r"\bottomrule")
tex_print(r"\end{longtable}")
tex_print(r"\newpage")

# ------------------- Company News -------------------
tex_print(r"\section*{Company News}")
tex_print(r"\begin{multicols}{2}")
latest_news = get_latest_news(TICKER, api_key=os.getenv("FINNHUB_API_KEY"), limit=7)
for i, news in enumerate(latest_news, 1):
    headline = latex_escape(news['headline'])
    date = latex_escape(news['date'])
    summary = latex_escape(news['summary'])
    tex_print(f"\\textbf{{{headline}}}\\\\")
    tex_print(r"\smallskip")
    tex_print(f"\\textit{{Date: {date}}}\\\\")
    tex_print(r"\smallskip")
    tex_print(f"{summary}\n")
    if i < len(latest_news):
        tex_print(r"\vspace{0.3cm}")
tex_print(r"\end{multicols}")

# ------------------- Disclosure -------------------
tex_print(r"\section*{Disclosure}")
tex_print(r"\begin{enumerate}")
tex_print(r"    \item The fundamental data and overview data is pulled from alphavantage, the stock data is from yfinance and the news is from finnhub.")
tex_print(r"    \item The buying decision is based on the DDM model, which takes an ARIMA(1,1,0) model on EPS and assumes the median payout rate of the last 5 years.\\ "
          r"            This is manually compared with company guidance. \\"
          r"            There are better methods to estimate a dividend guidance and a fair value, but given the project size this was the most reasonable.")
tex_print(r"    \item Such a report can be generated for any S\&P 500 company automatically under ")
tex_print(r"    \item All calculations and how the report is generated can be found here: \url{https://github.com/TiborB6/report}")
tex_print(r"\end{enumerate}")
tex_print(r"\end{document}")

# ------------------- Write and compile .tex -------------------
tex_filename = "report.tex"
with open(tex_filename, "w", encoding="utf-8") as f:
    f.write(''.join(tex_lines))

for i in range(2):
    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", tex_filename],
        capture_output=True,
        text=True
    )

if clean:
    cleanup()