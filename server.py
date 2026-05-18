from flask import Flask, send_file, render_template, request, redirect, url_for
import subprocess
import os

app = Flask(__name__)

@app.route('/')
def form():
    return render_template('home.html')

@app.route('/generate_report', methods=['POST'])
def generate_report():
    ticker = request.form.get('ticker')
    if not ticker:
        return "Missing ticker", 400
    
    result = subprocess.run(
        ["python", "generate_report.py", ticker],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return f"Report generation failed: {result.stderr}", 500
    
    report_path = "report.html"
    if not os.path.exists(report_path):
        return "Report file not found", 500
    return send_file(report_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
