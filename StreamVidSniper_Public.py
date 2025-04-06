import sys
import re
import os
import requests
import asyncio
import webbrowser
import threading
from threading import Thread
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem, QLineEdit, QTabWidget, QTextEdit, QAbstractItemView
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QIcon, QFont
from io import BytesIO
from twitchio.ext import commands

YOUTUBE_REGEX = r'(https?://(?:www\.|m\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+))'


# File dir

os.chdir(os.path.dirname(__file__))  
basedir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(basedir, 'resources', 'icon.ico')

# Access Token Twitch

ACCESS_TOKEN = "oauth:INSERT_YOUR_TWITCH_ACCESS_TOKEN"

# API Google

ACCESS_GOOGLE = "INSERT_YOUR_GOOGLE_API_KEY"

def obtener_info_video(video_id):
    API_KEY = ACCESS_GOOGLE
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id={video_id}&key={API_KEY}"
    
    response = requests.get(url).json()
    if 'items' in response and response['items']:
        item = response['items'][0]
        titulo = item['snippet']['title']
        fecha = item['snippet']['publishedAt'][:10]
        thumbnail_url = item['snippet']['thumbnails']['medium']['url']
        duracion = item['contentDetails']['duration']
        return titulo, fecha, duracion, thumbnail_url
    return None

# Video duration time

def formatear_duracion(iso_duracion):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duracion)
    if not match:
        return "Unknown Duration"

    horas = int(match.group(1)) if match.group(1) else 0
    minutos = int(match.group(2)) if match.group(2) else 0
    segundos = int(match.group(3)) if match.group(3) else 0

    if horas:
        return f"{horas}:{minutos:02}:{segundos:02}"
    else:
        return f"{minutos}:{segundos:02}"

# Class TwitchBOT

class TwitchBot(commands.Bot):
    """Catch Twitch Chat Messages."""
    def __init__(self, app, channel, token, video_signal):
        super().__init__(token=token, prefix='!', initial_channels=[channel])
        self.app = app
        self.channel = channel
        self.video_signal = video_signal

    async def event_ready(self):
        self.app.log(f"Starting...")
        self.app.log(f"Connected to: {self.channel}")  # Añadir log de conexión
        self.app.log(f"✅ Connected.")


    async def event_message(self, message):
        if message.echo:
            return
        match = re.search(YOUTUBE_REGEX, message.content)
        if match:
            video_url, video_id = match.groups()
            self.app.log(f"Youtube URL found: {video_url}")  # Verificar enlace encontrado
            info = obtener_info_video(video_id)
            usuario = message.author.name
            if info:
                self.video_signal.nuevo_video.emit(video_url, *info, usuario)

    async def run_bot(self):
        await self.start()

# Class APP

class VideoScraperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.bot = None

        # Signal to receive videos from bot thread
        self.video_signal = VideoSignal()
        self.video_signal.nuevo_video.connect(self.agregar_video)

    def initUI(self):
        self.setWindowTitle('StreamVid Sniper')
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.ico")))
        self.setGeometry(100, 100, 700, 500)
        layout = QVBoxLayout()

        # UI tabs
        self.tabs = QTabWidget()
        self.tab_videos = QWidget()
        self.tab_logs = QWidget()
        self.tab_about = QWidget()

        self.tabs.addTab(self.tab_videos, "Grabber")
        self.tabs.addTab(self.tab_logs, "Logs")
        self.tabs.addTab(self.tab_about, "About")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.init_video_tab()
        self.init_logs_tab()
        self.init_about_tab()

        # Channel Input


    def abrir_enlace(self, item):
        url = item.data(256)
        if url:
            webbrowser.open(url)

    def iniciar_bot(self):
        channel = self.channel_input.text().strip()
        print("Bot starting...")  # debug message

        

        if channel:
            token = ACCESS_TOKEN
            if not token:
                print("Error: Can't get Twitch access token.")
                return

            # Run everything in a separate thread: create bot and run it
            bot_thread = Thread(target=self.ejecutar_bot_en_hilo, args=(channel, token))
            bot_thread.start()

            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)


    def detener_bot(self):
        if self.bot and self.bot_loop:
            asyncio.run_coroutine_threadsafe(self.bot.close(), self.bot_loop)
            self.bot = None

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)



    def ejecutar_bot_en_hilo(self, channel, token):
        loop = asyncio.new_event_loop()
        self.bot_loop = loop  
        asyncio.set_event_loop(loop)

        
        self.bot = TwitchBot(self, channel, token, self.video_signal)
        loop.run_until_complete(self.bot.run_bot())


    def agregar_video(self, url, titulo, fecha, duracion, thumbnail_url, usuario):
        item = QListWidgetItem()
        widget = QWidget()
        layout = QVBoxLayout()

        duracion_legible = formatear_duracion(duracion)

        label_titulo = QLabel(f'🎬 <b>Title:</b> {titulo}')
        label_titulo.setStyleSheet("font-size: 13pt;")
        label_usuario = QLabel(f'👤 <b>Send by:</b> {usuario}')
        label_usuario.setStyleSheet("font-size: 13pt;")
        label_duracion = QLabel(f'⏱️ <b>Duration:</b> {duracion_legible}')
        label_duracion.setStyleSheet("font-size: 13pt;")
        label_fecha = QLabel(f'🗓️ <b>Date:</b> {fecha}')
        label_fecha.setStyleSheet("font-size: 13pt;")
        label_thumbnail = QLabel()

        img_data = requests.get(thumbnail_url).content
        pixmap = QPixmap()
        pixmap.loadFromData(BytesIO(img_data).read())
        label_thumbnail.setPixmap(pixmap.scaled(160, 90))

        layout.addWidget(label_thumbnail)
        layout.addWidget(label_titulo)
        layout.addWidget(label_usuario)
        layout.addWidget(label_duracion)
        layout.addWidget(label_fecha)


        widget.setLayout(layout)
        item.setSizeHint(widget.sizeHint())

        # Save URL as "data" to open later
        item.setData(256, url)  # 256 = Qt.UserRole

        self.lista_videos.insertItem(0, item)
        self.lista_videos.setItemWidget(item, widget)

    def init_video_tab(self):
        layout = QVBoxLayout()

        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText('Twitch Channel Name')
        layout.addWidget(self.channel_input)

        self.start_button = QPushButton('Start')
        self.start_button.clicked.connect(self.iniciar_bot)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton('Stop')
        self.stop_button.clicked.connect(self.detener_bot)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)

        self.lista_videos = QListWidget()
        self.lista_videos.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lista_videos.itemClicked.connect(self.abrir_enlace)
        layout.addWidget(self.lista_videos)

        self.tab_videos.setLayout(layout)

    def init_logs_tab(self):
        layout = QVBoxLayout()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.tab_logs.setLayout(layout)
    
    # Log Messages

    def log(self, mensaje):
        print(mensaje)  # showing in console
        self.log_output.append(mensaje)

    # About

    def init_about_tab(self):
        layout = QVBoxLayout()

        label_nombre = QLabel("Made by Alomancia 💜")
        label_nombre.setStyleSheet("font-size: 13pt;")
        label_correo = QLabel("https://github.com/Alomancia")
        label_correo.setStyleSheet("font-size: 13pt;")
        label_version = QLabel("Version 1.0")
        label_version.setStyleSheet("font-size: 13pt;")

        layout.addWidget(label_nombre)
        layout.addWidget(label_correo)
        layout.addWidget(label_version)

        layout.addStretch() 
        self.tab_about.setLayout(layout)



# Clase Signal Loop

class VideoSignal(QObject):
    nuevo_video = pyqtSignal(str, str, str, str, str, str)  # url, title, date, duration, thumbnail, user




if __name__ == '__main__':
    app = QApplication(sys.argv)

    fuente = QFont("Roboto", 11)
    app.setFont(fuente)

    window = VideoScraperApp()
    window.show()
    sys.exit(app.exec())