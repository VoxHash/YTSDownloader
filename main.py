import sys
import os
import time
import numpy as np
import yt_dlp
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image
from PyQt6.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QLabel, 
    QPushButton, 
    QLineEdit, 
    QRadioButton, 
    QButtonGroup, 
    QFileDialog, 
    QProgressBar, 
    QMessageBox, 
    QTabWidget, 
    QTextEdit,
    QFormLayout,
    QToolButton
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSize, QPoint, QObject
from PyQt6.QtGui import QIcon
import configparser
import logging

DEBUG = False

# Function to read configuration from a file
def read_config(file_path):
    config = configparser.ConfigParser()
    config.read(file_path)
    return config

# Load configuration
config = read_config('config.ini')
theme = config["SETTINGS"]["THEME"]
timer = int(config["SETTINGS"]["COUNT_TIMER_ONGOING"])
cookies_from_browser = config["SETTINGS"].get("COOKIES_FROM_BROWSER", "").strip()
cookies_file = config["SETTINGS"].get("COOKIES_FILE", "").strip()
js_runtime = config["SETTINGS"].get("JS_RUNTIME", "").strip()
js_runtime_path = config["SETTINGS"].get("JS_RUNTIME_PATH", "").strip()

def parse_cookies_from_browser(value):
    parts = [item.strip() for item in value.split(":") if item.strip()]
    if not parts:
        return None
    return tuple(parts)

def with_auth_opts(ydl_opts):
    ydl_opts["no_color"] = True
    if js_runtime:
        if js_runtime_path:
            ydl_opts["js_runtimes"] = {js_runtime: {"path": js_runtime_path}}
        else:
            ydl_opts["js_runtimes"] = {js_runtime: {}}
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = parse_cookies_from_browser(cookies_from_browser)
    elif cookies_file:
        ydl_opts["cookiefile"] = cookies_file
    return ydl_opts

# Set up logging configuration
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Capture all messages
title_cache = {}
cache_stats = {"hits": 0, "misses": 0}

class LogEmitter(QObject):
    message = pyqtSignal(str)

class TextEditLogger(logging.Handler):
    def __init__(self, emitter):
        super().__init__()
        self.emitter = emitter

    def emit(self, record):
        msg = self.format(record)
        self.emitter.message.emit(msg)

def clean_filename(filename):
    valid_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789áéíóúÁÉÍÓÚñÑ#"
    filename = ''.join(c for c in filename if c in valid_chars)
    return filename

def cache_title(link, title):
    if link and title and link not in title_cache:
        title_cache[link] = title

def reset_cache_stats():
    cache_stats["hits"] = 0
    cache_stats["misses"] = 0

def mark_cache_hit():
    cache_stats["hits"] += 1

def mark_cache_miss():
    cache_stats["misses"] += 1

def get_cache_status_text():
    hits = cache_stats["hits"]
    misses = cache_stats["misses"]
    total = hits + misses
    ratio = (hits / total * 100) if total else 0.0
    return f"Metadata cache - hits: {hits} | misses: {misses} | hit ratio: {ratio:.1f}%"

def get_video_links(input_url):
    ydl_opts = with_auth_opts({
        'quiet': True,
        'extract_flat': True,
        'playlist_end': 1 if DEBUG else 100,
    })
    input_url = input_url.strip()
    if '/watch?' in input_url or '/shorts/' in input_url or 'youtu.be/' in input_url:
        return [input_url]

    channel_url = input_url
    parts_to_remove = ['/about', '/community', '/playlist', '/playlists', '/streams', '/featured', '/videos', '/shorts']
    for part in parts_to_remove:
        channel_url = channel_url.split(part)[0]

    links = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for tab_path in ('/videos', '/shorts'):
            try:
                result = ydl.extract_info(f"{channel_url}{tab_path}", download=False)
            except Exception as error:
                logging.warning(f"Could not extract links from {channel_url}{tab_path}: {error}")
                continue

            if 'entries' not in result:
                continue

            for entry in result['entries']:
                entry_url = entry.get('url') or entry.get('webpage_url')
                entry_id = entry.get('id')
                entry_title = entry.get('title')
                if entry_url and entry_url.startswith('http'):
                    links.append(entry_url)
                    cache_title(entry_url, entry_title)
                elif entry_id:
                    resolved_url = f'https://www.youtube.com/watch?v={entry_id}'
                    links.append(resolved_url)
                    cache_title(resolved_url, entry_title)

    if not links:
        logging.warning("No videos found for the provided URL.")
        return []
    return list(dict.fromkeys(links))

