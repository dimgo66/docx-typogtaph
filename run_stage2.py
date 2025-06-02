#!/usr/bin/env python3
"""
@file: run_stage2.py
@description: Этап 2 пайплайна: HTML → LanguageTool → автокоррекция → DOCX. На вход — HTML, на выход — финальный DOCX.
@dependencies: src/pipeline/languagetool_processor_module.py, src/pipeline/autocorrect_processor_module.py, src/pipeline/html_to_docx_processor_module.py
@created: 2024-07-31
"""
import sys
import os
import uuid
from src.pipeline.languagetool_processor_module import LanguageToolProcessorModule
from src.pipeline.autocorrect_processor_module import AutocorrectProcessorModule
from src.pipeline.html_to_docx_processor_module import HtmlToDocxProcessorModule

def main():
    if len(sys.argv) != 3:
        print("Использование: python run_stage2.py input.html output.docx")
        sys.exit(1)
    input_html = sys.argv[1]
    output_docx = sys.argv[2]
    # Получаем базовое имя исходного DOCX (ожидается, что input_html = workspace/output/<basename>.html)
    base = os.path.splitext(os.path.basename(input_html))[0]
    output_html_dir = os.path.dirname(input_html)
    correct_html_path = os.path.join(output_html_dir, f"{base}_correct.html")
    final_docx_path = os.path.join(output_html_dir, f"{base}_final.docx")
    correlation_id = str(uuid.uuid4())
    temp_dir = os.path.join("workspace", "processing", correlation_id)
    os.makedirs(temp_dir, exist_ok=True)
    print(f"[DEBUG] Рабочая директория: {os.getcwd()}")
    print(f"[DEBUG] Входной HTML: {input_html}")
    print(f"[DEBUG] Выходной DOCX: {final_docx_path}")
    print(f"[DEBUG] Временная папка: {temp_dir}")
    print(f"[DEBUG] Содержимое {output_html_dir}: {os.listdir(output_html_dir) if os.path.exists(output_html_dir) else 'нет папки'}")
    print(f"[DEBUG] Содержимое workspace/processing: {os.listdir('workspace/processing') if os.path.exists('workspace/processing') else 'нет папки'}")
    # Этап 1: LanguageTool
    try:
        print("[DEBUG] Перед запуском LanguageToolProcessorModule")
        lt = LanguageToolProcessorModule(correlation_id)
        json_report_path = lt.run(input_html, temp_dir)
        print("[DEBUG] После запуска LanguageToolProcessorModule")
        print(f"[DEBUG] JSON-отчёт LanguageTool: {json_report_path}")
        if not json_report_path or not os.path.exists(json_report_path):
            print("[ERROR] Не удалось получить JSON-отчёт LanguageTool")
            sys.exit(2)
    except Exception as e:
        print(f"[ERROR] Ошибка на этапе LanguageTool: {e}")
        sys.exit(2)
    # Этап 2: автокоррекция
    try:
        autocorr = AutocorrectProcessorModule(correlation_id)
        corrected_html_path = autocorr.run(input_html, json_report_path, temp_dir)
        print(f"[DEBUG] Исправленный HTML: {corrected_html_path}")
        if not corrected_html_path or not os.path.exists(corrected_html_path):
            print("[ERROR] Не удалось получить исправленный HTML")
            sys.exit(3)
        # Сохраняем финальный HTML с именем <basename>_correct.html
        with open(corrected_html_path, "r", encoding="utf-8") as fin, open(correct_html_path, "w", encoding="utf-8") as fout:
            fout.write(fin.read())
        print(f"[OK] Финальный HTML сохранён: {correct_html_path}")
    except Exception as e:
        print(f"[ERROR] Ошибка на этапе автокоррекции: {e}")
        sys.exit(3)
    # Этап 3: HTML → DOCX
    try:
        html2docx = HtmlToDocxProcessorModule(correlation_id)
        docx_path = html2docx.run(correct_html_path, temp_dir)
        print(f"[DEBUG] Финальный DOCX: {docx_path}")
        if not docx_path or not os.path.exists(docx_path):
            print("[ERROR] Не удалось получить финальный DOCX")
            sys.exit(4)
        # Копируем результат в <basename>_final.docx
        with open(docx_path, "rb") as fin, open(final_docx_path, "wb") as fout:
            fout.write(fin.read())
        print(f"[OK] Финальный DOCX сохранён: {final_docx_path}")
    except Exception as e:
        print(f"[ERROR] Ошибка на этапе конвертации в DOCX: {e}")
        sys.exit(4)

if __name__ == "__main__":
    main() 