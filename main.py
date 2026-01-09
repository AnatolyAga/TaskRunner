import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog as fd
import os
from PIL import Image, ImageTk
from datetime import datetime, timedelta
from task_class import CounterId  # Импортируем CounterID
from task_class import TaskStatus # Импортируем класс TaskStatus
from task_class import Task # Импортируем класс Task
from tools import get_task, check_db_config_fields, save_config, load_config # Импортируем дополнительные функции

# === Задаем дефолтные переменные, настройки ===
db_config = {"host": "", "port": "", "dbname": "", "user": "", "password": ""} # Конфиг подключения к БД
task_list = [] # Пустой лист для тасков
# = Различные дефолтные значения =
TASK_DEFAULT_NAME = "Задача №"
TASK_START_TIME_MINUTES_ADD = int(2) # Кол-во минут, которые добавляются к текущему времени при создании нового таска


# ===== Основные методы =====

# === Создание таска ===
def create_task(check_db_pass = True, **kwargs): # check_db_pass - по умолчанию проверяем настройки БД и пароль
    # Извлекаем значения из kwargs
    task_title = kwargs.get('task_title')
    path_to_save = kwargs.get('path_to_save')
    task_time = kwargs.get('task_time')
    task_repeat = kwargs.get('task_repeat')
    task_sql = kwargs.get('task_sql')
    #Если проверка параметров БД и пароля включена - проверяем при создании таска
    if check_db_pass:
        # Проверяем, что есть настройки подключения к БД
        if not check_db_config():
            return
        # Проверяем, что пароль задан
        if not check_password():
            return
    # Добавляем таск в список тасков
    task_list.append(Task(task_title, task_time, task_repeat, task_sql, path_to_save, log_function=log_message))
    task = get_task(CounterId.counter, task_list) # Получаем id таска
    # Добавляем таск в очередь на запуск (ttk.after), также сохраняем его ID (из ttk.after) на случай если понадобится его удалить
    task.ttk_after_id = root.after(int(task.delay), run_task, task)
    refresh_table()  # Обновляем таблицу

# === Запуск таска ===
def run_task(task):
    log_message(f"Выполняется задача {task.id}")
    # Подключаемся к БД
    from db_connecting import connect_oss # Импортируем функцию подключения
    # Получаем датафрейм с данными
    df = connect_oss(log_function=log_message, **db_config, sql_exec=task.sql_to_exec)
    # Если датафрейм не пустой, сохраняем выгрузку. Если повторность по таску = 0, то меняем его статус
    if df is not None:
        from tools import save_to_excel
        save_to_excel(df, task.path_to_save, log_message) # Сохраняем выгрузку
        if task.repeat == 0:
            task.status = TaskStatus.COMPLETED
        else: # Если таск с повторностью
            from tools import get_delay
            new_time_to_run = datetime.now() + timedelta(minutes=int(task.repeat))  # Для повторного запуска добавляем время повтора к текущему времени
            new_time_to_run = get_delay(new_time_to_run.hour, new_time_to_run.minute, new_time_to_run.second) # Получаем время запуска и задержку
            task.delay = new_time_to_run.delay  # Обновляем задержку в таске
            task.updating_time_to_run = new_time_to_run.start_time # Обновляем время запуска используемое для таблицы
            task.ttk_after_id = root.after(int(task.delay), run_task, task) # Добавляем таск в запуск по расписанию
            log_message(f"Задача: {task.id} будет снова запущена {new_time_to_run.start_time}")
    refresh_table() # Обновляем таблицу


# = Проверка настроек БД =
def check_db_config():
    if not check_db_config_fields(db_config, log_function=log_message): # Проверяем заполненность полей в подключении к БД
        log_message("Требуется ввести данные для подключения...", 1)
        db_config_ref = show_connect_window() # Показываем окно настроек подключения
        root.wait_window(db_config_ref) # Ждем окно с настройками
        # После закрытия проверяем, все ли заполнено
        if not check_db_config_fields(db_config, log_function=log_message):
            log_message("Ввод данных для подключения отменен", 1)
            return False
    return True


