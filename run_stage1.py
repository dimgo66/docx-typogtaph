#!/usr/bin/env python3
"""
@file: run_stage1.py
@description: Этап 1 пайплайна: DOCX → HTML → типографика. На вход — DOCX, на выход — типографированный HTML.
@dependencies: src/pipeline/docx_to_html_converter.py, src/pipeline/typograf_processor_module.py
@created: 2024-07-31
"""
import sys
import os
import uuid
from src.pipeline.docx_to_html_converter import convert_docx_to_html
from src.pipeline.typograf_processor_module import TypografProcessorModule

def main():
    if len(sys.argv) != 3:
        print("Использование: python run_stage1.py input.docx output.html")
        sys.exit(1)
    input_docx = sys.argv[1]
    # Получаем базовое имя без расширения
    base = os.path.splitext(os.path.basename(input_docx))[0]
    output_html = os.path.join("workspace", "output", f"{base}.html")
    correlation_id = str(uuid.uuid4())
    temp_dir = os.path.join("workspace", "processing", correlation_id, "stage1")
    os.makedirs(temp_dir, exist_ok=True)

    # DOCX → HTML
    html_path = convert_docx_to_html(input_docx, output_html, temp_dir, correlation_id)
    if not html_path:
        print("Ошибка на этапе конвертации DOCX → HTML")
        sys.exit(2)

    # Типографика
    typograf = TypografProcessorModule(correlation_id)
    typograf_html_path = typograf.run(html_path, temp_dir)
    if not typograf_html_path:
        print("Ошибка на этапе типографики")
        sys.exit(3)

    # Копируем результат в output_html
    try:
        with open(typograf_html_path, "r", encoding="utf-8") as fin, open(output_html, "w", encoding="utf-8") as fout:
            fout.write(fin.read())
        print(f"Успех! Типографированный HTML сохранён в: {output_html}")
    except Exception as e:
        print(f"Ошибка при сохранении результата: {e}")
        sys.exit(4)

if __name__ == "__main__":
    main() 