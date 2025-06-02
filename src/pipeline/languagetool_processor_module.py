import os
import sys
import json
import logging
import subprocess
from typing import Optional

class LanguageToolProcessorModule:
    """
    Модуль для запуска проверки HTML-файла с помощью LanguageTool и интеграции с ИИ.
    Вызывает tools/check_text_languagetool.py как подпроцесс.
    """
    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.logger = logging.getLogger(f"LanguageToolProcessorModule.{correlation_id}")

    def run(self, html_path: str, output_dir: str) -> Optional[str]:
        """
        Запускает проверку HTML-файла, возвращает путь к JSON-отчету или None.
        """
        if not os.path.exists(html_path):
            self.logger.error(f"HTML-файл не найден: {html_path}")
            return None
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(html_path))[0]
        output_report_path = os.path.join(output_dir, f"{base_name}_languagetool_report.json")
        command = [
            "java",
            "-Xmx4G",
            "-jar",
            "LanguageTool-6.6/languagetool-commandline.jar",
            "-l", "ru",
            "-c", "utf-8",
            "--json",
            html_path
        ]
        try:
            with open(output_report_path, "w", encoding="utf-8") as fout:
                proc = subprocess.Popen(command, stdout=fout, stderr=subprocess.PIPE)
                _, stderr = proc.communicate()
                if proc.returncode != 0:
                    self.logger.error(f"LanguageTool завершился с ошибкой: {stderr.decode('utf-8', errors='ignore')}")
                    return None
        except Exception as e:
            self.logger.error(f"Ошибка при запуске LanguageTool: {e}")
            return None
        # Сохраняем служебный SUCCESS.json
        success_path = os.path.join(output_dir, "LanguageToolProcessorModule_SUCCESS.json")
        with open(success_path, "w", encoding="utf-8") as f:
            json.dump({"output_report_path": output_report_path}, f, ensure_ascii=False, indent=2)
        return output_report_path 