def get_platform_links(input_url, platform):
    ydl_opts = with_auth_opts({
        'quiet': True,
        'extract_flat': True,
        'playlist_end': 1 if DEBUG else 100,
    })
    input_url = input_url.strip()
    links = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(input_url, download=False)
    except Exception as error:
        logging.warning(f"Could not extract links from {platform} URL {input_url}: {error}")
        return []

    entries = result.get('entries') if isinstance(result, dict) else None
    if entries:
        for entry in entries:
            entry_url = entry.get('url') or entry.get('webpage_url')
            entry_title = entry.get('title')
            if entry_url and entry_url.startswith('http'):
                links.append(entry_url)
                cache_title(entry_url, entry_title)
        if links:
            return list(dict.fromkeys(links))

    return [input_url]

def get_instagram_links(input_url):
    return get_platform_links(input_url, "Instagram")

def get_facebook_links(input_url):
    return get_platform_links(input_url, "Facebook")

def get_tiktok_links(input_url):
    return get_platform_links(input_url, "TikTok")

def save_original_names(links, output_path, output_format):
    with open(os.path.join(output_path, "original_names.txt"), "w", encoding="utf-8") as file:
        links_to_process = links[:1] if DEBUG else links
        ydl_opts = with_auth_opts({'quiet': True})
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for link in links_to_process:
                try:
                    cached_title = title_cache.get(link)
                    if cached_title:
                        mark_cache_hit()
                        title = cached_title
                    else:
                        mark_cache_miss()
                        info = ydl.extract_info(link, download=False)
                        title = info.get('title', 'unknown_title')
                        cache_title(link, title)
                except Exception as error:
                    logging.warning(f"Could not fetch metadata for {link}: {error}")
                    title = 'unknown_title'
                file.write(f"{link}|{clean_filename(title)}.{output_format}\n")

def add_watermark(video_path, watermark_path, output_path):
    try:
        with VideoFileClip(video_path) as video:
            video_width, video_height = video.size

            # Load and resize the watermark image
            watermark = Image.open(watermark_path).convert("RGBA")
            watermark = watermark.resize((video_width, video_height), Image.LANCZOS)

            # Convert PIL Image to ImageClip
            watermark_array = np.array(watermark)
            watermark_clip = ImageClip(watermark_array).with_duration(video.duration).with_opacity(1)

            # Overlay the watermark on the video
            final_video = CompositeVideoClip([video.with_audio(video.audio), watermark_clip.with_position(('center', 'center'))])

            # Choose codecs based on output format
            if output_path.endswith('.mp4'):
                codec = 'libx264'
                audio_codec = 'aac'
            elif output_path.endswith('.webm'):
                codec = 'libvpx'
                audio_codec = 'libvorbis'
            else:
                raise ValueError("Unsupported output format")

            # Write the final video file
            final_video.write_videofile(output_path, codec=codec, audio_codec=audio_codec, fps=24)
            return "Video processed successfully."
    except Exception as e:
        return f"Error adding watermark: {str(e)}"

