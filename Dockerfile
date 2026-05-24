FROM python:3.12-slim

# Install pdflatex and required fonts
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        texlive-latex-base \
        texlive-fonts-recommended \
        texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8080
CMD ["python", "server.py"]