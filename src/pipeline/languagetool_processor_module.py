import os
import sys
import json
import logging
import subprocess
from typing import Optional
import tempfile
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../tools')))
from check_text_languagetool import ensure_html_lang_ru

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
        # Гарантируем lang="ru" в <html>
        ensure_html_lang_ru(html_path)
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(html_path))[0]
        output_report_path = os.path.join(output_dir, f"{base_name}_languagetool_report.json")
        # --- Извлекаем plain text из HTML ---
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.body.get_text(separator='\n', strip=True) if soup.body else soup.get_text(separator='\n', strip=True)
        with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8', suffix='.txt') as tmp_txt:
            tmp_txt.write(text)
            tmp_txt_path = tmp_txt.name
        # --- Логируем содержимое временного .txt-файла (первые 10 строк) ---
        try:
            with open(tmp_txt_path, 'r', encoding='utf-8') as f_txt:
                lines = f_txt.readlines()
                preview = ''.join(lines[:10])
                text_full = ''.join(lines)
                debug_info = (
                    f"\n===LANGTOOL_DEBUG===\n"
                    f"correlation_id: {self.correlation_id}\n"
                    f"tmp_txt_path: {tmp_txt_path}\n"
                    f"Кодировка: utf-8\n"
                    f"Длина текста (символов): {len(text_full)}\n"
                    f"Первые 10 строк:\n{preview}"
                    f"\n===END_LANGTOOL_DEBUG===\n"
                )
                print(debug_info, file=sys.stderr)
                print(debug_info)
                self.logger.info(f"[DEBUG] Содержимое временного .txt-файла для LT (первые 10 строк):\n{preview}")
                # Дублируем в отдельный лог-файл
                logs_dir = os.path.join('workspace', 'logs')
                os.makedirs(logs_dir, exist_ok=True)
                debug_log_path = os.path.join(logs_dir, 'langtool_debug.log')
                with open(debug_log_path, 'a', encoding='utf-8') as debug_log:
                    debug_log.write(debug_info)
        except Exception as e:
            self.logger.warning(f"Не удалось прочитать временный .txt-файл для логирования: {e}")
        # --- Запускаем LanguageTool на plain text ---
        command = [
            "java",
            "-Xmx4G",
            "-jar",
            "LanguageTool-6.6/languagetool-commandline.jar",
            "-l", "ru",
            "-c", "utf-8",
            "--json",
            tmp_txt_path
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
        finally:
            try:
                os.remove(tmp_txt_path)
            except Exception:
                pass
        # Сохраняем служебный SUCCESS.json
        success_path = os.path.join(output_dir, "LanguageToolProcessorModule_SUCCESS.json")
        with open(success_path, "w", encoding="utf-8") as f:
            json.dump({"output_report_path": output_report_path}, f, ensure_ascii=False, indent=2)
        return output_report_path 