class WorkerThread(QThread):
    update_progress = pyqtSignal(int)
    update_message = pyqtSignal(str)
    update_cache_status = pyqtSignal(str)

    def __init__(self, links, output_path, frame_image_path, output_format):
        super().__init__()
        self.links = links
        self.output_path = output_path
        self.frame_image_path = frame_image_path
        self.output_format = output_format

    def run(self):
        self.process_videos()

    def process_videos(self):
        with open(os.path.join(self.output_path, "original_names.txt"), "r", encoding="utf-8") as file:
            original_names = {line.split('|')[0]: line.split('|')[1].strip() for line in file}

        self.update_cache_status.emit(get_cache_status_text())
        total_links = len(self.links)
        for index, link in enumerate(self.links, start=1):
            if DEBUG and index > 1:
                break
            link = link.strip()
            original_name = original_names.get(link, f"{index}_unknown_title.{self.output_format}")
            output_filename = f"{index}_{clean_filename(link)}"
            output_file_path = os.path.join(self.output_path, output_filename).replace('\\', '/')
            final_file_path = os.path.join(self.output_path, f"{index}_{original_name}").replace('\\', '/')

            try:
                ydl_opts = {
                    'format': 'bestvideo+bestaudio/best',
                    'outtmpl': f"{output_file_path}.%(ext)s",
                    'noplaylist': True,
                    'quiet': True
                }
                ydl_opts = with_auth_opts(ydl_opts)

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([link])

                # Find the downloaded file
                downloaded_file = None
                for file in os.listdir(self.output_path):
                    if file.startswith(output_filename) and file.endswith(('.mp4', '.mkv', '.webm')):
                        downloaded_file = os.path.join(self.output_path, file)
                        break

                if not downloaded_file:
                    raise Exception(f"Downloaded file not found for {output_filename}")

                # Add watermark if provided, otherwise keep original download.
                if self.frame_image_path:
                    message = add_watermark(downloaded_file, self.frame_image_path, final_file_path)
                else:
                    downloaded_ext = os.path.splitext(downloaded_file)[1]
                    final_name = f"{index}_{os.path.splitext(original_name)[0]}{downloaded_ext}"
                    final_file_path = os.path.join(self.output_path, final_name).replace('\\', '/')
                    os.replace(downloaded_file, final_file_path)
                    message = "Video downloaded successfully."

                if os.path.exists(final_file_path):
                    if self.frame_image_path and os.path.exists(downloaded_file):
                        os.remove(downloaded_file)
                    self.update_message.emit(f"Video {index}/{total_links} processed successfully.")
                else:
                    self.update_message.emit(f"Error: final file not created for video {index}/{total_links}.")
            except Exception as e:
                self.update_message.emit(f"Error processing video {index}/{total_links}: {str(e)}")

            progress = int((index / total_links) * 100)
            self.update_progress.emit(progress)
            self.update_cache_status.emit(get_cache_status_text())
            time.sleep(timer)  # Small pause between downloads to avoid rate limits

