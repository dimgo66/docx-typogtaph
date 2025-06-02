#!/bin/bash
#
# @file: build-prince.sh
# @description: Генерация PDF из HTML через Prince for Books с нужными параметрами печати и стилем literata-book.css
# @dependencies: Prince for Books, css/literata-book.css
# @created: 2024-06-08
# @updated: 2024-07-06

set -e

INPUT="${1:-index.html}"
OUTPUT="${2:-princ.pdf}"

/usr/local/prince-books/bin/prince-books "$INPUT" -o "$OUTPUT" --no-warn-css-unknown --style="css/literata-book.css"
echo "PDF успешно создан: $OUTPUT" 