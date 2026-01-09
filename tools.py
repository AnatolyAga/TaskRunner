import datetime, time
from collections import namedtuple
import random
import json

# Структура с типом namedtuple для возвращаемого кортежа
ScheduleResult = namedtuple('ScheduleResult', ['delay', 'start_time'])

# Получаем таск по его ID
def get_task(id_for_search: int, task_list: list):
    for task in task_list:
        if task.id == id_for_search:
            return task
    return None

# = Сохраняем в эксель =
def save_to_excel(data_frame, path_to_save, log_function=None):
    try:
        data_frame.to_excel(path_to_save, index=False)
        if log_function: log_function(f"Файл сохранен: {path_to_save}. Строк: {data_frame.shape[0]}, столбцов: {data_frame.shape[1]}", 0)

    except Exception as e_error:
        if log_function: log_function(f"Ошибка при сохранении: {e_error}", 1)
        return None


# === Настройки подключения к БД ===
# = Загружаем файл с настройками =
def load_config(filename="config.json", log_function=None):
    try:
        with open(filename, "r") as f:
            config = json.load(f)
        if log_function: log_function("Конфиг подключения загружен")
        return config
    except FileNotFoundError:
        if log_function: log_function("Файл c настройками не найден", 1)
        return None
    except Exception as e_error:
        if log_function: log_function(f"Ошибка при чтении файла: {e_error}", 1)
        return None

# = Сохраняем файл с настройками =
def save_config(db_config: dict, filename="config.json", log_function=None):
    try:
        with open(filename, "w") as f:
            # indent=4 делает файл читаемым (красивые отступы)
            # ensure_ascii=False позволяет сохранять кириллицу корректно
            json.dump(db_config, f, indent=4, ensure_ascii=False)
        if log_function: log_function(f"Настройки успешно сохранены в {filename}")
    except Exception as e_error:
        if log_function: log_function(f"Ошибка при сохранении: {e_error}", 1)

# = Проверяем, что настройки подключения к БД заполнены =
def check_db_config_fields(db_config: dict, log_function=None):
    if db_config is not None: # Если в db_config вообще присутствуют элементы
        missing_params = [k for k, v in db_config.items() if not v and k != "password"] # Получаем список незаполненных полей, кроме password
    else:
        if log_function: log_function(f"Настройки подключения к БД пустые.") # Иначе возвращаем ошибку
        return False
    if not missing_params: # Все заполнено
        return True
    else:
        if log_function: log_function(f"В настройках подключения к БД не заполнены данные: {', '.join(missing)}")
        return False

# === Экспорт\импорт тасков ===
# = Экспорт тасков в json =
def save_tasks_to_json(task_list, filename="tasks.json", log_function=None):
    # Превращаем список объектов в список словарей
    data_to_save = [task.to_dict() for task in task_list]
    # Пишем в файл json
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    if log_function: log_function(f"Сохранено задач: {len(data_to_save)}")

# = Импорт тасков в json =
def load_tasks_from_json(filename="tasks.json", log_function=None):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if log_function: log_function(f"Файл {filename} не найден.", 1)
    except Exception as e:
        if log_function: log_function(f"Ошибка при импорте: {e}", 1)
        return []


#Самое примитивное шифрование пароля встроенными способами
def xor_cipher(text, key="dfsdfgfhgewdfggfhgffhfg_gaawrdf99021dfsfsdghgjd"):
    # Повторяем ключ до длины text и применяем XOR
    return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(text))

# Получение задержки времени до выполнения таска
def get_delay(hour, minute, second=0, log_function=None):
    current_time = datetime.datetime.now()
    start_time = current_time.replace(hour=hour, minute=minute, second=second, microsecond=0)
    if start_time <= current_time: start_time += datetime.timedelta(days=1) # Если выполнение уже пропущено в текущем дне
    delay = (start_time - current_time).total_seconds() # Время до выполнения от текущего времени
    delay = int(delay * 1000) # Для root.after нужно в миллисекундах
    if log_function: log_function(f"Запланирован запуск на: {start_time}. Задержка до запуска {delay:.2f} сек.")
    return ScheduleResult(delay=delay, start_time=start_time) # Возвращаем в виде кортежа


#Генерируем случайное время запуска таска
def generate_random_task_start():
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"

#Генерируем случайное время для повтора
def generate_random_repeat():
    list_of_values = [0, 15, 30, 45]
    return random.choice(list_of_values)