class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.initial_pos = None

        # App Title Bar
        title_bar_layout = QHBoxLayout(self)
        title_bar_layout.setContentsMargins(1, 1, 1, 1)
        title_bar_layout.setSpacing(2)
        
        # App icon
        self.icon_label = QLabel()
        self.icon_label.setPixmap(QIcon(f"themes/{theme}/images/icon.png").pixmap(32, 32))  # Load the icon
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setStyleSheet(
            """
        QLabel { border: none; }
        """
        )
        title_bar_layout.addWidget(self.icon_label)

        # Title Section
        self.title = QLabel(f"{self.__class__.__name__}", self)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet(
            """
        QLabel { text-transform: uppercase; font-size: 10pt; margin-left: 48px; border: none; }
        """
        )

        if title := parent.windowTitle():
            self.title.setText(title)
        title_bar_layout.addWidget(self.title)
        
        # Buttons Bar
        # Min button
        self.minimize_button = QToolButton(self)
        minimize_icon = QIcon()
        minimize_icon.addFile(f"themes/{theme}/images/min.svg")
        self.minimize_button.setIcon(minimize_icon)
        self.minimize_button.clicked.connect(self.minimize_window)

        # Normal button
        self.normal_button = QToolButton(self)
        normal_icon = QIcon()
        normal_icon.addFile(f"themes/{theme}/images/normal.svg")
        self.normal_button.setIcon(normal_icon)
        self.normal_button.clicked.connect(self.maximize_window)
        self.normal_button.setVisible(False)

        # Max button
        self.maximize_button = QToolButton(self)
        maximize_icon = QIcon()
        maximize_icon.addFile(f"themes/{theme}/images/max.svg")
        self.maximize_button.setIcon(maximize_icon)
        self.maximize_button.clicked.connect(self.maximize_window)

        # Close button
        self.close_button = QToolButton(self)
        close_icon = QIcon()
        close_icon.addFile(f"themes/{theme}/images/close.svg")
        self.close_button.setIcon(close_icon)
        self.close_button.clicked.connect(self.close_window)

        # Add buttons
        buttons = [
            self.minimize_button,
            self.normal_button,
            self.maximize_button,
            self.close_button,
        ]
        for button in buttons:
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setFixedSize(QSize(16, 16))
            button.setStyleSheet(
                """QToolButton {
                    border: none;
                    padding: 2px;
                }
                """
            )
            title_bar_layout.addWidget(button)

    def minimize_window(self):
        self.window().showMinimized()

    def maximize_window(self):
        if self.window().isMaximized():
            self.window().showNormal()
            self.normal_button.setVisible(True)
            self.maximize_button.setVisible(False)
        else:
            self.window().showMaximized()
            self.normal_button.setVisible(False)
            self.maximize_button.setVisible(True)

    def close_window(self):
        self.window().close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.initial_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.initial_pos is not None:
            self.window().move(event.globalPosition().toPoint() - self.initial_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_window()
            event.accept()

class VideoDownloaderTab(QWidget):
    def __init__(self, platform_name, func):
        super().__init__()
        self.platform_name = platform_name
        self.func = func

        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.form_widget = QWidget()
        self.form_widget.setLayout(self.form_layout)
        self.layout.addWidget(self.form_widget)

        self.folder_label = QLabel("Output Folder:")
        self.folder_button = QPushButton("Browse")
        self.folder_edit = QLineEdit()
        self.folder_button.clicked.connect(self.browse_folder)

        self.channel_label = QLabel(f"{self.platform_name} URL:")
        self.channel_edit = QLineEdit()
        self.platform_hint_label = QLabel(self.get_platform_hint())
        self.platform_hint_label.setWordWrap(True)
        self.platform_hint_label.setStyleSheet("QLabel { border: none; }")

        self.shape_label = QLabel("Watermark (PNG):")
        self.shape_button = QPushButton("Browse")
        self.shape_edit = QLineEdit()
        self.shape_button.clicked.connect(self.browse_shape)

        self.format_label = QLabel("Output Format:")
        self.format_webm = QRadioButton("WebM")
        self.format_mp4 = QRadioButton("MP4")
        self.format_group = QButtonGroup()
        self.format_group.addButton(self.format_webm)
        self.format_group.addButton(self.format_mp4)
        self.format_webm.setChecked(True)

        self.start_button = QPushButton("Start Download")
        self.start_button.clicked.connect(self.start_download)
        self.auth_check_button = QPushButton("Check Auth")
        self.auth_check_button.clicked.connect(self.check_auth_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                text-align: center;
            }
            """
        )
        self.progress_label = QLabel("")
        self.cache_status_label = QLabel(get_cache_status_text())

        self.log_text_box = QTextEdit(self)
        self.log_text_box.setReadOnly(True)
        self.log_emitter = LogEmitter()
        self.log_emitter.message.connect(self.log_text_box.append)
        self.log_text_box_handler = TextEditLogger(self.log_emitter)
        self.log_text_box_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(self.log_text_box_handler)

        # Layout setup
        self.form_layout.addRow(self.folder_label, self.folder_button)
        self.form_layout.addRow(self.folder_edit)
        self.form_layout.addRow(self.channel_label, self.channel_edit)
        self.form_layout.addRow(self.platform_hint_label)
        self.form_layout.addRow(self.shape_label, self.shape_button)
        self.form_layout.addRow(self.shape_edit)
        self.form_layout.addRow(self.format_label)
        self.form_layout.addRow(self.format_webm, self.format_mp4)
        self.layout.addWidget(self.auth_check_button)
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.progress_label)
        self.layout.addWidget(self.cache_status_label)
        self.layout.addWidget(self.log_text_box)

    def closeEvent(self, event):
        try:
            logger.removeHandler(self.log_text_box_handler)
            self.log_emitter.message.disconnect(self.log_text_box.append)
        except Exception:
            pass
        super().closeEvent(event)

    def get_platform_hint(self):
        if "Instagram" in self.platform_name:
            return "Tip: Instagram often requires authentication. Set COOKIES_FROM_BROWSER or COOKIES_FILE in config.ini."
        if "Facebook" in self.platform_name:
            return "Tip: Use direct video/post URLs when possible. Private or age-restricted content needs cookies in config.ini."
        if "TikTok" in self.platform_name:
            return "Tip: Profile and video URLs are supported. If extraction fails, configure cookies in config.ini."
        return "Tip: Channel, video, and shorts URLs are supported. If blocked, configure cookies in config.ini."

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_edit.setText(folder)

    def browse_shape(self):
        shape_file, _ = QFileDialog.getOpenFileName(self, "Select Watermark Image", "", "PNG Files (*.png)")
        if shape_file:
            self.shape_edit.setText(shape_file)

    def start_download(self):
        output_directory = self.folder_edit.text()
        frame_image_path = self.shape_edit.text()
        output_format = "mp4" if self.format_mp4.isChecked() else "webm"
        source_url = self.channel_edit.text()

        if not all([output_directory, source_url]):
            QMessageBox.warning(self, "Input Error", "Please fill in output folder and URL.")
            return

        if not os.path.isdir(output_directory):
            QMessageBox.warning(self, "Directory Error", "The selected folder is not valid.")
            return

        if frame_image_path and not os.path.isfile(frame_image_path):
            QMessageBox.warning(self, "File Error", "The selected shape image file is not valid.")
            return

        video_links = self.func(source_url)
        if not video_links:
            QMessageBox.information(self, "Error", "No videos found.")
            return

        reset_cache_stats()
        save_original_names(video_links, output_directory, output_format)
        self.cache_status_label.setText(get_cache_status_text())

        self.worker = WorkerThread(video_links, output_directory, frame_image_path, output_format)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.update_message.connect(self.progress_label.setText)
        self.worker.update_cache_status.connect(self.cache_status_label.setText)
        self.worker.start()

    def check_auth_status(self):
        input_url = self.channel_edit.text().strip()
        if not input_url:
            QMessageBox.warning(self, "Input Error", "Enter a YouTube URL first.")
            return

        ydl_opts = with_auth_opts({
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,
            'playlist_end': 1,
        })
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(input_url, download=False)
            self.progress_label.setText("Auth check passed.")
            QMessageBox.information(self, "Auth Status", "Authentication/runtime check passed.")
        except Exception as error:
            self.progress_label.setText(f"Auth check failed: {error}")
            QMessageBox.warning(
                self,
                "Auth Status",
                f"Authentication/runtime check failed:\n{error}\n\n"
                "Set COOKIES_FROM_BROWSER or COOKIES_FILE in config.ini and retry.",
            )

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f'{value}%')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.oldPosition = QPoint()  # Initialize oldPosition
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("YTSDownloader")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet(open(f"themes/{theme}/style.qss", "r").read())  # Load the PyDracula stylesheet  

        self.custom_title_bar = CustomTitleBar(self)
        self.setMenuWidget(self.custom_title_bar)  

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(open(f"themes/{theme}/style.qss", "r").read())
        self.layout.addWidget(self.tabs)

        self.tab1 = VideoDownloaderTab("YouTube (Channel / Video / Short)", get_video_links)
        self.tab2 = VideoDownloaderTab("Instagram (Profile / Post / Reel)", get_instagram_links)
        self.tab3 = VideoDownloaderTab("Facebook (Page / Post / Video)", get_facebook_links)
        self.tab4 = VideoDownloaderTab("TikTok (Profile / Video)", get_tiktok_links)
        self.tabs.addTab(self.tab1, "YouTube Downloader")
        self.tabs.addTab(self.tab2, "Instagram Downloader")
        self.tabs.addTab(self.tab3, "Facebook Downloader")
        self.tabs.addTab(self.tab4, "Tiktok Downloader")

    def process_videos(self, *args):
        short_links = get_video_links(*args)
        output_directory = self.tab1.folder_edit.text()
        frame_image_path = self.tab1.shape_edit.text()
        output_format = "mp4" if self.tab1.format_mp4.isChecked() else "webm"

        reset_cache_stats()
        save_original_names(short_links, output_directory, output_format)
        self.tab1.cache_status_label.setText(get_cache_status_text())

        self.worker = WorkerThread(short_links, output_directory, frame_image_path, output_format)
        self.worker.update_progress.connect(self.tab1.update_progress)
        self.worker.update_message.connect(self.tab1.progress_label.setText)
        self.worker.update_cache_status.connect(self.tab1.cache_status_label.setText)
        self.worker.start()

    def mousePressEvent(self, event):
        self.oldPosition = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPosition().toPoint() - self.oldPosition) 
        self.move(self.x() + delta.x(), self.y() + delta.y()) 
        self.oldPosition = event.globalPosition().toPoint()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    def cleanup_log_handlers():
        for handler in list(logger.handlers):
            if isinstance(handler, TextEditLogger):
                logger.removeHandler(handler)
                handler.close()
    app.aboutToQuit.connect(cleanup_log_handlers)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
