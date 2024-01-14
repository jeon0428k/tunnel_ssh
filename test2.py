from sqlalchemy import create_engine, MetaData, text, Table, Column, String, inspect, JSON

import datetime
import psutil

PROC_ATTRS = ['pid', 'name', 'username', 'status', 'create_time']
# PROC_ATTRS = []

TABLE_NAME = "proc"
engine = create_engine("mysql+pymysql://root:5402@localhost:3306/ZDB")


def proc_print_keys():
    for key in list(psutil.Process().as_dict().keys()):
        print(key)


def get_create_table(proc_info):
    metadata = MetaData()
    inspector = inspect(engine)
    if TABLE_NAME not in inspector.get_table_names():
        cols = []
        for key, value in proc_info.items():
            print(f"{key} -> {value}")
            if isinstance(value, dict):
                cols.append(Column(key, JSON))
            elif isinstance(value, list):
                cols.append(Column(key, JSON))
            else:
                cols.append(Column(key, String(500)))
        table = Table(TABLE_NAME, metadata, *cols)
        metadata.create_all(engine)
    else:
        table = Table(TABLE_NAME, metadata, autoload_with=engine)
    return table


def proc_print(params):
    connection = engine.connect()
    connection.execute(text("DROP TABLE IF EXISTS proc"))
    for proc in psutil.process_iter():
        try:
            if params:
                proc_info = proc.as_dict(attrs=params)
                if 'create_time' in proc_info:
                    create_time = datetime.datetime.fromtimestamp(proc_info['create_time'])
                    proc_info['create_time'] = create_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                proc_info = proc.as_dict()
            print(proc_info)

            table = get_create_table(proc_info)

            # connection.execute(table.insert().values(proc_info))
            connection.execute(table.insert(), [proc_info])
            connection.commit()

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # 프로세스에 접근할 수 없는 경우를 처리합니다.
            pass

    connection.close()


# proc_print_keys()
proc_print(PROC_ATTRS)
