from enum import Enum
from datetime import datetime

# === Счетчик для создания ID под объекты класса ===
# ID просто увеличиваются на единицу при инициализации экземпляра класса
class CounterId:
    counter = 0

# ==== Класс для статуса по таскам ====
class TaskStatus(Enum):
    OPEN = "В работе"
    COMPLETED = "Выполнен"
    CANCELED =  "Отменен"

# ==== Класс Таск ====
class Task:
    def __init__(self, title: str, run_time: datetime,  repeat: int, sql_to_exec: str = "", path_to_save: str = "", log_function=None): #log_function - логировать создание таска
        from tools import get_delay # Импортируем получение задержки до запуска
        CounterId.counter += 1 #Увеличиваем счетчик ID
        self.log_function = log_function # Включаем функцию логирования в класс
        self.id = CounterId.counter  # Присваиваем номер в ID
        self._status = TaskStatus.OPEN # Создаем внутреннею переменную для отслеживания смены класса
        run_time = get_delay(run_time.hour, run_time.minute) # Получаем задержку до запуска
        self.title = title
        self.sql_to_exec = sql_to_exec
        self.time_to_run = run_time.start_time # Время запуска
        self.updating_time_to_run = self.time_to_run # Обновляемое время запуска для таблицы
        self.repeat = repeat # Повторять таск каждые repeat минут
        self.delay = run_time.delay # Задержка до запуска
        self.path_to_save = path_to_save # Путь сохранения выгрузки
        self.status = TaskStatus.OPEN # Внешний статус
        self.ttk_after_id = None # Внутренний id для запуска в root.after
        log_function(f"Задача {self.id} создана. Задержка до запуска {self.delay/1000} сек.")

    @property
    def status(self): # Метод для чтения статуса
        return self._status


    # Отслеживание смены статуса
    @status.setter
    def status(self, new_value):
        if self._status != new_value:
            old_value = self._status
            self._status = new_value
            self.on_status_change(old_value, new_value) # Вызываем функцию, что статус изменен

    # При смене статуса
    def on_status_change(self, old_val, new_val):
        old_delay = self.delay # Старое значение задержки
        self.delay = None
        message = f"Статус задачи {self.id} изменен на '{new_val.value}'"
        if self.log_function:
            self.log_function(message)

    # Превращаем объект в словарь (для экспорта)
    def to_dict(self):
        return {
            "title": self.title,
            "run_time": self.time_to_run.strftime("%H:%M"),  # datetime -> строка "2026-01-09T..."
            "repeat": self.repeat,
            "sql_to_exec": self.sql_to_exec,
            "path_to_save": self.path_to_save
        }

