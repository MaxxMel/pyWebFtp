from fastapi import FastAPI, WebSocket, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from ftplib import FTP
import ftplib

# Создаем экземпляр приложения
app = FastAPI()

# Указываем путь к статическим файлам и шаблонам
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Хранилище данных для сессии
session_data = {}

# Главная страница (html_ftp.html)
@app.get("/", response_class=HTMLResponse)
async def serve_login_page():
    return templates.TemplateResponse("html_ftp.html", {"request": {}})

# Обработка формы авторизации
@app.post("/login", response_class=RedirectResponse)
async def login(
    ftp_host: str = Form(...),
    ftp_login: str = Form(...),
    ftp_password: str = Form(...)
):
    global session_data
    session_data = {
        "ftp_host": ftp_host,
        "ftp_login": ftp_login,
        "ftp_password": ftp_password,
    }
    # Перенаправление на страницу с консолью
    return RedirectResponse(url="/work", status_code=303)

# Страница с вводом команд (ftp_html_2.html)
@app.get("/work", response_class=HTMLResponse)
async def serve_work_page():
    if not session_data:
        # Если нет данных сессии, возвращаем на страницу авторизации
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("ftp_html_2.html", {"request": {}, "session_data": session_data})

# WebSocket для обработки команд FTP
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ftp_host = session_data.get("ftp_host")
    ftp_login = session_data.get("ftp_login")
    ftp_password = session_data.get("ftp_password")

    try:
        # Подключаемся к FTP-серверу
        ftp = FTP(ftp_host)
        ftp.login(user=ftp_login, passwd=ftp_password)
        await websocket.send_text(f"Подключение к {ftp_host} успешно. Введите FTP-команду.")
    except Exception as e:
        await websocket.send_text(f"Ошибка подключения к FTP-серверу: {e}")
        await websocket.close()
        return

    while True:
        try:
            command = await websocket.receive_text()  # Получаем команду от клиента
            """if command.lower() == "ls":
                # Список файлов и директорий
                file_list = []
                ftp.retrlines("LIST", file_list.append)
                response = "\n".join(file_list)
                await websocket.send_text(response)
            """
            # Измененный блок команды ls
            if command.lower() == "ls":
                current_dir = ftp.pwd()  # Получаем текущую директорию
                items = ftp.nlst()
                response = f"Содержимое {current_dir}:\n"

                for item in items:
                    try:
                        ftp.cwd(item)  # Проверяем, является ли объект директорией
                        response += f"{item}/ (директория)\n"
                        ftp.cwd(current_dir)  # Возвращаемся обратно
                    except ftplib.error_perm:
                        response += f"{item} (файл)\n"
                await websocket.send_text(response)

            # Обновленный блок команды cd
            elif command.lower().startswith("cd "):
                dir_name = command[3:].strip()
                try:
                    ftp.cwd(dir_name)
                    await websocket.send_text(f"Перешли в директорию {dir_name}")
                except ftplib.error_perm:
                    await websocket.send_text(f"Ошибка: не удалось перейти в {dir_name}")

            elif command.lower().startswith("get "):
                # Скачать файл
                filename = command[4:].strip()
                with open(filename, "wb") as f:
                    ftp.retrbinary(f"RETR {filename}", f.write)
                await websocket.send_text(f"Файл {filename} загружен.")
            elif command.lower().startswith("put "):
                # Загрузить файл на сервер
                filename = command[4:].strip()
                with open(filename, "rb") as f:
                    ftp.storbinary(f"STOR {filename}", f)
                await websocket.send_text(f"Файл {filename} загружен на сервер.")
            elif command.lower() == "quit":
                ftp.quit()
                await websocket.send_text("Отключение от сервера.")
                break
            else:
                await websocket.send_text(f"Неизвестная команда: {command}")
        except Exception as e:
            await websocket.send_text(f"Ошибка: {e}")
            break

    await websocket.close()

"""
- ftp-host: students.yss.su
- login: ftpiu8
- passwd: 3Ru7yOTA

"""