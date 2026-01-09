import psycopg2
import pandas as pd

# Подключение к БД
def connect_oss(log_function=None, **kwargs):
    # Извлекаем значения из kwargs
    host = kwargs.get('host')
    port = kwargs.get('port')
    dbname = kwargs.get('dbname')
    user = kwargs.get('user')
    password = kwargs.get('password')
    sql_exec = kwargs.get('sql_exec')

    try:
        conn = psycopg2.connect(dbname=dbname, host=host, port=port, user=user, password=password)
        cursor = conn.cursor()
        cursor.execute(sql_exec)
        conn.commit()
        column_names = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        conn.close()
        if log_function: log_function(f"Запрос выполнен. Данные получены. Подключение закрыто.")
        return pd.DataFrame(data, columns=column_names)
    except Exception as e_error:
        if log_function: log_function(f"Ошибка при подключении\запросе подключения: {e_error}", 1)
        return None