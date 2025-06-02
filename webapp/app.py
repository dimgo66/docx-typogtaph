"""
@file: app.py
@description: Веб-интерфейс на Flask для загрузки doc/docx, обработки через build-book.sh и скачивания результата. Реализована очередь обработки файлов и отслеживание статусов.
@dependencies: Flask, Python 3, build-book.sh
@created: 2024-07-05
@updated: 2024-07-07
"""

import os
import tempfile
import subprocess
import json
import threading
import queue
import time
from datetime import datetime
from flask import Flask, request, render_template, send_from_directory, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import shutil
import logging

logging.basicConfig(level=logging.INFO)

ALLOWED_EXTENSIONS = {'doc', 'docx'}
# Используем директории внутри webapp для удобства
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
RESULT_FOLDER = os.path.join(BASE_DIR, 'results')
FILE_REGISTRY = os.path.join(BASE_DIR, 'file_registry.json')

# Создаем папки, если они не существуют
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.secret_key = 'supersecretkey'  # Для flash-сообщений

# Очередь для обработки файлов
processing_queue = queue.Queue()

def load_file_registry():
    """Загружает статусы файлов из JSON."""
    if not os.path.exists(FILE_REGISTRY):
        return {}
    try:
        with open(FILE_REGISTRY, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {} # Возвращаем пустой словарь, если файл пуст или некорректен

def save_file_registry(registry):
    """Сохраняет статусы файлов в JSON."""
    with open(FILE_REGISTRY, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

def update_file_status(filename, status, result_filename=None, error_message=None):
    logging.info(f"update_file_status: {filename} -> {status}")
    registry = load_file_registry()
    if filename not in registry:
        registry[filename] = {}
    registry[filename]['status'] = status
    registry[filename]['updated_at'] = datetime.now().isoformat()
    if result_filename:
        registry[filename]['result'] = result_filename
    if error_message:
        registry[filename]['error'] = error_message
    save_file_registry(registry)

def process_file_worker():
    """Воркер, который обрабатывает файлы из очереди."""
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
    TEXTINPUT_DIR = os.path.join(PROJECT_ROOT, 'textinput')
    WORKSPACE_OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'workspace', 'output')
    os.makedirs(TEXTINPUT_DIR, exist_ok=True)
    os.makedirs(WORKSPACE_OUTPUT_DIR, exist_ok=True)

    while True:
        try:
            original_filename, upload_path = processing_queue.get(timeout=1)
            logging.info(f"Взята задача из очереди: {original_filename}")
            update_file_status(original_filename, "обрабатывается")

            # Копируем файл в textinput для пайплайна
            textinput_path = os.path.join(TEXTINPUT_DIR, original_filename)
            logging.info(f"Копируем файл в textinput: {textinput_path}")
            shutil.copy2(upload_path, textinput_path)

            # Запускаем orchestrator.py через subprocess (теперь как модуль)
            try:
                logging.info(f"Запуск пайплайна для: {original_filename}")
                result = subprocess.run([
                    'python3', '-m', 'src.pipeline.orchestrator', original_filename
                ], check=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
                logging.info(f"Пайплайн завершён для: {original_filename}")
            except subprocess.CalledProcessError as e:
                error_output = e.stderr or e.stdout or "Неизвестная ошибка при обработке."
                logging.error(f"Ошибка пайплайна: {error_output.strip()}")
                update_file_status(original_filename, "ошибка", error_message=error_output.strip())
                processing_queue.task_done()
                continue
            except Exception as e:
                logging.error(f"Исключение при запуске пайплайна: {e}")
                update_file_status(original_filename, "ошибка", error_message=str(e))
                processing_queue.task_done()
                continue

            # Копируем итоговый DOCX из workspace/output в results
            docx_basename = os.path.splitext(original_filename)[0] + '_final.docx'
            docx_path = os.path.join(WORKSPACE_OUTPUT_DIR, docx_basename)
            result_docx_name = docx_basename  # теперь имя совпадает с output
            result_docx_path = os.path.join(app.config['RESULT_FOLDER'], result_docx_name)
            if os.path.exists(docx_path):
                logging.info(f"Результат найден: {docx_path}")
                shutil.copy2(docx_path, result_docx_path)
                update_file_status(original_filename, "готов", result_filename=result_docx_name)
            else:
                logging.error(f"DOCX-файл не найден: {docx_path}")
                update_file_status(original_filename, "ошибка", error_message="DOCX-файл не найден после обработки пайплайном.")
            processing_queue.task_done()
        except queue.Empty:
            time.sleep(1)
        except Exception as e:
            logging.error(f"Ошибка в воркере: {e}")
            time.sleep(5)

# Запуск потока-воркера
worker_thread = threading.Thread(target=process_file_worker, daemon=True)
worker_thread.start()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file_route(): # Переименовал, чтобы избежать конфликта имен
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Файл не выбран')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Файл не выбран')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            
            # Проверка, не обрабатывается ли уже такой файл (по имени)
            registry = load_file_registry()
            if original_filename in registry and registry[original_filename].get('status') in ['в очереди', 'обрабатывается']:
                flash(f'Файл {original_filename} уже находится в обработке.')
                return redirect(request.url)

            file.save(upload_path)
            
            # Добавляем в реестр и очередь
            registry[original_filename] = {
                'status': "в очереди",
                'uploaded_at': datetime.now().isoformat(),
                'original_filename': original_filename,
                'result': None,
                'error': None
            }
            save_file_registry(registry)
            processing_queue.put((original_filename, upload_path))
            
            flash(f'Файл {original_filename} добавлен в очередь на обработку.')
            return redirect(request.url) # Остаемся на той же странице
        else:
            flash('Недопустимый формат файла')
            return redirect(request.url)
    
    # Для GET запроса передаем список файлов в шаблон
    files_status = load_file_registry()
    return render_template('upload.html', files_status=files_status)

@app.route('/status')
def get_status():
    """Возвращает статусы всех файлов в JSON."""
    registry = load_file_registry()
    return jsonify(registry)

@app.route('/download/<filename>')
def download_file(filename):
    """Позволяет скачать обработанный файл и автоматически удалить его после скачивания."""
    registry = load_file_registry()
    # Ищем по имени оригинального файла, чтобы найти имя результирующего файла
    file_to_download = None
    result_filename_to_serve = None
    original_filename_to_delete = None

    for original_fn, data in registry.items():
        if data.get('result') == filename: # Если имя файла в URL это имя результирующего файла
            file_to_download = data
            result_filename_to_serve = filename
            original_filename_to_delete = original_fn
            break
        elif original_fn == filename and data.get('status') == 'готов' and data.get('result'):
            file_to_download = data
            result_filename_to_serve = data['result']
            original_filename_to_delete = original_fn
            break

    if file_to_download and file_to_download.get('status') == 'готов' and result_filename_to_serve:
        response = send_from_directory(app.config['RESULT_FOLDER'], result_filename_to_serve, as_attachment=True)
        # После отправки файла — удаляем его из results и workspace/output, а также запись из реестра
        @response.call_on_close
        def cleanup_after_download():
            # Удаляем из results
            result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename_to_serve)
            if os.path.exists(result_path):
                try:
                    os.remove(result_path)
                except Exception as e:
                    print(f"Ошибка при удалении файла из results: {e}")
            # Удаляем из workspace/output
            PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
            WORKSPACE_OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'workspace', 'output')
            output_path = os.path.join(WORKSPACE_OUTPUT_DIR, result_filename_to_serve)
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception as e:
                    print(f"Ошибка при удалении файла из output: {e}")
            # Удаляем запись из file_registry.json
            if original_filename_to_delete and original_filename_to_delete in registry:
                del registry[original_filename_to_delete]
                save_file_registry(registry)
        return response
    else:
        flash(f'Файл {filename} не найден или еще не готов.')
        return redirect(url_for('upload_file_route'))


