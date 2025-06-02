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
CONVERTED_HTML=$(./.venv/bin/python3 tools/convert_docx_to_html.py "$INPUT_DOCX" --output_dir "$OUTPUT_DIR")
HTML_PATH="$OUTPUT_DIR/$FILENAME/$FILENAME.html"

if [ ! -f "$HTML_PATH" ]; then
  log "Ошибка: HTML файл не был создан"
  exit 1
fi

log "HTML файл создан: $HTML_PATH"

# Шаг 2: Проверка текста с помощью LanguageTool
log "Шаг 2: Проверка текста с помощью LanguageTool"
./.venv/bin/python3 tools/check_text_languagetool.py "$HTML_PATH" -o "$OUTPUT_DIR/$FILENAME"
LT_REPORT="$OUTPUT_DIR/$FILENAME/${FILENAME}_languagetool_report.json"

if [ ! -f "$LT_REPORT" ]; then
  log "Ошибка: Отчет LanguageTool не был создан"
  exit 1
fi

log "Отчет LanguageTool создан: $LT_REPORT"

# Шаг 3: Автоматическое исправление ошибок
log "Шаг 3: Автоматическое исправление ошибок на основе отчета LanguageTool"
./.venv/bin/python3 tools/autocorrect_html_languagetool.py "$HTML_PATH" "$LT_REPORT"
CORRECTED_HTML="$HTML_PATH"

if [ ! -f "$CORRECTED_HTML" ]; then
  log "Ошибка: Исправленный HTML не был создан"
  exit 1
fi

log "HTML файл исправлен"

# Шаг 4: Добавление табуляции перед каждым <p>
log "Шаг 4: Добавление табуляции перед каждым <p>"
TABBED_HTML="$OUTPUT_DIR/$FILENAME/${FILENAME}.tabbed.html"
./.venv/bin/python3 tools/tabulate_paragraphs.py "$CORRECTED_HTML" "$TABBED_HTML"

if [ ! -f "$TABBED_HTML" ]; then
  log "Ошибка: HTML с табуляцией не был создан"
  exit 1
fi

log "HTML с табуляцией создан: $TABBED_HTML"

# Шаг 5: Применение типографики к HTML
log "Шаг 5: Применение типографики к HTML"
TYPOGRAF_HTML="$OUTPUT_DIR/$FILENAME/${FILENAME}.typograf.html"
node tools/typografize.js "$CORRECTED_HTML" "$TYPOGRAF_HTML"

if [ ! -f "$TYPOGRAF_HTML" ]; then
  log "Ошибка: Типографицированный HTML файл не был создан"
  exit 1
fi

log "Типографицированный HTML файл создан: $TYPOGRAF_HTML"

# Шаг 5.5: Добавление 8 пробелов в начало каждого абзаца в типографицированном HTML
log "Шаг 5.5: Добавление 8 пробелов в начало каждого <p> в $TYPOGRAF_HTML"
SPACED_TYPOGRAF_HTML="$OUTPUT_DIR/$FILENAME/${FILENAME}.spaced_typograf.html"
./.venv/bin/python3 tools/add_spaces_to_paragraphs.py "$TYPOGRAF_HTML" "$SPACED_TYPOGRAF_HTML"

if [ ! -f "$SPACED_TYPOGRAF_HTML" ]; then
  log "Ошибка: HTML с 8 пробелами ($SPACED_TYPOGRAF_HTML) не был создан"
  exit 1
fi
log "HTML с 8 пробелами создан: $SPACED_TYPOGRAF_HTML"

# Шаг 6: Конвертация типографицированного HTML (с пробелами) в Markdown
# Важно: этот Markdown, вероятно, будет содержать &nbsp; как есть.
# Для DOCX мы используем SPACED_TYPOGRAF_HTML напрямую.
log "Шаг 6: Конвертация типографицированного HTML (уже с пробелами) в Markdown"
TYPOGRAF_MD="$OUTPUT_DIR/$FILENAME/${FILENAME}.typograf.md"
pandoc -f html -t markdown "$SPACED_TYPOGRAF_HTML" -o "$TYPOGRAF_MD"

if [ ! -f "$TYPOGRAF_MD" ]; then
  log "Ошибка: Markdown файл не был создан"
  exit 1
fi

log "Markdown файл создан: $TYPOGRAF_MD"

# Шаг 7: Конвертация Markdown обратно в HTML
log "Шаг 7: Конвертация Markdown обратно в HTML"
PROCESSED_HTML="$OUTPUT_DIR/$FILENAME/${FILENAME}_processed.html"
pandoc -f markdown -t html "$TYPOGRAF_MD" -o "$PROCESSED_HTML" --metadata title="-" # Добавляем пустой заголовок, чтобы избежать предупреждения

if [ ! -f "$PROCESSED_HTML" ]; then
  log "Ошибка: Финальный HTML файл не был создан"
  exit 1
fi

log "Финальный HTML файл создан: $PROCESSED_HTML"

# Шаг 8: Конвертация HTML (после типографики и с 8 пробелами) в DOCX
log "Шаг 8: Конвертация HTML (после типографики, с 8 пробелами) в DOCX"
FINAL_DOCX="$OUTPUT_DIR/$FILENAME/${FILENAME}_final.docx"

# Убираем использование --reference-doc, DOCX будет со стилями pandoc по умолчанию + 8 пробелов
pandoc -s "$SPACED_TYPOGRAF_HTML" -o "$FINAL_DOCX"
log "Финальный DOCX файл создан на основе $SPACED_TYPOGRAF_HTML со стилями pandoc по умолчанию (отступы через 8 пробелов): $FINAL_DOCX"

if [ ! -f "$FINAL_DOCX" ]; then
  log "Ошибка: Финальный DOCX файл не был создан"
  exit 1
fi

log "Обработка файла $INPUT_DOCX завершена успешно"
log "Результаты находятся в директории $OUTPUT_DIR/$FILENAME/"
log "Исходный HTML: $HTML_PATH"
log "Итоговый обработанный HTML: $PROCESSED_HTML"
log "Итоговый DOCX: $FINAL_DOCX"

# Удаление всех промежуточных файлов, кроме итогового DOCX
# find "$OUTPUT_DIR/$FILENAME" \
#  ! -name "${FILENAME}_final.docx" \
#  ! -type d \
#  -exec rm -f {} +

end_time=$(date +%s)
execution_time=$((end_time - start_time))
log "Время выполнения скрипта: ${execution_time} секунд."