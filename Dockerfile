FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y wget tar curl openjdk-17-jre-headless && \
    wget https://github.com/jgm/pandoc/releases/download/3.2/pandoc-3.2-1-amd64.deb && \
    apt-get install -y ./pandoc-3.2-1-amd64.deb && \
    rm pandoc-3.2-1-amd64.deb && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN npm install --omit=dev

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# --- Диагностика окружения ---
RUN echo '=== JAVA VERSION ===' && java -version || true
RUN echo '=== LOCALE ===' && locale || true
RUN echo '=== LANGUAGE TOOL VERSION ===' && java -jar LanguageTool-6.6/languagetool-commandline.jar --version || true
# Установка русской локали (если требуется)
RUN apt-get update && apt-get install -y locales && locale-gen ru_RU.UTF-8 && update-locale LANG=ru_RU.UTF-8
ENV LANG=ru_RU.UTF-8
# Тестовый запуск LanguageTool (можно закомментировать после диагностики)
RUN echo 'Артур Другой\nЭто тестовая строка.' > /tmp/test_ru.txt && java -jar LanguageTool-6.6/languagetool-commandline.jar -l ru -c utf-8 --json /tmp/test_ru.txt || true

CMD ["gunicorn", "webapp.app:app"] 