@app.route('/delete/<original_filename>')
def delete_file_route(original_filename): # Переименовал
    """Удаляет файл и его запись из реестра."""
    registry = load_file_registry()
    secured_original_filename = secure_filename(original_filename)

    if secured_original_filename in registry:
        file_data = registry[secured_original_filename]
        
        # Удаляем загруженный файл
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], secured_original_filename)
        if os.path.exists(upload_path):
            try:
                os.remove(upload_path)
            except OSError as e:
                flash(f'Ошибка при удалении загруженного файла {secured_original_filename}: {e}')
                # Продолжаем, чтобы удалить запись из реестра и результат
        
        # Удаляем результирующий файл, если он есть
        if file_data.get('result'):
            result_path = os.path.join(app.config['RESULT_FOLDER'], file_data['result'])
            if os.path.exists(result_path):
                try:
                    os.remove(result_path)
                except OSError as e:
                    flash(f'Ошибка при удалении результирующего файла {file_data["result"]}: {e}')
                    # Продолжаем, чтобы удалить запись из реестра

        # Удаляем запись из реестра
        del registry[secured_original_filename]
        save_file_registry(registry)
        flash(f'Файл {secured_original_filename} и его результаты удалены.')
    else:
        flash(f'Файл {secured_original_filename} не найден в реестре.')
    
    return redirect(url_for('upload_file_route'))

if __name__ == '__main__':
    # Важно: debug=True может вызывать запуск воркера дважды.
    # Для продакшена или стабильного тестирования лучше использовать debug=False
    # или запускать через production WSGI сервер (gunicorn, uwsgi).
    app.run(debug=False, host='0.0.0.0', port=5000) 