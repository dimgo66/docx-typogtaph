FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y wget tar && \
    wget https://github.com/jgm/pandoc/releases/download/3.2/pandoc-3.2-1-amd64.deb && \
    apt-get install -y ./pandoc-3.2-1-amd64.deb && \
    rm pandoc-3.2-1-amd64.deb && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["gunicorn", "webapp.app:app"] 