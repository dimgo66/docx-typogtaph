#!/bin/bash
#
# @file: build-prince-a5.sh
# @description: Генерация PDF формата A5 из HTML через Prince for Books с использованием a5_core_styles.css
# @dependencies: Prince for Books, css/a5_core_styles.css, reports/pisk.semantic.full.typograf.print.html
# @created: 2024-07-06
# @modified: YYYY-MM-DD

set -e

# Параметры по умолчанию
INPUT="${1:-reports/pisk.semantic.full.typograf.print.html}"
OUTPUT="${2:-book-a5.pdf}"
CSS_FILE="css/a5_core_styles.css"

# Проверка наличия Prince for Books
PRINCE_PATH="/usr/local/prince-books/bin/prince-books"

if [ ! -f "$PRINCE_PATH" ]; then
    echo "Ошибка: Prince for Books не найден по пути $PRINCE_PATH" >&2
    echo "Пожалуйста, установите Prince for Books или укажите правильный путь в переменной PRINCE_PATH." >&2
    exit 1
fi

# Проверка наличия входного файла
if [ ! -f "$INPUT" ]; then
    echo "Ошибка: Входной HTML файл '$INPUT' не найден." >&2
    exit 1
fi

# Проверка наличия CSS файла
if [ ! -f "$CSS_FILE" ]; then
    echo "Ошибка: CSS файл '$CSS_FILE' не найден." >&2
    exit 1
fi

echo "Создаю PDF формата A5 из файла $INPUT с использованием стилей $CSS_FILE..."

# Команда для генерации PDF
"$PRINCE_PATH" "$INPUT" -s "$CSS_FILE" -o "$OUTPUT" --no-warn-css-unknown --no-warn-css-unsupported

echo "PDF успешно создан: $OUTPUT"

# Если macOS, открыть файл
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$OUTPUT"
fi 