# = Проверка наличия пароля =
def check_password():
    if db_config.get('password', "") == "": # Пароль не задан
        log_message("Требуется пароль для подключения...", 1)
        password_window_ref = show_password_window() # Показываем окно ввода пароля
        root.wait_window(password_window_ref) # Ждем окно пароля
        # После закрытия проверяем, появился ли пароль
        if db_config.get('password', "") == "": # Пароль опять не задан
            log_message("Ввод пароля отменен", 1)
            return False
    return True


# ====== Интерфейс =====
# === Окна с настройками и прочие окна ===

# = Окно выбора файла для сохранения =
def pickup_file_save(initialfile: str = "result.xlsx", defaultextension: str = ".xlsx", filetypes: list = [("Excel файлы", "*.xlsx")]):
    file_to_save = fd.asksaveasfilename(
    title="Сохранить как...",
    initialfile=initialfile,                # Имя файла
    defaultextension=defaultextension,      # Расширение
    filetypes=filetypes # Убираем "Все файлы (*.*)", чтобы оставить только один тип (из параметра по умолчанию [("Excel файлы", "*.xlsx")])
    )
    if file_to_save:
        return file_to_save
    return None

# = Окно выбора файла для открытия =
def pickup_file_open(filetypes: list = [("Excel файлы", "*.xlsx")]):
    file_to_open = fd.askopenfilename(
        title="Открыть файл",
        filetypes=filetypes,            # Типы файлов
        initialdir="."  # Начинать поиск в текущей папке
    )
    if file_to_open:
        return file_to_open
    return None

