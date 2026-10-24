"""Suite main window: sidebar navigation, queue, download, metadata bridge."""

from __future__ import annotations

import os
import time
from typing import Dict, List, Optional, Set

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QMimeData, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QAction
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QLineEdit,
    QFileDialog,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QMessageBox,
    QRadioButton,
    QButtonGroup,
    QStatusBar,
    QComboBox,
    QPlainTextEdit,
    QFormLayout,
    QFrame,
    QSpinBox,
    QDoubleSpinBox,
    QScrollArea,
    QSplitter,
    QCheckBox,
    QMenu,
)

from ytscore.analytics import SessionAnalytics
from ytscore.cache import title_cache
from ytscore.companion import (
    consume_companion_inbox,
    default_inbox_dir,
    default_inbox_jsonl_path,
    ensure_inbox_layout,
)
from ytscore.crawl import (
    CRAWL_MODE_LABELS,
    CrawlAuthError,
    CrawlMode,
    clamp_crawl_limit,
    cookie_auth_configured,
    crawl_many,
    crawl_profile,
    crawl_requires_auth,
    parse_crawl_mode,
)
from ytscore.folder_dialog import get_existing_directory
from ytscore.native_bridge import clear_native_cache, native_status
from ytscore.persist import (
    default_queue_state_path,
    deserialize_queue_snapshot,
    load_queue_state,
    save_queue_state,
    serialize_queue_snapshot,
)
from ytscore.presets import (
    CUSTOM,
    ExportPreset,
    get_preset,
    list_presets,
    resolve_job_options,
)
from ytscore.queue import DownloadQueue, QueueJob, JobState
from ytscore.resolvers import auth_probe, detect_platform
from ytscore.settings import Settings, load_settings, save_settings, DEFAULT_CONFIG_PATH
from ytscore.triage import (
    category_label,
    classify_failure,
    failure_detail_text,
)
from ytscore.util import extract_urls
from ytscore import spotify_bridge
from ytsgui.styles import load_stylesheet


class QueueBridge(QObject):
    job_updated = pyqtSignal(object)


