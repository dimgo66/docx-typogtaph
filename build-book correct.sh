#!/bin/bash

# Запись в лог
log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a process.log
}

# Проверка наличия аргумента
if [ $# -lt 1 ]; then
  echo "Использование: $0 <путь_к_docx_файлу>"
  exit 1
fi

# Входной файл
INPUT_DOCX="$1"
FILENAME=$(basename "$INPUT_DOCX" .docx)
OUTPUT_DIR="reports"

log "Начало обработки файла $INPUT_DOCX"

# Шаг 1: Конвертация DOCX в HTML
log "Шаг 1: Конвертация DOCX в HTML"
CONVERTED_HTML=$(python3 tools/convert_docx_to_html.py "$INPUT_DOCX" --output_dir "$OUTPUT_DIR")
HTML_PATH="$OUTPUT_DIR/$FILENAME/$FILENAME.html"

if [ ! -f "$HTML_PATH" ]; then
  log "Ошибка: HTML файл не был создан"
  exit 1
fi

log "HTML файл создан: $HTML_PATH"

# Шаг 2: Проверка текста с помощью LanguageTool
log "Шаг 2: Проверка текста с помощью LanguageTool"
python3 tools/check_text_languagetool.py "$HTML_PATH" -o "$OUTPUT_DIR/$FILENAME"
LT_REPORT="$OUTPUT_DIR/$FILENAME/${FILENAME}_languagetool_report.json"

if [ ! -f "$LT_REPORT" ]; then
  log "Ошибка: Отчет LanguageTool не был создан"
  exit 1
fi

log "Отчет LanguageTool создан: $LT_REPORT"

# Шаг 3: Автоматическое исправление ошибок
log "Шаг 3: Автоматическое исправление ошибок на основе отчета LanguageTool"
python3 tools/autocorrect_html_languagetool.py "$HTML_PATH" "$LT_REPORT"
CORRECTED_HTML="$HTML_PATH"

if [ ! -f "$CORRECTED_HTML" ]; then
  log "Ошибка: Исправленный HTML не был создан"
  exit 1
fi

log "HTML файл исправлен"

# Шаг 4: Добавление табуляции перед каждым <p>
log "Шаг 4: Добавление табуляции перед каждым <p>"
TABBED_HTML="$OUTPUT_DIR/$FILENAME/${FILENAME}.tabbed.html"
python3 tools/tabulate_paragraphs.py "$CORRECTED_HTML" "$TABBED_HTML"

if [ ! -f "$TABBED_HTML" ]; then
  log "Ошибка: HTML с табуляцией не был создан"
  exit 1
fi

log "HTML с табуляцией создан: $TABBED_HTML"

# Шаг 5: Применение типографики к HTML
log "Шаг 5: Применение типографики к HTML"
TYPOGRAF_HTML="$OUTPUT_DIR/$FILENAME/${FILENAME}.typograf.html"
node tools/typografize.js "$TABBED_HTML" "$TYPOGRAF_HTML"

if [ ! -f "$TYPOGRAF_HTML" ]; then
  log "Ошибка: Типографицированный HTML файл не был создан"
  exit 1
fi

log "Типографицированный HTML файл создан: $TYPOGRAF_HTML"

# Шаг 6: Конвертация типографицированного HTML в Markdown
log "Шаг 6: Конвертация типографицированного HTML в Markdown"
TYPOGRAF_MD="$OUTPUT_DIR/$FILENAME/${FILENAME}.typograf.md"
pandoc -f html -t markdown "$TYPOGRAF_HTML" -o "$TYPOGRAF_MD"

if [ ! -f "$TYPOGRAF_MD" ]; then
  log "Ошибка: Markdown файл не был создан"
  exit 1
fi

log "Markdown файл создан: $TYPOGRAF_MD"

# Шаг 7: Конвертация Markdown обратно в HTML
log "Шаг 7: Конвертация Markdown обратно в HTML"
FINAL_HTML="$OUTPUT_DIR/$FILENAME/${FILENAME}_processed.html"
pandoc -f markdown -t html "$TYPOGRAF_MD" -o "$FINAL_HTML"

if [ ! -f "$FINAL_HTML" ]; then
  log "Ошибка: Финальный HTML файл не был создан"
  exit 1
fi

log "Финальный HTML файл создан: $FINAL_HTML"

# Завершение
log "Обработка файла $INPUT_DOCX завершена успешно"
echo "Результаты находятся в директории $OUTPUT_DIR/$FILENAME/"
echo "Исходный HTML: $HTML_PATH"
echo "Итоговый обработанный HTML: $FINAL_HTML"