# = Центровка дочернего окна по центру root =
def center_window(child_window, parent_window):
    # Обновляем окна, чтобы получить текущие размеры
    child_window.update_idletasks()
    parent_window.update_idletasks()

    # Ширина и высота дочернего окна
    width = child_window.winfo_width()
    height = child_window.winfo_height()

    # Координаты и размеры родительского окна
    parent_x = parent_window.winfo_x()
    parent_y = parent_window.winfo_y()
    parent_width = parent_window.winfo_width()
    parent_height = parent_window.winfo_height()

    # Вычисляем центр
    x = parent_x + (parent_width // 2) - (width // 2)
    y = parent_y + (parent_height // 2) - (height // 2)

    # Устанавливаем геометрию (позиция без изменения размера)
    child_window.geometry(f"+{x}+{y}")

# === Окно для подключения к БД ===
def show_connect_window():

    # Методы окна
    # == Заполняем поля ввода данными из конфига ==
    def fill_connect_window():
        entry_host.delete(0, tk.END)
        entry_host.insert(0, db_config.get("host", ""))

        entry_port.delete(0, tk.END)
        entry_port.insert(0, db_config.get("port", "5432"))

        entry_db.delete(0, tk.END)
        entry_db.insert(0, db_config.get("dbname", ""))

        entry_login.delete(0, tk.END)
        entry_login.insert(0, db_config.get("user", ""))


    # == Кнопка применить ==
    def button_apply_db_settings(entry_pass=None):
        global db_config
        db_config = {
            "host": entry_host.get(),
            "port": entry_port.get(),
            "dbname": entry_db.get(),
            "user": entry_login.get()
        }
        save_config(db_config) # Сохраняем конфиг
        connect_window.destroy()


    # = Создаем новое окно типа Toplevel (дочернее) =
    connect_window = tk.Toplevel(root)
    connect_window.title("Настройка подключения к БД")
    connect_window.resizable(False, False)  #Запрещаем изменение размера
    connect_window.geometry("400x100")

    # = Окно для ввода данных для подключения =
    # Добавляем через frame в grid, чтобы выровнять было попроще
    # Подписи и поля
    frame_host = ttk.Frame(connect_window)
    frame_host.pack(pady=10, padx=10, fill="x")  # Заполняем все окно
    frame_host.grid_columnconfigure(1, weight=1)  # Второй столбец растягивается на все окно
    label_host = ttk.Label(frame_host, text="Хост:")
    label_host.grid(row=0, column=0, padx=5, sticky="w")  # Подпись ХОСТА слева, столбец 0
    entry_host = ttk.Entry(frame_host)
    entry_host.grid(row=0, column=1, padx=5, sticky="EW")  # Строка ввода ХОСТА, столбец 1
    label_port = ttk.Label(frame_host, text="Порт:")
    label_port.grid(row=0, column=2, padx=5, sticky="w")  # Подпись ПОРТ слева, столбец 2
    entry_port = ttk.Entry(frame_host, width=6)  # Ввод ПОРТА, ширина = 6
    entry_port.grid(row=0, column=3, padx=5)  # Строка ввода ПОРТА, столбец 3
    label_db = ttk.Label(frame_host, text="База данных:")
    label_db.grid(row=1, column=0, padx=5, pady=5, sticky="w")  # Подпись БД слева, строка 1, столбец 0
    entry_db = ttk.Entry(frame_host, width=20)  # Ввод БД, ширина = 20
    entry_db.grid(row=1, column=1, padx=5, sticky="EW")  # Строка ввода БД, столбец 1
    label_login = ttk.Label(frame_host, text="Логин:")
    label_login.grid(row=2, column=0, padx=5, sticky="EW")  # Строка ввода ЛОГИНА, столбец 0
    entry_login = ttk.Entry(frame_host, width=20)  # Ввод ЛОГИНА, ширина = 20
    entry_login.grid(row=2, column=1, padx=5, sticky="EW")  # Строка ввода ЛОГИНА, столбец 1
    # Кнопка Применить
    close_button = ttk.Button(frame_host, text="Применить", command=button_apply_db_settings)
    close_button.grid(row=2, column=2, padx=5, columnspan=2, sticky="ew")

    center_window(connect_window, root) # Сдвигаем окно относительно root
    connect_window.focus()  # Фокус на окно
    connect_window.bind('<Return>', lambda event: [close_button.invoke(), "break"])  # По нажатию Enter запускается close_button, не надо прокликивать. Break - останавливает нажатие Enter в этом окне
    connect_window.grab_set()  # Запрещаем взаимодействовать с остальными окнами, пока открыто это

    if db_config is not None: fill_connect_window() # Если словарь с данными для подключения не пустой - заполняем поля ввода в окне
    return connect_window

# === Окно для ввода пароля ===
def show_password_window():

    # = Отправляем пароль =
    def button_update_password():
        global db_config
        db_config['password'] = entry_pass.get()
        password_window.destroy()


    # = Создаем новое дочернее окно =
    password_window = tk.Toplevel(root)
    password_window.title("Пароль")
    password_window.resizable(False, False)  # Разрешаем изменение размера

    password_window.geometry("200x100")  # Перемещаем новое окно

    password_window.columnconfigure(0, weight=1)  # Левые отступы
    password_window.columnconfigure(3, weight=1)  # Правые отступы
    ttk.Label(password_window, text=f"Пароль для {db_config['user']}:").grid(row=3, column=1, columnspan=2, pady=(10, 0))
    entry_pass = ttk.Entry(password_window, show="•", width=30)
    entry_pass.grid(row=4, column=1, columnspan=2, pady=(5, 10))
    entry_pass.focus_set() # Фокус на поле ввода пароля
    btn_submit = ttk.Button(password_window, text="Ввод", command=button_update_password)
    btn_submit.grid(row=5, column=0, columnspan=4, pady=(5, 15))
    center_window(password_window, root)  # Сдвигаем окно относительно root
    password_window.bind('<Return>', lambda event: [btn_submit.invoke(), "break"])  # По нажатию Enter запускается btn_submit, не надо прокликивать. Break - останавливает нажатие Enter в этом окне
    password_window.grab_set()  # Запрещаем взаимодействовать с остальными окнами, пока открыто это
    return password_window

# === Выбор таска двойным кликом ===
def on_table_double_click(event):
    # Определяем, на какой элемент нажали
    selected = table.focus()
    if not selected:
        return  # Если клик не по таску выходим
    task_id = int(selected)  # Выбранная строка
    show_task_window(task_id) # Показываем окно с выбранным таском


# === Окно информации по таску ===
def show_task_window(task_id=None): # task_id - если выбран таск
    global task_list

    # Кнопка добавить таск (внутри окна создания таска)
    def button_submit_task():
        task_title = entry_task_title.get()  # Название
        if len(task_title) == 0: # Если название таска отсутствует
            task_title = f"{TASK_DEFAULT_NAME} {(CounterId.counter + 1)}"
        # Путь сохранения файла
        current_file_input = entry_file_path.get()  # Полный путь из ентри для сохранения
        last_directory = os.path.dirname(current_file_input)  # Путь до последней папки (директории)
        if current_file_input and os.path.isdir(last_directory):  # Если путь до файла есть и последняя папка в пути существуют
            path_to_save = current_file_input
        else:
            main_dir = os.path.dirname(os.path.abspath(__file__))  # Путь до исполняемого файла (main.py)
            path_to_save = os.path.join(main_dir, "Export_" + task_title + "_" + str(
                CounterId.counter + 1) + ".xlsx")  # Добавляем в путь имя файла для сохранения
        task_time = f"{spinbox_hour.get()}:{spinbox_minute.get()}"  # Получаем время из спинбоксов
        task_time = datetime.strptime(task_time, "%H:%M").time()  # Приводим в формат
        # Повторность
        if repeat_var.get():  # Если чекбокс повторности проставлен
            task_repeat = int(spinbox_minute_repeat.get())  # Берем время повторного запуска из ентри
        else:
            task_repeat = 0  # Иначе время повторного запуска = 0

        task_sql = sql_editor.get("1.0", "end-1c")  # SQL-запрос

        # Введенные данные упаковываем в словарь, чтобы отправить на создание таска
        task_form_data = {
            "task_title": task_title,
            "path_to_save": path_to_save,
            "task_time": task_time,
            "task_repeat": task_repeat,
            "task_sql": task_sql
        }
        create_task(**task_form_data) # Создаем таск
        task_window.destroy()

    def button_file_path_pickup():
        file_to_save = pickup_file_save()
        if file_to_save:
            save_path_var.set(file_to_save)


    #Показать спинбокс для повторности (каждые Х минут), когда чекбокс повторности нажат
    def toggle_repeat_spinbox():
        if repeat_var.get(): # Если чекбокс прожат (True) показываем спинбокс
            spinbox_minute_repeat.config(state='normal')
        else:
            spinbox_minute_repeat.config(state='disabled')

    def close_task_info(): # Закрытие окна с таском, если мы его просто просматриваем
        refresh_table()
        task_window.destroy()

    # == Создаем новое окно типа Toplevel (дочернее) ==
    task_window = tk.Toplevel(root)
    task_window.title("Таск")
    task_window.resizable(False, False)  #Запрещаем изменение размера
    task_window.geometry("400x400")

    # = Размещаем подписи, спинбоксы и кнопки для создания таска =
    # Фрейм через grid чтобы было проще выравнивать
    frame_host = ttk.Frame(task_window)
    frame_host.pack(pady=10, padx=10, fill="x")  # Заполняем все окно
    frame_host.grid_columnconfigure(1, weight=1)  # Второй столбец растягивается на все окно
    label_task_title = ttk.Label(frame_host, text="Название таска:")
    label_task_title.grid(row=0, column=0, padx=5, sticky="w")  # Подпись НАЗВАНИЕ, столбец 0
    entry_task_title = ttk.Entry(frame_host)
    entry_task_title.grid(row=0, column=1, padx=5, sticky="EW")  # Строка ввода НАЗВАНИЯ, столбец 1, растягиваем на весь столбец
    label_task_id = ttk.Label(frame_host, text="ID:")
    label_task_id.grid(row=0, column=2, padx=0, sticky="e")  # Подпись ID, столбец 2
    entry_task_id = ttk.Entry(frame_host, width=6)  # Ввод ID, ширина = 6
    entry_task_id.grid(row=0, column=3, padx=5, sticky="ew")  # Строка ввода ID (НАКТИВНАЯ), столбец 3, растягиваем на весь столбец


    # Фрейм с выбором времени через спинбоксы
    time_container = ttk.Frame(frame_host)
    time_container.grid(row=1, column=0, columnspan=3, sticky="w", pady=10)

    # Переменные для начальных значений Часов\Минут\Минут повторности
    # Время запуска таска по умолчанию, через timedelta чтобы корректно переходить в новый час
    initial_start_time_for_task = datetime.now() + timedelta(minutes=TASK_START_TIME_MINUTES_ADD) # Добавляем значение из TASK_START_TIME_MINUTES_ADD, что бы перенести время запуска вперед
    hour_sb = tk.IntVar(value=initial_start_time_for_task.hour)
    minute_sb = tk.IntVar(value=initial_start_time_for_task.minute)
    repeat_minute_sb = tk.IntVar(value=10)

    # Подписи и спиннеры
    ttk.Label(time_container, text="Время запуска:").pack(side='left', padx=(5, 10))
    # Часы
    ttk.Label(time_container, text="Часы:").pack(side='left')
    spinbox_hour = tk.Spinbox(time_container, from_=0, to=23, textvariable=hour_sb, width=3, format="%02.0f", wrap=True)
    spinbox_hour.pack(side='left', padx=2)
    # Минуты
    ttk.Label(time_container, text="Минуты:").pack(side='left', padx=(5, 0))
    spinbox_minute = tk.Spinbox(time_container, from_=0, to=59, textvariable=minute_sb, width=3, format="%02.0f", wrap=True)
    spinbox_minute.pack(side='left', padx=2)

    # Кнопка "Добавить" в строке 1, на все последние колонки
    button_create_task = ttk.Button(frame_host, text="Добавить", command=button_submit_task)
    button_create_task.grid(row=1, column=3, columnspan=2, padx=5, pady=5, sticky="e")

    # = Путь сохранения файла =
    save_path_var = tk.StringVar()
    entry_file_path = ttk.Entry(frame_host, textvariable=save_path_var)
    entry_file_path.grid(row=2, column=0, columnspan=3, padx=5,sticky="EW")  # Строка ввода НАЗВАНИЯ, столбец 1, растягиваем на весь столбец
    button_pick_file_path = ttk.Button(frame_host, text="Файл сохр.", command=button_file_path_pickup)
    button_pick_file_path.grid(row=2, column=3, columnspan=2, padx=5, pady=5, sticky="EW")

    # Подпись sql запроса
    label_sql_title = ttk.Label(frame_host, text="Введите SQL:")
    label_sql_title.grid(row=3, column=0, padx=5, pady=5, sticky="w")  # Подпись Введите SQL слева, столбец 0

    # Чекбокс повтора
    repeat_var = tk.BooleanVar(value=False) # Переменная для признака повтора
    # Привязываем repeat_var к значению чекбокса и для проверки статуса назначаем команду
    check_repeat = ttk.Checkbutton(frame_host, text="Повторять задачу",variable=repeat_var, command=toggle_repeat_spinbox)
    check_repeat.grid(row=3, column=1, sticky="e", padx=5)
    # Минуты повторности (через сколько повторять таск)
    ttk.Label(frame_host, text="Минут:").grid(row=3, column=2, padx=0, sticky="e")
    # Спинбокс для времени повтора (минут), от 5 до 1440 с шагом в 5 минут
    spinbox_minute_repeat = tk.Spinbox(frame_host, from_=5, to=1440, increment=5, textvariable=repeat_minute_sb, width=4, format="%02.0f",
                                wrap=True)
    spinbox_minute_repeat.grid(row=3, column=3,  padx=(2, 5), sticky="w")
    spinbox_minute_repeat.config(state='disabled') # По умолчанию выключаем спинбокс

    # Окно ввода sql запроса
    sql_editor = scrolledtext.ScrolledText(frame_host, height=15, font=("Consolas", 11), undo=True)
    sql_editor.grid(row=4, column=0, columnspan=4, sticky="w", pady=10)
    sql_editor.insert("1.0", "SELECT * FROM users ORDER BY id")

    check_repeat.state(['!alternate'])  # Убираем состояние для чекбокса, которое рисует квадрат

    # Еще раз проверяем состояние чекбокса, т.к. иногда квадрат все-равно рисуется
    if 'alternate' in check_repeat.state():
        check_repeat.state(['!alternate'])

    center_window(task_window, root) # Центрируем окно относительно root
    task_window.focus()  # Фокус на окно
    task_window.grab_set()  # Запрещаем взаимодействовать с остальными окнами, пока открыто это

    # = Если выбран один из тасков дабл кликом =
    # Заполняем окно данными из таска
    if task_id:
        task = get_task(task_id, task_list)
        print(task.id)
        # if task.id == task_id:
        # Название таска
        entry_task_title.delete(0, tk.END)
        entry_task_title.insert(0, task.title)
        entry_task_title.config(state='disabled')  # Блокируем поле
        # ID таска
        entry_task_id.delete(0, tk.END)
        entry_task_id.insert(0, task.id)
        entry_task_id.config(state='disabled')  # Блокируем поле
        # Время запуска таска
        hour_sb.set(task.time_to_run.hour)  # Получаем часы
        spinbox_hour.config(format="%02.0f")  # Обновляем формат часов
        minute_sb.set(task.time_to_run.minute)  # Получаем минуты
        spinbox_minute.config(format="%02.0f")  # Обновляем формат минут
        spinbox_hour.config(state='disabled')  # Блокируем поле
        spinbox_minute.config(state='disabled')  # Блокируем поле
        # Повторность
        # Проверяем и проставляем чекбокс, а также минуты повторности
        if task.repeat > 0:
            repeat_var.set(True)
            repeat_minute_sb.set(task.repeat)
        else:
            check_repeat.state(['!selected'])
        check_repeat.config(state='disabled')  # Блокируем поле
        spinbox_minute_repeat.config(state='disabled')  # Блокируем поле
        # SQL запрос
        sql_editor.delete("1.0", tk.END)
        sql_editor.insert("1.0", task.sql_to_exec)
        sql_editor.config(state='disabled')  # Блокируем поле
        # Меняем текст кнопки на "Закрыть"
        button_create_task.config(text="Закрыть", command=close_task_info)
        # Путь сохранения файла
        entry_file_path.delete(0, tk.END)
        entry_file_path.insert(0, task.path_to_save)
        entry_file_path.config(state='disabled')  # Блокируем поле
        button_pick_file_path.config(state='disabled')  # Блокируем кнопку


    else: # Иначе заполняем значениями по умолчанию
        entry_task_id.insert(0, str(CounterId.counter + 1))  # Получаем CounterId для номера таска
        entry_task_title.insert(0, "Задача " + str(CounterId.counter + 1)) # Название задачи
        entry_task_id.config(state='disabled')  # Блокируем поле c ID, т.к. его ручной ввод не предусмотрен


    return show_task_window


# === Методы кнопок, окон и настроек ===
# == Включение\отключение кнопок и проверка статусов ==

# = Включить\отключить кнопку запуска =
def button_run_check():
    global task_list
    if len(task_list) > 0: # Если есть таски в списке, делаем кнопку запуска активной
        button_run.state(['!disabled'])
    else:
        button_run.state(['disabled'])

# = Включить\отключить кнопку удаления =
def button_delete_check():
    global task_list
    if len(task_list) > 0: # Если есть таски в списке, делаем кнопку удаления активной
        button_delete.state(['!disabled'])
    else:
        button_delete.state(['disabled'])

# = Включить\отключить кнопку обновления =
def button_refresh_check():
    global task_list
    if len(task_list) > 0: # Если есть таски в списке, делаем кнопку обновления активной
        button_refresh.state(['!disabled'])
    else:
        button_refresh.state(['disabled'])

# == Клики по кнопкам ==

# = Кнопка выхода в меню =
def menu_close_click():
    root.quit()

# = Кнопка экспорта тасков =
def menu_task_export_click():
    global task_list
    if task_list:
        filename_path = pickup_file_save("export_tasks.json", ".json",[("JSON файлы", "*.json")])
        from tools import save_tasks_to_json
        save_tasks_to_json(task_list, filename_path, log_function=log_message)
    else:
        log_message(f"Список задач пуст", 1)


# = Кнопка импорта тасков =
def menu_task_import_click():
    filename_path = pickup_file_open([("JSON файлы", "*.json")])
    from tools import load_tasks_from_json
    data = load_tasks_from_json(filename_path, log_function=log_message) # Читаем файл с тасками
    if not data: # Если не удалось прочитать
        log_message(f"Не удалось импортировать задачи.", 1)
        return
   # Проверяем, что есть настройки подключения к БД
    if not check_db_config():
        return
    # Проверяем, что пароль задан
    if not check_password():
        return
    # Создаем таски по полученным данным
    count = 0 # Счетчик тасков
    for item in data:
        try:
            # Превращаем строку из JSON обратно в datetime
            time_to_run = datetime.strptime(item["run_time"], "%H:%M").time()
            # Вызываем функцию создания таска
            create_task(
                check_db_pass=False,
                task_title=item.get('title'),
                path_to_save=item.get('path_to_save'),
                task_time=time_to_run,
                task_repeat=item.get('repeat'),
                task_sql=item.get('sql_to_exec')
            )
            count += 1
        except Exception as e:
            log_message(f"Ошибка при создании задачи из файла: {e}", 1)
    log_message(f"Импорт завершен. Добавлено задач: {count}")


# = Кнопка немедленного запуска =
def button_run_click():
    global task_list
    selected = table.focus()
    if len(task_list) == 0: return # Если тасков вообще нет - выходим
    # Если ничего не выбрано, и при этом в списке есть таски
    if not selected and len(task_list) > 0:
        log_message("Для запуска выберите таск", 1)
        return
    task_id = int(selected) # Выбранный таск
    task = get_task(task_id, task_list)
    run_task(task)

# = Кнопка добавить таск =
def button_add_task():
    show_task_window()
    refresh_table()

# = Кнопка удаления таска =
def button_delete_selected_task(by_keybord=False): # by_keybord - если удаляем нажатием Del
    global task_list
    selected = table.focus()
    if len(task_list) == 0: return # Если тасков вообще нет - выходим
    # Если ничего не выбрано, и при этом в списке есть таски
    if not selected and len(task_list) > 0:
        if not by_keybord: log_message("Для удаления выберите таск", 1)
        return
    task_to_delete = get_task(int(selected), task_list) # Таск на удаление
    # Убираем таск из планировщика запуска root.after и удаляем его ttk_after_id
    if task_to_delete:
        if task_to_delete.ttk_after_id:
            try:
                root.after_cancel(task_to_delete.ttk_after_id)
                task_to_delete.ttk_after_id = None
                log_message(f"Таск {task_to_delete.id} исключен из запуска")
            except:
                pass  # Если таймер уже сработал или недействителен
    # Заново собираем список тасков не включая в него удаленный таск по его id
    task_list = [task for task in task_list if task.id != task_to_delete.id]

    # Запоминаем индекс удаленного таска, чтобы выделить соседний
    all_items = table.get_children()
    current_index = all_items.index(selected)
    refresh_table() # Обновляем таблицу
    new_items = table.get_children()
    if new_items:
        # Если удалили последний таск — берем новый последний таск, иначе берем тот же индекс
        new_index = min(current_index, len(new_items) - 1)
        target_id = new_items[new_index]
        table.selection_set(target_id)
        table.focus(target_id)

# = Кнопка обновления =
def button_refresh():
    refresh_table()

# === Обновление таблицы ===
def refresh_table():
    for row in table.get_children():
        table.delete(row)

    from tools import get_delay
    for task in task_list:
        if task.status != TaskStatus.COMPLETED:
            run_time = get_delay(task.updating_time_to_run.hour, task.updating_time_to_run.minute)
            task.delay = run_time.delay
        values = (
            task.id,
            task.title,
            task.updating_time_to_run, # Отображаем обновляемое время запуска таска
            task.repeat,
            f"{task.delay/1000:.1f}" if task.delay is not None else task.delay, # Форматируем под более читаемый вид
            task.status.value
        )

        table.insert("", "end", iid=task.id, values=values)

    # Проверяем статус кнопок
    button_run_check()
    button_delete_check()
    button_refresh_check()


# === Логирование действий ===
def log_message(message, level=0):
    log_widget.config(state='normal') # Разблокируем log_widget для записи
    timestamp = datetime.now().strftime("%H:%M:%S") # Время добавления записи
    full_message = f"[{timestamp}]: {message}\n"
    log_widget.insert(tk.END, full_message) # Вставляем текст в конец виджета

    if level == 1: # Подкрашиваем для ошибок
        log_widget.tag_add("error", "end-2c linestart", "end-1c")
        log_widget.tag_config("error", foreground="red")

    log_widget.see(tk.END) # Прокручиваем окно виджета
    log_widget.config(state='disabled') # Блокируем виджет


# ===== Главное окно =====
root = tk.Tk()
root.title("Планировщик выгрузки")
root.geometry("550x650")
root.resizable(False, False)  #Запрещаем изменение размера
root.option_add("*tearOff", False)  #Убираем для ttk.menu строку после основного пункта

# = Иконка приложения =
icon_image = tk.PhotoImage(file="IMG/img_logo.png")
root.iconphoto(True, icon_image)

# = Загрузка иконок для кнопок =
image = Image.open("IMG/img_add.png")
image = image.resize((15, 15), Image.Resampling.LANCZOS)
add_ph_image = ImageTk.PhotoImage(image)
image = Image.open("IMG/img_delete.png")
image = image.resize((15, 15), Image.Resampling.LANCZOS)
delete_ph_image = ImageTk.PhotoImage(image)
image = Image.open("IMG/img_run.png")
image = image.resize((15, 15), Image.Resampling.LANCZOS)
run_ph_image = ImageTk.PhotoImage(image)
image = Image.open("IMG/img_refresh.png")
image = image.resize((15, 15), Image.Resampling.LANCZOS)
refresh_ph_image = ImageTk.PhotoImage(image)

# === Меню ===
main_menu = tk.Menu()
file_menu = tk.Menu()
file_menu.add_command(label="Импорт тасков", command=menu_task_import_click)
file_menu.add_command(label="Экспорт тасков", command=menu_task_export_click)
file_menu.add_command(label="Настройка подключения", command=show_connect_window)
file_menu.add_separator()  # Добавляем разделитель перед кнопкой выход
file_menu.add_command(label="Выход", command=menu_close_click)
main_menu.add_cascade(label="Опции", menu=file_menu)

# ===== Кнопки =====
# Фрейм для кнопок
frame_buttons = ttk.Frame(root, padding="0")
frame_buttons.pack(fill='both', anchor="w", padx=10, pady=1)

# Кнопка добавить
button_add = ttk.Button(frame_buttons, text="Добавить", command=button_add_task, image=add_ph_image, compound=tk.LEFT)
button_add.pack(side='left', padx=0, pady=5)
# Кнопка запуск
button_run = ttk.Button(frame_buttons, text="Запустить", command=button_run_click, image=run_ph_image, compound=tk.LEFT)
button_run.pack(side='left', padx=0, pady=5)
# Кнопка обновить
button_refresh = ttk.Button(frame_buttons, text="Обновить", command=button_refresh, image=refresh_ph_image, compound=tk.LEFT)
button_refresh.pack(side='left', padx=0, pady=5)
# Кнопка удалить
button_delete = ttk.Button(frame_buttons, text="Удалить", command=button_delete_selected_task, image=delete_ph_image, compound=tk.LEFT)
button_delete.pack(side='left', padx=0, pady=5)
#Проверяем кнопки и меняем их статус
button_run_check()
button_delete_check()
button_refresh_check()

# Кнопка задать пароль
button_set_password = ttk.Button(frame_buttons, text="Задать пароль", command=show_password_window, compound=tk.LEFT)
button_set_password.pack(side='right', padx=0, pady=5)

root.config(menu=main_menu)  # Добавляем кнопку меню

# ===== Таблица =====
table = ttk.Treeview(root, columns=("id", "title", "start_time", "repeat", "delay", "status"), show="headings")

# === Заголовки ===
table.heading("id", text="ID")
table.heading("title", text="Название", anchor="w")
table.heading("start_time", text="Время запуска", anchor="w")
table.heading("repeat", text="Повторять", anchor="w")
table.heading("delay", text="Задержка (сек.)", anchor="w")
table.heading("status", text="Статус", anchor="w")

# === Свойства колонок ===
table.column("id", width=40, minwidth=30, anchor="center", stretch=False)
table.column("title", width=40, anchor="w")
table.column("start_time", width=115, minwidth=110, anchor="w", stretch=False)
table.column("repeat", width=70, minwidth=65,  anchor="center", stretch=False)
table.column("delay", width=20, anchor="center")
table.column("status", width=65, minwidth=60, anchor="w", stretch=False)

table.pack(fill="both", expand=True, padx=10, pady=1)

# === Биндим кнопку Del на удаление таска ===
table.bind("<Delete>", lambda event: button_delete_selected_task(True))

# === Виджет для логов ===
log_widget = scrolledtext.ScrolledText(root, height=10, state='disabled', font=("Consolas", 10))
log_widget.pack(padx=10, pady=10, fill="both")

# === Дабл клик по таску в таблице ===
table.bind("<Double-1>", on_table_double_click)


# ===== Загрузка данных при старте =====


# Загружаем конфиг из файла
db_config = load_config(log_function=log_message)
# Обновляем таблицу
refresh_table()
# Основное окно
root.mainloop()