class UrlDropZone(QFrame):
    """Visual drop target that emits extracted http(s) URLs."""

    urls_dropped = pyqtSignal(list)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("urlDropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(88)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        title = QLabel("Drop URLs here")
        title.setObjectName("dropZoneTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel("Drag links from a browser, or drop a .txt / .url file")
        hint.setObjectName("dropZoneHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._mime_has_urls(event.mimeData()):
            event.acceptProposedAction()
            self.setProperty("dragOver", True)
            self.style().unpolish(self)
            self.style().polish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        urls = self._urls_from_mime(event.mimeData())
        if urls:
            event.acceptProposedAction()
            self.urls_dropped.emit(urls)
        else:
            event.ignore()

    @staticmethod
    def _mime_has_urls(mime: QMimeData) -> bool:
        if mime.hasUrls():
            return True
        if mime.hasText() and extract_urls(mime.text()):
            return True
        return False

    @staticmethod
    def _urls_from_mime(mime: QMimeData) -> List[str]:
        chunks: List[str] = []
        if mime.hasUrls():
            for qurl in mime.urls():
                local = qurl.toLocalFile()
                if local and os.path.isfile(local):
                    try:
                        with open(local, "r", encoding="utf-8", errors="ignore") as fh:
                            chunks.append(fh.read())
                    except OSError:
                        continue
                else:
                    chunks.append(qurl.toString())
        if mime.hasText():
            chunks.append(mime.text())
        found: List[str] = []
        seen = set()
        for chunk in chunks:
            for url in extract_urls(chunk):
                if url not in seen:
                    seen.add(url)
                    found.append(url)
        return found


class SuiteWindow(QMainWindow):
    def __init__(
        self,
        settings: Optional[Settings] = None,
        *,
        config_path: str = DEFAULT_CONFIG_PATH,
    ) -> None:
        super().__init__()
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.settings = settings or load_settings(self.config_path)
        self.setWindowTitle("YTSDownloader")
        self.resize(1120, 720)
        self.setStyleSheet(load_stylesheet(self.settings.theme))

        self.queue: Optional[DownloadQueue] = None
        self._bridge = QueueBridge()
        self._bridge.job_updated.connect(self._on_job_updated)
        self._job_rows = {}
        self._queue_state_path = default_queue_state_path()
        self._persist_enabled = True
        self._companion_inbox_dir = default_inbox_dir()
        self._companion_inbox_jsonl = default_inbox_jsonl_path()
        ensure_inbox_layout(
            inbox_dir=self._companion_inbox_dir,
            jsonl_path=self._companion_inbox_jsonl,
        )
        self.session_analytics = SessionAnalytics()
        self._analytics_started: Dict[str, float] = {}
        self._analytics_counted: Set[str] = set()

        root = QWidget()
        root.setObjectName("centralRoot")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("contentPane")
        layout.addWidget(self.stack, stretch=1)

        self.page_download = self._build_download_page()
        self.page_queue = self._build_queue_page()
        self.page_grabber = self._build_grabber_page()
        self.page_spotify = self._build_spotify_page()
        self.page_settings = self._build_settings_page()

        for page in (
            self.page_download,
            self.page_queue,
            self.page_grabber,
            self.page_spotify,
            self.page_settings,
        ):
            self.stack.addWidget(page)

        self.status = QStatusBar()
        self.analytics_label = QLabel("")
        self.analytics_label.setObjectName("statusAnalytics")
        self.status.addPermanentWidget(self.analytics_label)
        self.setStatusBar(self.status)
        self._refresh_analytics_label()
        self._refresh_status("Ready")

        self._nav_buttons[0].setChecked(True)
        self._set_page(0)

        self._persist_timer = QTimer(self)
        self._persist_timer.setSingleShot(True)
        self._persist_timer.setInterval(400)
        self._persist_timer.timeout.connect(self._persist_queue_now)

        self._spotify_timer = QTimer(self)
        self._spotify_timer.setInterval(2000)
        self._spotify_timer.timeout.connect(self._poll_spotify_session)
        self._spotify_timer.start()
        self._poll_spotify_session()

        self._companion_timer = QTimer(self)
        self._companion_timer.setInterval(1500)
        self._companion_timer.timeout.connect(self._poll_companion_inbox)
        self._companion_timer.start()

        self._restore_queue_from_disk()

    # ----- sidebar -----
    def _build_sidebar(self) -> QWidget:
        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(220)
        v = QVBoxLayout(side)
        v.setContentsMargins(8, 8, 8, 8)
        brand = QLabel("YTSDownloader")
        brand.setObjectName("brandTitle")
        sub = QLabel("VoxHash Suite")
        sub.setObjectName("brandSub")
        v.addWidget(brand)
        v.addWidget(sub)

        self._nav_buttons = []
        labels = ["Download", "Queue", "Link Grabber", "Metadata Bridge", "Settings"]
        for i, text in enumerate(labels):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setProperty("class", "navBtn")
            btn.setStyleSheet("")  # use QSS via class — PyQt needs setProperty + polish
            btn.setObjectName("navBtn")
            btn.setProperty("class", "navBtn")
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding: 10px 16px; border: none; "
                "border-radius: 4px; background: transparent; color: #b3b3b3; font-weight: 600; }"
                "QPushButton:hover { color: #fff; background: #181818; }"
                "QPushButton:checked { color: #fff; background: #282828; }"
            )
            btn.clicked.connect(lambda checked, idx=i: self._set_page(idx))
            v.addWidget(btn)
            self._nav_buttons.append(btn)
        v.addStretch(1)
        return side

    def _set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

    # ----- download page -----
    def _build_download_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Download")
        title.setObjectName("pageTitle")
        hint = QLabel(
            "Paste or drop a video, playlist, channel, or profile URL. "
            "Companions can also write URLs into .ytsdownloader/inbox/. "
            "Deep crawl modes need cookie auth (Brave profile or cookie file) "
            "and only enumerate content your session can already reach."
        )
        hint.setObjectName("pageHint")
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)

        self.url_drop_zone = UrlDropZone()
        self.url_drop_zone.urls_dropped.connect(self._on_urls_dropped)
        layout.addWidget(self.url_drop_zone)

        form = QFormLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://…")
        self.url_edit.setAcceptDrops(True)
        self.out_edit = QLineEdit(self.settings.default_output or os.path.expanduser("~/Downloads/YTSDownloader"))
        out_btn = QPushButton("Browse")
        out_btn.setProperty("class", "secondary")
        out_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #fff; border: 1px solid #727272; border-radius: 20px; }"
        )
        out_btn.clicked.connect(self._browse_out)
        out_row = QHBoxLayout()
        out_row.addWidget(self.out_edit, stretch=1)
        out_row.addWidget(out_btn)

        self.wm_edit = QLineEdit()
        wm_btn = QPushButton("Browse")
        wm_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #fff; border: 1px solid #727272; border-radius: 20px; }"
        )
        wm_btn.clicked.connect(self._browse_wm)
        wm_row = QHBoxLayout()
        wm_row.addWidget(self.wm_edit, stretch=1)
        wm_row.addWidget(wm_btn)

        self.media_video = QRadioButton("Video")
        self.media_audio = QRadioButton("Audio")
        self.media_video.setChecked(True)
        media_group = QButtonGroup(page)
        media_group.addButton(self.media_video)
        media_group.addButton(self.media_audio)
        media_row = QHBoxLayout()
        media_row.addWidget(self.media_video)
        media_row.addWidget(self.media_audio)
        media_row.addStretch(1)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "webm", "mkv"])

        self.preset_combo = QComboBox()
        for preset in list_presets(include_custom=True):
            self.preset_combo.addItem(preset.name, preset.id)
        # Default: Video + audio
        idx_va = self.preset_combo.findData("video_audio")
        if idx_va >= 0:
            self.preset_combo.setCurrentIndex(idx_va)
        self.preset_combo.currentIndexChanged.connect(self._on_download_preset_changed)
        self.preset_hint = QLabel("")
        self.preset_hint.setObjectName("pageHint")
        self.preset_hint.setWordWrap(True)

        self.crawl_mode_combo = QComboBox()
        for mode in CrawlMode:
            self.crawl_mode_combo.addItem(CRAWL_MODE_LABELS[mode], mode.value)
        self.crawl_mode_combo.setCurrentIndex(0)
        self.crawl_mode_combo.currentIndexChanged.connect(self._refresh_crawl_auth_hint)
        self.crawl_limit_spin = QSpinBox()
        self.crawl_limit_spin.setRange(1, 500)
        self.crawl_limit_spin.setValue(50)
        self.crawl_limit_spin.setToolTip(
            "Max items to enqueue from a profile / channel crawl (1–500)."
        )
        crawl_row = QHBoxLayout()
        crawl_row.addWidget(self.crawl_mode_combo, stretch=2)
        crawl_row.addWidget(QLabel("Limit"))
        crawl_row.addWidget(self.crawl_limit_spin)
        crawl_row.addStretch(1)
        self.crawl_auth_hint = QLabel("")
        self.crawl_auth_hint.setObjectName("pageHint")
        self.crawl_auth_hint.setWordWrap(True)

        form.addRow("URL", self.url_edit)
        form.addRow("Output", out_row)
        form.addRow("Export preset", self.preset_combo)
        form.addRow("", self.preset_hint)
        form.addRow("Crawl mode", crawl_row)
        form.addRow("", self.crawl_auth_hint)
        form.addRow("Watermark PNG", wm_row)
        form.addRow("Media", media_row)
        form.addRow("Container", self.format_combo)
        layout.addLayout(form)
        self._apply_preset_to_download_form(self._selected_download_preset(), announce=False)
        self._refresh_crawl_auth_hint()

        actions = QHBoxLayout()
        resolve_btn = QPushButton("Resolve & Queue")
        resolve_btn.clicked.connect(self._resolve_and_queue)
        auth_btn = QPushButton("Check Auth")
        auth_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #fff; border: 1px solid #727272; border-radius: 20px; }"
        )
        auth_btn.clicked.connect(self._check_auth)
        start_btn = QPushButton("Start Queue")
        start_btn.clicked.connect(self._start_queue)
        actions.addWidget(resolve_btn)
        actions.addWidget(auth_btn)
        actions.addWidget(start_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.download_log = QTextEdit()
        self.download_log.setReadOnly(True)
        layout.addWidget(self.download_log, stretch=1)
        self.cache_label = QLabel(title_cache.status_text())
        layout.addWidget(self.cache_label)
        return page

    # ----- queue page -----
    def _build_queue_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Queue")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        hint = QLabel(
            "Concurrent workers, per-item progress, automatic retries. "
            "Queue is saved locally and restored on startup (pending items stay paused — press Start). "
            "Select a failed row for triage detail, then Retry selected / Retry failed."
        )
        hint.setObjectName("pageHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("State"))
        self.queue_state_filter = QComboBox()
        self.queue_state_filter.addItem("All", "")
        for state in JobState:
            self.queue_state_filter.addItem(state.value.capitalize(), state.value)
        self.queue_state_filter.currentIndexChanged.connect(self._apply_queue_filters)
        filter_row.addWidget(self.queue_state_filter)

        filter_row.addWidget(QLabel("Search"))
        self.queue_search_filter = QLineEdit()
        self.queue_search_filter.setPlaceholderText("Title, URL, or message…")
        self.queue_search_filter.setClearButtonEnabled(True)
        self.queue_search_filter.textChanged.connect(self._apply_queue_filters)
        filter_row.addWidget(self.queue_search_filter, stretch=1)

        self.queue_filter_count = QLabel("")
        self.queue_filter_count.setObjectName("pageHint")
        filter_row.addWidget(self.queue_filter_count)
        layout.addLayout(filter_row)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Export preset"))
        self.queue_preset_combo = QComboBox()
        for preset in list_presets(include_custom=False):
            self.queue_preset_combo.addItem(preset.name, preset.id)
        preset_row.addWidget(self.queue_preset_combo)
        apply_sel = QPushButton("Apply to selected")
        apply_sel.setStyleSheet(
            "QPushButton { background: transparent; color: #fff; border: 1px solid #727272; border-radius: 20px; }"
        )
        apply_sel.clicked.connect(self._apply_preset_to_selected)
        apply_queued = QPushButton("Apply to queued")
        apply_queued.setStyleSheet(
            "QPushButton { background: transparent; color: #fff; border: 1px solid #727272; border-radius: 20px; }"
        )
        apply_queued.clicked.connect(self._apply_preset_to_queued)
        preset_row.addWidget(apply_sel)
        preset_row.addWidget(apply_queued)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        self.queue_table = QTableWidget(0, 6)
        self.queue_table.setHorizontalHeaderLabels(
            ["#", "Title / URL", "State", "Export", "Progress", "Message"]
        )
        self.queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.queue_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_table.customContextMenuRequested.connect(self._queue_table_context_menu)
        self.queue_table.itemSelectionChanged.connect(self._refresh_failure_triage)
        splitter.addWidget(self.queue_table)

        triage = QFrame()
        triage.setObjectName("failureTriagePanel")
        triage_layout = QVBoxLayout(triage)
        triage_layout.setContentsMargins(12, 10, 12, 10)
        triage_layout.setSpacing(6)

        triage_header = QHBoxLayout()
        triage_title = QLabel("Failure triage")
        triage_title.setObjectName("triageTitle")
        triage_header.addWidget(triage_title)
        self.triage_category = QLabel("Category: —")
        self.triage_category.setObjectName("triageCategory")
        triage_header.addWidget(self.triage_category)
        triage_header.addStretch(1)
        triage_layout.addLayout(triage_header)

        self.triage_detail = QPlainTextEdit()
        self.triage_detail.setReadOnly(True)
        self.triage_detail.setPlaceholderText(
            "Select a failed (or cancelled) queue row to inspect error detail."
        )
        self.triage_detail.setMaximumBlockCount(200)
        self.triage_detail.setMinimumHeight(96)
        triage_layout.addWidget(self.triage_detail)

        triage_actions = QHBoxLayout()
        retry_sel = QPushButton("Retry selected")
        retry_sel.clicked.connect(self._retry_selected_jobs)
        retry_failed = QPushButton("Retry failed")
        retry_failed.setStyleSheet(
            "QPushButton { background: transparent; color: #fff; border: 1px solid #727272; border-radius: 20px; }"
        )
        retry_failed.clicked.connect(self._retry_failed_jobs)
        triage_actions.addWidget(retry_sel)
        triage_actions.addWidget(retry_failed)
        triage_actions.addStretch(1)
        triage_layout.addLayout(triage_actions)
        splitter.addWidget(triage)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([420, 180])
        layout.addWidget(splitter, stretch=1)

        self.overall_progress = QProgressBar()
        self.overall_progress.setValue(0)
        layout.addWidget(self.overall_progress)

        row = QHBoxLayout()
        start = QPushButton("Start")
        start.clicked.connect(self._start_queue)
        stop = QPushButton("Stop")
        stop.setStyleSheet(
            "QPushButton { background: transparent; color: #fff; border: 1px solid #727272; border-radius: 20px; }"
        )
        stop.clicked.connect(self._stop_queue)
        clear = QPushButton("Clear Finished")
        clear.setStyleSheet(
            "QPushButton { background: transparent; color: #fff; border: 1px solid #727272; border-radius: 20px; }"
        )
        clear.clicked.connect(self._clear_finished)
        clear_all = QPushButton("Clear All")
        clear_all.setStyleSheet(
            "QPushButton { background: transparent; color: #fff; border: 1px solid #727272; border-radius: 20px; }"
        )
        clear_all.clicked.connect(self._clear_all_queue)
        row.addWidget(start)
        row.addWidget(stop)
        row.addWidget(clear)
        row.addWidget(clear_all)
        row.addStretch(1)
        layout.addLayout(row)
        self._refresh_failure_triage()
        return page

    # ----- link grabber -----
    def _build_grabber_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Link Grabber")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        hint = QLabel("Paste many URLs (one per line). Filters empty lines and comments.")
        hint.setObjectName("pageHint")
        layout.addWidget(hint)
        self.grabber_text = QPlainTextEdit()
        self.grabber_text.setPlaceholderText("https://…\nhttps://…")
        layout.addWidget(self.grabber_text, stretch=1)
        btn = QPushButton("Resolve All → Queue")
        btn.clicked.connect(self._grabber_queue)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)
        return page

    # ----- spotify / metadata bridge -----
    def _build_spotify_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Metadata Bridge")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        hint = QLabel(
            "Uses the open Spotify desktop session (MPRIS) or a catalog URL. "
            "Matches public media hosts and queues audio downloads — does not rip Spotify streams."
        )
        hint.setObjectName("pageHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.spotify_status = QLabel("Session: checking…")
        layout.addWidget(self.spotify_status)
        self.spotify_now = QLabel("Now playing: —")
        self.spotify_now.setWordWrap(True)
        layout.addWidget(self.spotify_now)

        form = QFormLayout()
        self.spotify_url = QLineEdit()
        self.spotify_url.setPlaceholderText("https://open.spotify.com/track/… or playlist/album")
        form.addRow("Catalog URL", self.spotify_url)
        layout.addLayout(form)

        row = QHBoxLayout()
        capture = QPushButton("Queue Now Playing")
        capture.clicked.connect(self._queue_now_playing)
        resolve = QPushButton("Resolve URL → Queue")
        resolve.clicked.connect(self._queue_spotify_url)
        row.addWidget(capture)
        row.addWidget(resolve)
        row.addStretch(1)
        layout.addLayout(row)

        self.spotify_log = QTextEdit()
        self.spotify_log.setReadOnly(True)
        layout.addWidget(self.spotify_log, stretch=1)
        return page

    # ----- settings -----
    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        hint = QLabel(
            "Edit values below and Save to write config.ini. "
            "Pace, backoff, cookies, formats, retries, and status analytics "
            "apply immediately; worker count applies on the next Start Queue. "
            "Analytics counters are local/session only (no network telemetry)."
        )
        hint.setObjectName("pageHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_host = QWidget()
        form = QFormLayout(form_host)
        form.setContentsMargins(0, 8, 12, 8)
        form.setSpacing(10)

        self.settings_theme = QComboBox()
        self.settings_theme.setEditable(True)
        for name in self._theme_names():
            self.settings_theme.addItem(name)

        self.settings_cookies_browser = QLineEdit()
        self.settings_cookies_browser.setPlaceholderText("brave:Default")
        self.settings_cookies_file = QLineEdit()
        cookies_row = QHBoxLayout()
        cookies_row.addWidget(self.settings_cookies_file, stretch=1)
        cookies_browse = QPushButton("Browse…")
        cookies_browse.clicked.connect(self._browse_cookies_file)
        cookies_row.addWidget(cookies_browse)

        self.settings_js_runtime = QLineEdit()
        self.settings_js_runtime.setPlaceholderText("node")
        self.settings_js_path = QLineEdit()
        self.settings_js_path.setPlaceholderText("optional absolute path")

        self.settings_max_workers = QSpinBox()
        self.settings_max_workers.setRange(1, 32)
        self.settings_max_retries = QSpinBox()
        self.settings_max_retries.setRange(0, 20)

        self.settings_pace = QDoubleSpinBox()
        self.settings_pace.setRange(0.0, 600.0)
        self.settings_pace.setDecimals(2)
        self.settings_pace.setSingleStep(0.5)
        self.settings_pace.setSuffix(" s")

        self.settings_backoff_base = QDoubleSpinBox()
        self.settings_backoff_base.setRange(0.0, 600.0)
        self.settings_backoff_base.setDecimals(2)
        self.settings_backoff_factor = QDoubleSpinBox()
        self.settings_backoff_factor.setRange(1.0, 16.0)
        self.settings_backoff_factor.setDecimals(2)
        self.settings_backoff_max = QDoubleSpinBox()
        self.settings_backoff_max.setRange(0.0, 3600.0)
        self.settings_backoff_max.setDecimals(1)
        self.settings_backoff_max.setSuffix(" s")

        self.settings_audio_format = QLineEdit()
        self.settings_video_format = QLineEdit()
        self.settings_default_output = QLineEdit()
        out_row = QHBoxLayout()
        out_row.addWidget(self.settings_default_output, stretch=1)
        out_browse = QPushButton("Browse…")
        out_browse.clicked.connect(self._browse_default_output)
        out_row.addWidget(out_browse)

        self.settings_show_analytics = QCheckBox("Show analytics in status bar")
        self.settings_show_analytics.setToolTip(
            "Local session success / error / timing counters only — nothing is sent over the network."
        )
        self.settings_process_nice = QSpinBox()
        self.settings_process_nice.setRange(0, 19)
        self.settings_process_nice.setToolTip(
            "CPU nice when Start Queue runs (0 = unchanged). Higher = more polite to other apps."
        )
        self.settings_process_idle_io = QCheckBox("Idle I/O priority on Start Queue")
        self.settings_process_idle_io.setToolTip(
            "Linux ionice idle class so downloads yield disk bandwidth to interactive apps. "
            "Uses native yts-prio when built; otherwise ionice CLI / no-op."
        )

        form.addRow("Theme", self.settings_theme)
        form.addRow("Cookies from browser", self.settings_cookies_browser)
        form.addRow("Cookies file", cookies_row)
        form.addRow("JS runtime", self.settings_js_runtime)
        form.addRow("JS runtime path", self.settings_js_path)
        form.addRow("Max workers", self.settings_max_workers)
        form.addRow("Max retries", self.settings_max_retries)
        form.addRow("Playlist pace", self.settings_pace)
        form.addRow("Backoff base (s)", self.settings_backoff_base)
        form.addRow("Backoff factor", self.settings_backoff_factor)
        form.addRow("Backoff max", self.settings_backoff_max)
        form.addRow("Audio format", self.settings_audio_format)
        form.addRow("Video format", self.settings_video_format)
        form.addRow("Default output", out_row)
        form.addRow("Status analytics", self.settings_show_analytics)
        form.addRow("Process nice", self.settings_process_nice)
        form.addRow("Disk priority", self.settings_process_idle_io)

        native_panel = self._build_native_status_panel()
        form.addRow(native_panel)

        scroll.setWidget(form_host)
        layout.addWidget(scroll, stretch=1)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save to config.ini")
        save_btn.clicked.connect(self._save_settings)
        reload_btn = QPushButton("Reload config.ini")
        reload_btn.clicked.connect(self._reload_settings)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(reload_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self._fill_settings_form(self.settings)
        self._refresh_native_status()
        return page

    def _build_native_status_panel(self) -> QFrame:
        """Read-only discovery snapshot for optional native sidecars."""
        panel = QFrame()
        panel.setObjectName("nativeStatusPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Native helpers")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("nativeStatusRefresh")
        refresh_btn.setToolTip(
            "Re-scan native/bin (and YTS_NATIVE_DIR) after building sidecars."
        )
        refresh_btn.clicked.connect(self._on_refresh_native_status)
        header.addWidget(refresh_btn)
        panel_layout.addLayout(header)

        hint = QLabel(
            "Optional sidecars speed up normalize, process priority, companion inbox, "
            "and JSON filtering. Missing or disabled helpers fall back to Python "
            "automatically — nothing fails hard."
        )
        hint.setObjectName("nativeStatusHint")
        hint.setWordWrap(True)
        panel_layout.addWidget(hint)

        status_form = QFormLayout()
        status_form.setContentsMargins(0, 4, 0, 0)
        status_form.setSpacing(6)

        self.native_status_enabled = QLabel("—")
        self.native_status_enabled.setObjectName("nativeStatusValue")
        self.native_status_enabled.setWordWrap(True)
        self.native_status_bin_dir = QLabel("—")
        self.native_status_bin_dir.setObjectName("nativeStatusValue")
        self.native_status_bin_dir.setWordWrap(True)
        self.native_status_bin_dir.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.native_status_normalize = QLabel("—")
        self.native_status_normalize.setObjectName("nativeStatusValue")
        self.native_status_normalize.setWordWrap(True)
        self.native_status_normalize.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.native_status_prio = QLabel("—")
        self.native_status_prio.setObjectName("nativeStatusValue")
        self.native_status_prio.setWordWrap(True)
        self.native_status_prio.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.native_status_inbox = QLabel("—")
        self.native_status_inbox.setObjectName("nativeStatusValue")
        self.native_status_inbox.setWordWrap(True)
        self.native_status_inbox.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.native_status_ruby = QLabel("—")
        self.native_status_ruby.setObjectName("nativeStatusValue")
        self.native_status_ruby.setWordWrap(True)
        self.native_status_ruby.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        status_form.addRow("YTS_USE_NATIVE", self.native_status_enabled)
        status_form.addRow("Search directory", self.native_status_bin_dir)
        status_form.addRow("Normalize (Rust)", self.native_status_normalize)
        status_form.addRow("Priority (C / zig cc)", self.native_status_prio)
        status_form.addRow("Inbox (Go)", self.native_status_inbox)
        status_form.addRow("JSON filter (Ruby)", self.native_status_ruby)
        panel_layout.addLayout(status_form)
        return panel

    def _on_refresh_native_status(self) -> None:
        clear_native_cache()
        self._refresh_native_status()
        self._refresh_status("Native helper discovery refreshed")

    @staticmethod
    def _format_native_sidecar(path: Optional[str], *, enabled: bool) -> str:
        if not enabled:
            return "Skipped — natives disabled (Python fallback)"
        if path:
            return path
        return "Not found — using Python fallback"

    def _refresh_native_status(self) -> None:
        if not hasattr(self, "native_status_enabled"):
            return
        status = native_status()
        enabled = bool(status.get("enabled"))
        if enabled:
            self.native_status_enabled.setText("Enabled (set YTS_USE_NATIVE=0 to disable)")
        else:
            self.native_status_enabled.setText(
                "Disabled — Python fallbacks only (YTS_USE_NATIVE is off)"
            )
        bin_dir = str(status.get("bin_dir") or "").strip() or "(none)"
        self.native_status_bin_dir.setText(bin_dir)
        self.native_status_normalize.setText(
            self._format_native_sidecar(status.get("normalize"), enabled=enabled)
        )
        self.native_status_prio.setText(
            self._format_native_sidecar(status.get("prio"), enabled=enabled)
        )
        self.native_status_inbox.setText(
            self._format_native_sidecar(status.get("inbox"), enabled=enabled)
        )
        self.native_status_ruby.setText(
            self._format_native_sidecar(status.get("ruby_filter"), enabled=enabled)
        )

    @staticmethod
    def _theme_names() -> List[str]:
        themes_dir = "themes"
        names: List[str] = []
        if os.path.isdir(themes_dir):
            for entry in sorted(os.listdir(themes_dir)):
                path = os.path.join(themes_dir, entry)
                if os.path.isdir(path) and not entry.startswith("."):
                    names.append(entry)
        if "SuiteDark" not in names:
            names.insert(0, "SuiteDark")
        return names

    def _fill_settings_form(self, settings: Settings) -> None:
        theme = settings.theme or "SuiteDark"
        idx = self.settings_theme.findText(theme)
        if idx >= 0:
            self.settings_theme.setCurrentIndex(idx)
        else:
            self.settings_theme.setEditText(theme)
        self.settings_cookies_browser.setText(settings.cookies_from_browser or "")
        self.settings_cookies_file.setText(settings.cookies_file or "")
        self.settings_js_runtime.setText(settings.js_runtime or "")
        self.settings_js_path.setText(settings.js_runtime_path or "")
        self.settings_max_workers.setValue(max(1, int(settings.max_workers)))
        self.settings_max_retries.setValue(max(0, int(settings.max_retries)))
        self.settings_pace.setValue(float(settings.pace_seconds))
        self.settings_backoff_base.setValue(float(settings.backoff_base))
        self.settings_backoff_factor.setValue(float(settings.backoff_factor))
        self.settings_backoff_max.setValue(float(settings.backoff_max))
        self.settings_audio_format.setText(settings.audio_format or "m4a")
        self.settings_video_format.setText(
            settings.video_format_pref or "bestvideo+bestaudio/best"
        )
        self.settings_default_output.setText(settings.default_output or "")
        self.settings_show_analytics.setChecked(bool(settings.show_status_analytics))
        self.settings_process_nice.setValue(max(0, min(19, int(settings.process_nice))))
        self.settings_process_idle_io.setChecked(bool(settings.process_idle_io))

    def _settings_from_form(self) -> Settings:
        return Settings(
            theme=self.settings_theme.currentText().strip() or "SuiteDark",
            cookies_from_browser=self.settings_cookies_browser.text().strip(),
            cookies_file=self.settings_cookies_file.text().strip(),
            js_runtime=self.settings_js_runtime.text().strip(),
            js_runtime_path=self.settings_js_path.text().strip(),
            max_workers=int(self.settings_max_workers.value()),
            max_retries=int(self.settings_max_retries.value()),
            pace_seconds=float(self.settings_pace.value()),
            backoff_base=float(self.settings_backoff_base.value()),
            backoff_factor=float(self.settings_backoff_factor.value()),
            backoff_max=float(self.settings_backoff_max.value()),
            audio_format=self.settings_audio_format.text().strip() or "m4a",
            video_format_pref=(
                self.settings_video_format.text().strip() or "bestvideo+bestaudio/best"
            ),
            default_output=self.settings_default_output.text().strip(),
            show_status_analytics=self.settings_show_analytics.isChecked(),
            process_nice=int(self.settings_process_nice.value()),
            process_idle_io=self.settings_process_idle_io.isChecked(),
        )

    def _browse_cookies_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Cookie file",
            "",
            "Cookies (*.txt *.json);;All files (*)",
        )
        if path:
            self.settings_cookies_file.setText(path)

    def _browse_default_output(self) -> None:
        start = self.settings_default_output.text().strip() or os.path.expanduser("~")
        folder = get_existing_directory(self, "Default output folder", start)
        if folder:
            self.settings_default_output.setText(folder)

    def _apply_settings_runtime(self, settings: Settings) -> None:
        """Push settings into the running Suite (queue/pacing/cookies without full restart)."""
        self.settings = settings
        self.setStyleSheet(load_stylesheet(self.settings.theme))
        if self.queue is not None:
            self.queue.settings = self.settings
        default_out = (settings.default_output or "").strip()
        if default_out and hasattr(self, "out_edit"):
            current = self.out_edit.text().strip()
            # Only seed Download page output when empty or still matching prior default.
            if not current or current == os.path.expanduser("~/Downloads/YTSDownloader"):
                self.out_edit.setText(default_out)
        self._refresh_analytics_label()
        self._refresh_crawl_auth_hint()

    # ----- helpers -----
    def _browse_out(self) -> None:
        start = self.out_edit.text().strip() or os.path.expanduser("~")
        folder = get_existing_directory(self, "Select output folder", start)
        if folder:
            self.out_edit.setText(folder)

    def _browse_wm(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Watermark PNG", "", "PNG (*.png)")
        if path:
            self.wm_edit.setText(path)

    def _selected_download_preset(self) -> ExportPreset:
        pid = self.preset_combo.currentData() if hasattr(self, "preset_combo") else "video_audio"
        return get_preset(str(pid or "video_audio")) or get_preset("video_audio") or CUSTOM

    def _selected_crawl_mode(self) -> CrawlMode:
        if not hasattr(self, "crawl_mode_combo"):
            return CrawlMode.SHALLOW
        raw = self.crawl_mode_combo.currentData()
        try:
            return parse_crawl_mode(str(raw or CrawlMode.SHALLOW.value))
        except ValueError:
            return CrawlMode.SHALLOW

    def _crawl_limit(self) -> int:
        if not hasattr(self, "crawl_limit_spin"):
            return 50
        return clamp_crawl_limit(self.crawl_limit_spin.value())

    def _refresh_crawl_auth_hint(self) -> None:
        if not hasattr(self, "crawl_auth_hint"):
            return
        mode = self._selected_crawl_mode()
        auth_ok = cookie_auth_configured(self.settings)
        if not crawl_requires_auth(mode):
            self.crawl_auth_hint.setText(
                "Shallow mode: single-pass resolve (cookies optional)."
            )
            return
        if auth_ok:
            src = (self.settings.cookies_from_browser or "").strip() or "cookie file"
            self.crawl_auth_hint.setText(
                f"Cookie auth ready ({src}). Deep crawl paces tab fetches; "
                "only public/authorized surfaces your session can reach."
            )
        else:
            self.crawl_auth_hint.setText(
                "Deep crawl needs cookie auth — set Cookies from browser "
                "(e.g. brave:Default) or Cookies file in Settings."
            )

    def _on_download_preset_changed(self) -> None:
        self._apply_preset_to_download_form(self._selected_download_preset(), announce=True)

    def _apply_preset_to_download_form(self, preset: ExportPreset, *, announce: bool = True) -> None:
        self.preset_hint.setText(preset.description)
        if preset.id == CUSTOM.id:
            if announce:
                self._refresh_status("Export preset: Custom (manual media / watermark)")
            return
        if preset.media == "audio":
            self.media_audio.setChecked(True)
        else:
            self.media_video.setChecked(True)
        if preset.media == "video" and preset.output_format in ("mp4", "webm", "mkv"):
            idx = self.format_combo.findText(preset.output_format)
            if idx >= 0:
                self.format_combo.setCurrentIndex(idx)
        if announce:
            self._refresh_status(f"Export preset: {preset.name}")

    def _current_enqueue_options(self) -> dict:
        """Resolve media / watermark / container from the Download preset + form."""
        preset = self._selected_download_preset()
        media_override = "audio" if self.media_audio.isChecked() else "video"
        return resolve_job_options(
            preset,
            watermark_path=self.wm_edit.text().strip(),
            output_format=self.format_combo.currentText(),
            media_override=media_override,
        )

    def _job_export_label(self, job: QueueJob) -> str:
        media = job.media or "video"
        if media == "search_audio":
            return "search audio"
        if media == "audio":
            return "audio"
        wm = job.watermark_path
        if wm is None:
            wm = self.queue.watermark_path if self.queue else ""
        if wm:
            return "video+wm"
        return "video"

    def _selected_queue_job_ids(self) -> List[str]:
        ids: List[str] = []
        seen = set()
        for idx in self.queue_table.selectionModel().selectedRows():
            row = idx.row()
            for jid, r in self._job_rows.items():
                if r == row and jid not in seen:
                    ids.append(jid)
                    seen.add(jid)
                    break
        return ids

    def _refresh_failure_triage(self) -> None:
        if not hasattr(self, "triage_detail"):
            return
        ids = self._selected_queue_job_ids()
        if not ids or not self.queue:
            self.triage_category.setText("Category: —")
            self.triage_detail.setPlainText("")
            return
        # Prefer the first selected failed/cancelled job; else first selection.
        jobs = [self.queue.get(jid) for jid in ids]
        jobs = [j for j in jobs if j is not None]
        if not jobs:
            self.triage_category.setText("Category: —")
            self.triage_detail.setPlainText("")
            return
        preferred = next(
            (j for j in jobs if j.state in (JobState.FAILED, JobState.CANCELLED)),
            jobs[0],
        )
        raw = (preferred.error or preferred.message or "").strip()
        if preferred.state == JobState.FAILED or preferred.error:
            cat = classify_failure(raw)
            self.triage_category.setText(f"Category: {category_label(cat)}")
        elif preferred.state == JobState.CANCELLED:
            self.triage_category.setText("Category: Cancelled")
        else:
            self.triage_category.setText(f"Category: — ({preferred.state.value})")
        self.triage_detail.setPlainText(
            failure_detail_text(
                title=preferred.title or "",
                url=preferred.url or "",
                state=preferred.state.value,
                error=preferred.error,
                message=preferred.message or "",
            )
        )

    def _retry_selected_jobs(self) -> None:
        if not self.queue:
            QMessageBox.information(self, "Queue", "Queue is empty.")
            return
        ids = self._selected_queue_job_ids()
        if not ids:
            QMessageBox.information(self, "Retry", "Select one or more failed / cancelled rows.")
            return
        n = self.queue.retry_jobs(ids)
        self._persist_queue_now()
        self._refresh_failure_triage()
        self._update_overall()
        if n == 0:
            QMessageBox.information(
                self,
                "Retry",
                "No selected items were failed or cancelled.",
            )
            return
        if self.queue.is_running:
            self._refresh_status(f"Re-queued {n} selected item(s) for retry")
        else:
            self._refresh_status(
                f"Re-queued {n} selected item(s) — press Start to download"
            )

    def _retry_failed_jobs(self) -> None:
        if not self.queue:
            QMessageBox.information(self, "Queue", "Queue is empty.")
            return
        n = self.queue.retry_failed()
        self._persist_queue_now()
        self._refresh_failure_triage()
        self._update_overall()
        if n == 0:
            QMessageBox.information(self, "Retry", "No failed items to retry.")
            return
        if self.queue.is_running:
            self._refresh_status(f"Re-queued {n} failed item(s)")
        else:
            self._refresh_status(
                f"Re-queued {n} failed item(s) — press Start to download"
            )

    def _apply_preset_to_jobs(self, job_ids: Optional[List[str]], *, only_queued: bool) -> None:
        if not self.queue:
            QMessageBox.information(self, "Queue", "Queue is empty.")
            return
        pid = self.queue_preset_combo.currentData()
        preset = get_preset(str(pid or ""))
        if not preset or preset.id == CUSTOM.id:
            QMessageBox.information(self, "Preset", "Choose Audio only, Video + audio, or Watermark.")
            return
        wm = self.wm_edit.text().strip()
        if preset.use_watermark and not wm:
            QMessageBox.warning(
                self,
                "Preset",
                "Watermark preset needs a PNG path on the Download page.",
            )
            return
        opts = resolve_job_options(
            preset,
            watermark_path=wm,
            output_format=self.format_combo.currentText() or preset.output_format,
        )
        only_states = [JobState.QUEUED] if only_queued else None
        n = self.queue.apply_export_options(
            job_ids,
            media=opts["media"],
            watermark_path=opts["watermark_path"],
            output_format=opts["output_format"],
            only_states=only_states,
        )
        # Keep queue-level defaults aligned with last applied batch preset for new jobs.
        if opts["media"] == "video":
            self.queue.watermark_path = opts["watermark_path"]
            self.queue.output_format = opts["output_format"] or self.queue.output_format
        self._persist_queue_now()
        target = "queued" if only_queued else ("selected" if job_ids is not None else "all")
        self._refresh_status(f"Applied {preset.name} to {n} {target} item(s)")
        if n == 0:
            QMessageBox.information(
                self,
                "Preset",
                "No matching items updated (search-audio jobs are skipped).",
            )

    def _apply_preset_to_selected(self) -> None:
        ids = self._selected_queue_job_ids()
        if not ids:
            QMessageBox.information(self, "Preset", "Select one or more queue rows first.")
            return
        self._apply_preset_to_jobs(ids, only_queued=False)

    def _apply_preset_to_queued(self) -> None:
        self._apply_preset_to_jobs(None, only_queued=True)

    def _poll_companion_inbox(self) -> None:
        """Accept URLs written by a browser companion into the local inbox."""
        try:
            items = consume_companion_inbox(
                inbox_dir=self._companion_inbox_dir,
                jsonl_path=self._companion_inbox_jsonl,
            )
        except Exception as exc:
            self.download_log.append(f"Companion inbox error: {exc}")
            return
        if not items:
            return
        urls = [item.url for item in items]
        titled = sum(1 for item in items if item.title)
        self.download_log.append(
            f"Companion handoff: {len(urls)} URL(s)"
            + (f" ({titled} with title)" if titled else "")
        )
        self._on_urls_dropped(urls)

    def _on_urls_dropped(self, urls: List[str]) -> None:
        if not urls:
            return
        self._set_page(0)
        self._nav_buttons[0].setChecked(True)
        if len(urls) == 1:
            self.url_edit.setText(urls[0])
            self.download_log.append(f"Dropped URL: {urls[0]}")
            self._refresh_status("Dropped 1 URL — Resolve & Queue when ready")
            return
        self.grabber_text.setPlainText("\n".join(urls))
        mode = self._selected_crawl_mode()
        limit = self._crawl_limit()
        self.download_log.append(
            f"Dropped {len(urls)} URLs — crawling ({mode.value}, limit {limit})…"
        )
        self._refresh_status(f"Crawling {len(urls)} dropped URL(s)…")
        try:
            crawled = crawl_many(
                urls,
                self.settings,
                mode=mode,
                limit=limit,
            )
        except CrawlAuthError as exc:
            QMessageBox.warning(self, "Crawl auth", str(exc))
            self.download_log.append(f"Drop crawl blocked: {exc}")
            return
        except Exception as exc:
            QMessageBox.warning(self, "Drop", str(exc))
            self.download_log.append(f"Drop crawl failed: {exc}")
            return
        links = crawled.urls
        if not links:
            QMessageBox.information(self, "Drop", "No media links found in dropped URLs.")
            return
        opts = self._current_enqueue_options()
        preset = self._selected_download_preset()
        if preset.use_watermark and not opts["watermark_path"]:
            QMessageBox.warning(
                self,
                "Preset",
                "Watermark preset needs a PNG path before enqueueing.",
            )
            return
        q = self._ensure_queue()
        q.add_many(
            links,
            media=opts["media"],
            watermark_path=opts["watermark_path"],
            output_format=opts["output_format"],
        )
        self.download_log.append(
            f"Queued {len(links)} from drop ({preset.name}, crawl={mode.value})."
        )
        self._set_page(1)
        self._nav_buttons[1].setChecked(True)
        self._refresh_status(f"Queued {len(links)} from drop ({preset.name})")

    def _apply_queue_filters(self) -> None:
        state_want = self.queue_state_filter.currentData() or ""
        needle = self.queue_search_filter.text().strip().lower()
        visible = 0
        total = self.queue_table.rowCount()
        for row in range(total):
            state_item = self.queue_table.item(row, 2)
            title_item = self.queue_table.item(row, 1)
            export_item = self.queue_table.item(row, 3)
            msg_item = self.queue_table.item(row, 5)
            state = (state_item.text() if state_item else "").lower()
            title = (title_item.text() if title_item else "").lower()
            export = (export_item.text() if export_item else "").lower()
            msg = (msg_item.text() if msg_item else "").lower()
            state_ok = not state_want or state == state_want.lower()
            text_ok = (
                not needle
                or needle in title
                or needle in msg
                or needle in state
                or needle in export
            )
            show = state_ok and text_ok
            self.queue_table.setRowHidden(row, not show)
            if show:
                visible += 1
        if total == 0:
            self.queue_filter_count.setText("")
        elif visible == total and not state_want and not needle:
            self.queue_filter_count.setText(f"{total} item(s)")
        else:
            self.queue_filter_count.setText(f"{visible}/{total} shown")

    def _ensure_queue(self) -> DownloadQueue:
        out = self.out_edit.text().strip() or os.path.expanduser("~/Downloads/YTSDownloader")
        os.makedirs(out, exist_ok=True)
        opts = self._current_enqueue_options()
        # Queue-level defaults match the active Download preset (per-job opts still win).
        wm_default = opts["watermark_path"]
        fmt_default = opts["output_format"] if opts["media"] == "video" else (
            self.format_combo.currentText() or "mp4"
        )
        if self.queue is None or self.queue.output_dir != out:
            old_jobs = self.queue.jobs() if self.queue else []
            if self.queue:
                self.queue.stop()
            self.queue = DownloadQueue(
                settings=self.settings,
                output_dir=out,
                watermark_path=wm_default,
                output_format=fmt_default,
            )
            self.queue.add_listener(lambda job: self._bridge.job_updated.emit(job))
            if old_jobs:
                self.queue.restore_jobs(old_jobs)
        else:
            self.queue.watermark_path = wm_default
            self.queue.output_format = fmt_default
            self.queue.settings = self.settings
        return self.queue

    def _schedule_persist(self) -> None:
        if not self._persist_enabled:
            return
        self._persist_timer.start()

    def _persist_queue_now(self) -> None:
        if not self._persist_enabled or not self.queue:
            return
        snapshot = serialize_queue_snapshot(
            jobs=self.queue.jobs(),
            output_dir=self.queue.output_dir,
            watermark_path=self.queue.watermark_path,
            output_format=self.queue.output_format,
        )
        try:
            save_queue_state(self._queue_state_path, snapshot)
        except OSError:
            pass

    def _restore_queue_from_disk(self) -> None:
        data = load_queue_state(self._queue_state_path)
        if not data:
            return
        jobs, meta = deserialize_queue_snapshot(data, remap_running=True)
        if not jobs:
            return
        self._persist_enabled = False
        try:
            out = (meta.get("output_dir") or "").strip()
            if out:
                self.out_edit.setText(out)
            wm = (meta.get("watermark_path") or "").strip()
            if wm:
                self.wm_edit.setText(wm)
            fmt = (meta.get("output_format") or "").strip()
            if fmt:
                idx = self.format_combo.findText(fmt)
                if idx >= 0:
                    self.format_combo.setCurrentIndex(idx)
            q = self._ensure_queue()
            q.restore_jobs(jobs)
            for job in q.jobs():
                self._upsert_job_row(job)
            pending = sum(1 for j in jobs if j.state == JobState.QUEUED)
            done = sum(1 for j in jobs if j.state == JobState.DONE)
            failed = sum(1 for j in jobs if j.state == JobState.FAILED)
            self._refresh_status(
                f"Restored {len(jobs)} item(s) "
                f"({pending} pending, {done} done, {failed} failed) — not auto-started"
            )
            self._update_overall()
        finally:
            self._persist_enabled = True

    def _resolve_and_queue(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Input", "Enter a URL.")
            return
        out = self.out_edit.text().strip()
        if not out:
            QMessageBox.warning(self, "Input", "Choose an output folder.")
            return
        mode = self._selected_crawl_mode()
        limit = self._crawl_limit()
        self.download_log.append(
            f"Crawling {url} ({detect_platform(url)}, mode={mode.value}, limit={limit})…"
        )
        try:
            crawled = crawl_profile(
                url,
                self.settings,
                mode=mode,
                limit=limit,
            )
        except CrawlAuthError as exc:
            self.download_log.append(f"Crawl blocked: {exc}")
            QMessageBox.warning(self, "Crawl auth", str(exc))
            return
        except Exception as exc:
            self.download_log.append(f"Crawl failed: {exc}")
            QMessageBox.warning(self, "Crawl", str(exc))
            return
        links = crawled.urls
        if not links:
            detail = "; ".join(crawled.errors[:3]) if crawled.errors else ""
            QMessageBox.information(
                self,
                "Crawl",
                "No media links found." + (f"\n{detail}" if detail else ""),
            )
            return
        title_cache.reset_stats()
        q = self._ensure_queue()
        opts = self._current_enqueue_options()
        preset = self._selected_download_preset()
        if preset.use_watermark and not opts["watermark_path"]:
            QMessageBox.warning(
                self,
                "Preset",
                "Watermark preset needs a PNG path before enqueueing.",
            )
            return
        for link in links:
            q.add(
                link,
                media=opts["media"],
                watermark_path=opts["watermark_path"],
                output_format=opts["output_format"],
            )
        self.cache_label.setText(title_cache.status_text())
        tabs = f", tabs={'+'.join(crawled.tabs_tried)}" if crawled.tabs_tried else ""
        self.download_log.append(
            f"Queued {len(links)} item(s) [{preset.name}, crawl={mode.value}{tabs}]. "
            "Open Queue and press Start."
        )
        self._set_page(1)
        self._nav_buttons[1].setChecked(True)
        self._refresh_status(f"Queued {len(links)} item(s) ({preset.name})")

    def _grabber_queue(self) -> None:
        lines = self.grabber_text.toPlainText().splitlines()
        urls = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]
        if not urls:
            QMessageBox.warning(self, "Grabber", "Paste at least one URL.")
            return
        mode = self._selected_crawl_mode()
        limit = self._crawl_limit()
        self._refresh_status(f"Crawling {len(urls)} line(s) ({mode.value})…")
        try:
            crawled = crawl_many(
                urls,
                self.settings,
                mode=mode,
                limit=limit,
            )
        except CrawlAuthError as exc:
            QMessageBox.warning(self, "Crawl auth", str(exc))
            return
        except Exception as exc:
            QMessageBox.warning(self, "Grabber", str(exc))
            return
        links = crawled.urls
        q = self._ensure_queue()
        opts = self._current_enqueue_options()
        preset = self._selected_download_preset()
        if preset.use_watermark and not opts["watermark_path"]:
            QMessageBox.warning(
                self,
                "Preset",
                "Watermark preset needs a PNG path before enqueueing.",
            )
            return
        q.add_many(
            links,
            media=opts["media"],
            watermark_path=opts["watermark_path"],
            output_format=opts["output_format"],
        )
        self._set_page(1)
        self._nav_buttons[1].setChecked(True)
        self._refresh_status(
            f"Queued {len(links)} from grabber ({preset.name}, crawl={mode.value})"
        )

    def _check_auth(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Auth", "Enter a URL first.")
            return
        try:
            auth_probe(url, self.settings)
            QMessageBox.information(self, "Auth", "Authentication / runtime check passed.")
            self.download_log.append("Auth check passed.")
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Auth",
                f"Check failed:\n{exc}\n\n"
                "Set COOKIES_FROM_BROWSER or COOKIES_FILE in config.ini and retry.",
            )
            self.download_log.append(f"Auth check failed: {exc}")

    def _start_queue(self) -> None:
        q = self._ensure_queue()
        if not q.jobs():
            QMessageBox.information(self, "Queue", "Queue is empty.")
            return
        q.start()
        self._refresh_status("Queue running")
        self._set_page(1)
        self._nav_buttons[1].setChecked(True)

    def _stop_queue(self) -> None:
        if self.queue:
            self.queue.stop()
            self._refresh_status("Queue stopped")

    def _rebuild_queue_table(self) -> None:
        self.queue_table.setRowCount(0)
        self._job_rows.clear()
        if not self.queue:
            return
        for job in self.queue.jobs():
            self._upsert_job_row(job)
        self._apply_queue_filters()
        self._refresh_failure_triage()
        self._update_overall()

    def _clear_finished(self) -> None:
        if not self.queue:
            return
        self.queue.clear_terminal()
        self._rebuild_queue_table()
        self._persist_queue_now()

    def _clear_all_queue(self) -> None:
        if not self.queue or not self.queue.jobs():
            QMessageBox.information(self, "Queue", "Queue is already empty.")
            return
        reply = QMessageBox.question(
            self,
            "Clear All",
            "Remove every item from the queue?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        n = self.queue.clear_all()
        self._rebuild_queue_table()
        self._persist_queue_now()
        self._refresh_status(f"Cleared {n} queue item(s)")

    def _job_id_at_row(self, row: int) -> Optional[str]:
        for jid, r in self._job_rows.items():
            if r == row:
                return jid
        return None

    def _queue_table_context_menu(self, pos: QPoint) -> None:
        if not self.queue:
            return
        index = self.queue_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        # Ensure the clicked row is part of the selection (keeps multi-select).
        selected_rows = {i.row() for i in self.queue_table.selectionModel().selectedRows()}
        if row not in selected_rows:
            self.queue_table.selectRow(row)
        ids = self._selected_queue_job_ids()
        if not ids:
            jid = self._job_id_at_row(row)
            if jid:
                ids = [jid]
        if not ids:
            return

        menu = QMenu(self.queue_table)
        remove_act = QAction("Remove from queue", menu)
        force_act = QAction("Force download", menu)
        menu.addAction(remove_act)
        menu.addAction(force_act)
        chosen = menu.exec(self.queue_table.viewport().mapToGlobal(pos))
        if chosen is remove_act:
            self._remove_queue_jobs(ids)
        elif chosen is force_act:
            self._force_download_jobs(ids)

    def _remove_queue_jobs(self, job_ids: List[str]) -> None:
        if not self.queue or not job_ids:
            return
        n = self.queue.remove_jobs(job_ids)
        self._rebuild_queue_table()
        self._persist_queue_now()
        self._refresh_status(f"Removed {n} item(s) from queue")

    def _force_download_jobs(self, job_ids: List[str]) -> None:
        if not self.queue or not job_ids:
            return
        ok = 0
        for jid in job_ids:
            if self.queue.force_download(jid):
                ok += 1
        self._rebuild_queue_table()
        self._persist_queue_now()
        self._update_overall()
        if ok:
            self._refresh_status(f"Force download started for {ok} item(s)")
        else:
            QMessageBox.information(self, "Force download", "No matching queue items.")

    def _on_job_updated(self, job: QueueJob) -> None:
        self._upsert_job_row(job)
        self._update_overall()
        self._track_job_analytics(job)
        self.cache_label.setText(title_cache.status_text())
        self._schedule_persist()
        selected = self._selected_queue_job_ids()
        if job.id in selected or job.state == JobState.FAILED:
            self._refresh_failure_triage()

    def _track_job_analytics(self, job: QueueJob) -> None:
        """Update local session counters when a job finishes (or is re-queued)."""
        if job.state == JobState.QUEUED:
            self._analytics_counted.discard(job.id)
            self._analytics_started.pop(job.id, None)
            return
        if job.state == JobState.RUNNING:
            # Start timing when download work begins (after playlist pace wait).
            if job.message.startswith("Downloading") and job.id not in self._analytics_started:
                self._analytics_started[job.id] = time.monotonic()
            return
        if job.state not in (JobState.DONE, JobState.FAILED):
            return
        if job.id in self._analytics_counted:
            return
        self._analytics_counted.add(job.id)
        started = self._analytics_started.pop(job.id, None)
        duration = (time.monotonic() - started) if started is not None else None
        if job.state == JobState.DONE:
            self.session_analytics.record_success(duration)
        else:
            self.session_analytics.record_failure(duration)
        self._refresh_analytics_label()

    def _upsert_job_row(self, job: QueueJob) -> None:
        row = self._job_rows.get(job.id)
        if row is None:
            row = self.queue_table.rowCount()
            self.queue_table.insertRow(row)
            self._job_rows[job.id] = row
        self.queue_table.setItem(row, 0, QTableWidgetItem(str(job.index or "")))
        self.queue_table.setItem(row, 1, QTableWidgetItem(job.title or job.url))
        self.queue_table.setItem(row, 2, QTableWidgetItem(job.state.value))
        self.queue_table.setItem(row, 3, QTableWidgetItem(self._job_export_label(job)))
        self.queue_table.setItem(row, 4, QTableWidgetItem(f"{job.progress:.0f}%"))
        self.queue_table.setItem(row, 5, QTableWidgetItem(job.message or job.error or ""))
        self._apply_queue_filters()

    def _update_overall(self) -> None:
        if not self.queue:
            self.overall_progress.setValue(0)
            return
        jobs = self.queue.jobs()
        if not jobs:
            self.overall_progress.setValue(0)
            return
        avg = sum(j.progress for j in jobs) / len(jobs)
        self.overall_progress.setValue(int(avg))
        done = sum(1 for j in jobs if j.state == JobState.DONE)
        failed = sum(1 for j in jobs if j.state == JobState.FAILED)
        self._refresh_status(f"Queue: {done}/{len(jobs)} done, {failed} failed")

    def _poll_spotify_session(self) -> None:
        try:
            track = spotify_bridge.read_now_playing()
            self.spotify_status.setText("Session: connected (MPRIS)")
            artists = ", ".join(track.artists) if track.artists else "—"
            self.spotify_now.setText(
                f"Now playing: {track.title} — {artists}\n{track.spotify_url}"
            )
        except Exception as exc:
            self.spotify_status.setText(f"Session: offline ({exc})")
            self.spotify_now.setText("Now playing: —")

    def _queue_now_playing(self) -> None:
        try:
            track = spotify_bridge.read_now_playing()
        except Exception as exc:
            QMessageBox.warning(self, "Metadata Bridge", str(exc))
            return
        q = self._ensure_queue()
        query = track.search_query
        job = q.add(
            track.spotify_url or query,
            media="search_audio",
            title=query,
            search_query=query,
        )
        self.spotify_log.append(f"Queued now playing: {query} [{job.id[:8]}]")
        self._set_page(1)
        self._nav_buttons[1].setChecked(True)
        self._start_queue()

    def _queue_spotify_url(self) -> None:
        url = self.spotify_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Metadata Bridge", "Enter a catalog URL.")
            return
        tracks = spotify_bridge.resolve_spotify_entries(url, self.settings)
        if not tracks:
            # Fallback: treat now-playing query if URL is current track
            try:
                now = spotify_bridge.read_now_playing()
                if now.spotify_url and now.spotify_url.rstrip("/") == url.rstrip("/"):
                    tracks = [now]
            except Exception:
                pass
        if not tracks:
            QMessageBox.information(
                self,
                "Metadata Bridge",
                "Could not resolve catalog entries. Play the track in Spotify "
                "and use Queue Now Playing, or paste a track URL while it is playing.",
            )
            return
        q = self._ensure_queue()
        for t in tracks:
            query = t.search_query
            q.add(
                t.spotify_url or query,
                media="search_audio",
                title=query,
                search_query=query,
            )
        self.spotify_log.append(f"Queued {len(tracks)} track(s) from catalog URL.")
        self._set_page(1)
        self._nav_buttons[1].setChecked(True)

    def _save_settings(self) -> None:
        settings = self._settings_from_form()
        try:
            save_settings(settings, self.config_path)
        except OSError as exc:
            QMessageBox.warning(self, "Settings", f"Could not write config.ini:\n{exc}")
            return
        self._apply_settings_runtime(settings)
        self._fill_settings_form(settings)
        self._refresh_status("Settings saved to config.ini")
        QMessageBox.information(
            self,
            "Settings",
            "Saved to config.ini and applied.\n"
            "Worker count changes take effect on the next Start Queue.",
        )

    def _reload_settings(self) -> None:
        self.settings = load_settings(self.config_path)
        self._fill_settings_form(self.settings)
        self._apply_settings_runtime(self.settings)
        self._refresh_status("Config reloaded")
        QMessageBox.information(self, "Settings", "config.ini reloaded.")

    def _refresh_status(self, text: str) -> None:
        self.status.showMessage(text)

    def _refresh_analytics_label(self) -> None:
        if not hasattr(self, "analytics_label"):
            return
        show = bool(getattr(self.settings, "show_status_analytics", True))
        self.analytics_label.setVisible(show)
        if show:
            self.analytics_label.setText(self.session_analytics.format_status())
        else:
            self.analytics_label.setText("")

    def closeEvent(self, event) -> None:  # noqa: N802
        self._spotify_timer.stop()
        self._companion_timer.stop()
        self._persist_timer.stop()
        if self.queue:
            self.queue.stop()
            self._persist_queue_now()
        super().closeEvent(event)
