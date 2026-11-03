"""Output-folder picker helpers with Linux volume sidebar URLs.

Browse hangs on Linux are almost always Qt ``QFileDialog`` doing synchronous
stat/icon/listing I/O on the UI thread against slow or stuck mounts (NTFS,
exFAT, FUSE, NFS). This module:

- Probes candidate sidebar paths with a short timeout (skip hung volumes)
- Caches sidebar URLs so repeated Browse does not re-scan mounts
- Configures the non-native dialog to avoid symlink resolution and custom
  directory-icon lookups that amplify mount I/O
- Guards against re-entrant dialog opens
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import List, Optional, Sequence, Tuple

_SKIP_MOUNT_PREFIXES = (
    "/proc",
    "/sys",
    "/dev",
    "/run/user",
    "/snap",
    "/boot",
    "/var/lib/docker",
    "/var/lib/containers",
)

# Never put XDG user places (or Trash) in the folder-dialog sidebar.
_XDG_SIDEBAR_NAMES = frozenset(
    {
        "desktop",
        "documents",
        "downloads",
        "music",
        "pictures",
        "videos",
        "trash",
        ".trash",
        "home",
    }
)

# Soft deadline for isdir / listdir against removable / secondary volumes.
# Hung NFS/FUSE/NTFS must not block the Qt UI thread while building the sidebar.
_MOUNT_PROBE_TIMEOUT_S = 0.35
_SIDEBAR_CACHE_TTL_S = 30.0

_sidebar_cache: Optional[Tuple[float, Tuple[str, ...]]] = None
_sidebar_cache_lock = threading.Lock()
_dialog_open = False
_dialog_open_lock = threading.Lock()


def _user_name() -> str:
    return (
        os.environ.get("USER")
        or os.environ.get("LOGNAME")
        or os.path.basename(os.path.expanduser("~"))
        or "user"
    )


def path_ready(path: str, timeout: float = _MOUNT_PROBE_TIMEOUT_S) -> bool:
    """
    Return True if ``path`` is a directory and responds within ``timeout`` seconds.

    Runs ``os.path.isdir`` on a daemon thread so a stuck mount does not block the
    caller past ``timeout``. Threads blocked in uninterruptible I/O are abandoned
    (the path is treated as not ready).
    """
    if not path:
        return False
    if timeout <= 0:
        try:
            return os.path.isdir(path)
        except OSError:
            return False

    box: List[Optional[bool]] = [None]

    def _probe() -> None:
        try:
            box[0] = bool(os.path.isdir(path))
        except OSError:
            box[0] = False

    worker = threading.Thread(target=_probe, name="yts-path-ready", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        return False
    return bool(box[0])


def listdir_ready(
    path: str, timeout: float = _MOUNT_PROBE_TIMEOUT_S
) -> Optional[List[str]]:
    """
    ``os.listdir`` with the same soft timeout as ``path_ready``.

    Returns ``None`` on timeout or OSError so callers can skip the root.
    """
    if not path:
        return None
    box: List[Optional[List[str]]] = [None]
    err: List[BaseException] = []

    def _probe() -> None:
        try:
            box[0] = sorted(os.listdir(path))
        except OSError as exc:
            err.append(exc)

    worker = threading.Thread(target=_probe, name="yts-listdir-ready", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive() or err:
        return None
    return box[0] if box[0] is not None else []


def _existing_dir(path: str, *, timeout: Optional[float] = None) -> Optional[str]:
    """Absolute directory path if it exists and answers within ``timeout``."""
    try:
        if not path:
            return None
        abs_path = os.path.abspath(path)
    except OSError:
        return None
    probe_timeout = _MOUNT_PROBE_TIMEOUT_S if timeout is None else timeout
    # Local system root is always present; skip thread overhead.
    if abs_path == "/":
        return abs_path
    if path_ready(abs_path, timeout=probe_timeout):
        return abs_path
    return None


def _is_xdg_user_place(path: str) -> bool:
    """True for Home / Desktop / Downloads / Trash-style paths we must not sidebar."""
    try:
        abs_path = os.path.abspath(path)
    except OSError:
        return True
    home = os.path.abspath(os.path.expanduser("~"))
    if abs_path == home:
        return True
    base = os.path.basename(abs_path).lower()
    if base in _XDG_SIDEBAR_NAMES:
        return True
    # Trash locations (user + volume trash dirs).
    if base.startswith(".trash") or "/trash/" in abs_path.lower() + "/":
        return True
    return False


def _is_mount_point(path: str) -> bool:
    try:
        return os.path.ismount(path)
    except OSError:
        return False


def primary_system_volume() -> Optional[str]:
    """
    Absolute path of the local machine root volume for the folder sidebar.

    On Unix this is ``/`` (shown as “Computer” in the Qt dialog). Not used on
    Windows. Does **not** return XDG user places.
    """
    if sys.platform.startswith("win"):
        return None
    return _existing_dir("/", timeout=0.0)


def discover_mount_points(
    proc_mounts: Optional[str] = None,
    *,
    probe_timeout: float = _MOUNT_PROBE_TIMEOUT_S,
) -> List[str]:
    """
    Return absolute mount points for user-visible volumes.

    Reads ``/proc/mounts`` (or ``proc_mounts`` text) and keeps paths under
    ``/run/media/$USER``, ``/media/$USER``, ``/mnt``, plus other real device
    mounts with common filesystem types. Does **not** add XDG user folders
    or the system root (see ``primary_system_volume`` / ``volume_sidebar_paths``).
    Under ``/mnt``, only real mount points are included (empty stubs like
    ``/mnt/test`` are skipped).

    Each candidate is checked with ``path_ready`` so a hung Cloud/USB/NFS volume
    is omitted from the sidebar instead of freezing Browse.
    """
    text = proc_mounts
    if text is None:
        try:
            with open("/proc/mounts", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""

    found: List[str] = []
    seen = set()

    def add(path: str) -> None:
        abs_path = _existing_dir(path, timeout=probe_timeout)
        if not abs_path or abs_path in seen:
            return
        if _is_xdg_user_place(abs_path):
            return
        # Skip container roots themselves; prefer volume leaves.
        if abs_path in ("/run/media", "/media", "/mnt"):
            return
        seen.add(abs_path)
        found.append(abs_path)

    user = _user_name()
    media_user_roots = (f"/run/media/{user}", f"/media/{user}")

    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        _source, target, _fstype = parts[0], parts[1], parts[2]
        # Unescape octal sequences used in /proc/mounts (e.g. \040 for space).
        target = (
            target.replace("\\040", " ")
            .replace("\\011", "\t")
            .replace("\\012", "\n")
            .replace("\\134", "\\")
        )
        if any(target == p or target.startswith(p + "/") for p in _SKIP_MOUNT_PREFIXES):
            continue
        # Only user-facing removable / secondary volume roots — never OS
        # subvolumes (/srv, /root, /var/*, /home, …).
        is_media = (
            target.startswith("/run/media/")
            or target.startswith("/media/")
            or target.startswith("/mnt/")
        )
        if not is_media:
            continue
        add(target)

    # Children of per-user media roots (covers mounts not yet typed in /proc).
    for root in media_user_roots:
        names = listdir_ready(root, timeout=probe_timeout)
        if names is None:
            continue
        for name in names:
            child = os.path.join(root, name)
            add(child)

    # Under /mnt only real mounts — never empty stubs (e.g. /mnt/test).
    names = listdir_ready("/mnt", timeout=probe_timeout)
    if names is not None:
        for name in names:
            child = os.path.join("/mnt", name)
            if _is_mount_point(child):
                add(child)

    return found


def clear_sidebar_cache() -> None:
    """Drop the cached sidebar path list (tests / after mount change)."""
    global _sidebar_cache
    with _sidebar_cache_lock:
        _sidebar_cache = None


def volume_sidebar_paths(
    *,
    home: Optional[str] = None,
    downloads: Optional[str] = None,
    proc_mounts: Optional[str] = None,
    extra: Optional[Sequence[str]] = None,
    use_cache: bool = True,
    probe_timeout: float = _MOUNT_PROBE_TIMEOUT_S,
) -> List[str]:
    """
    Ordered sidebar paths: local system root first, then volume/mount roots.

    ``home`` / ``downloads`` are accepted for API compatibility but ignored —
    XDG places must not appear in the dialog sidebar. Pure path helper (no Qt)
    so unit tests can run without a display.

    Results are cached briefly when ``proc_mounts`` / ``extra`` are not injected,
    so opening Browse twice does not re-probe every Cloud volume on the UI thread.
    """
    del home, downloads  # unused; kept for call-site compatibility
    global _sidebar_cache

    can_cache = use_cache and proc_mounts is None and not extra
    if can_cache:
        with _sidebar_cache_lock:
            cached = _sidebar_cache
            if cached is not None:
                ts, paths = cached
                if (time.monotonic() - ts) < _SIDEBAR_CACHE_TTL_S:
                    return list(paths)

    paths: List[str] = []
    seen = set()

    def add(path: str) -> None:
        # ``extra`` paths still need a readiness probe so tests / callers cannot
        # inject a hung volume into the live sidebar.
        abs_path = _existing_dir(path, timeout=probe_timeout)
        if not abs_path or abs_path in seen:
            return
        if _is_xdg_user_place(abs_path):
            return
        seen.add(abs_path)
        paths.append(abs_path)

    root = primary_system_volume()
    if root:
        add(root)
    for m in discover_mount_points(proc_mounts=proc_mounts, probe_timeout=probe_timeout):
        add(m)
    if extra:
        for p in extra:
            add(p)

    if can_cache:
        with _sidebar_cache_lock:
            _sidebar_cache = (time.monotonic(), tuple(paths))
    return paths


def safe_start_directory(directory: str = "") -> str:
    """
    Directory to open the picker at, falling back if ``directory`` is slow/hung.

    Prefer the requested path when it answers quickly; otherwise home, then ``/``.
    """
    if directory:
        ready = _existing_dir(directory, timeout=_MOUNT_PROBE_TIMEOUT_S)
        if ready:
            return ready
    home = os.path.expanduser("~")
    ready_home = _existing_dir(home, timeout=_MOUNT_PROBE_TIMEOUT_S)
    if ready_home:
        return ready_home
    return "/" if not sys.platform.startswith("win") else home or ""


def _label_system_volume_sidebar(dialog) -> None:
    """Rename the ``/`` sidebar entry to “Computer” in Qt's non-native dialog."""
    from PyQt6.QtWidgets import QListWidget

    for lw in dialog.findChildren(QListWidget):
        for i in range(lw.count()):
            item = lw.item(i)
            if item is None:
                continue
            if item.text() in ("/", ""):
                item.setText("Computer")


def configure_directory_dialog(dialog, *, start_dir: str = "") -> None:
    """
    Apply volume sidebar URLs and Linux non-native option to a QFileDialog.

    Native GTK/KDE pickers often hide removable volumes; Qt's dialog plus
    ``setSidebarUrls`` lists the system root (“Computer”) and mount roots
    (no Desktop/Downloads/Trash). Options that reduce mount I/O are set
    **before** directory/sidebar changes (Qt docs requirement).
    """
    from PyQt6.QtCore import QUrl
    from PyQt6.QtWidgets import QFileDialog

    # Options first — before setDirectory / setSidebarUrls.
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    dialog.setOption(QFileDialog.Option.DontResolveSymlinks, True)
    dialog.setOption(QFileDialog.Option.DontUseCustomDirectoryIcons, True)
    if sys.platform.startswith("linux"):
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setViewMode(QFileDialog.ViewMode.List)

    start = safe_start_directory(start_dir)
    if start:
        dialog.setDirectory(start)

    urls = [QUrl.fromLocalFile(p) for p in volume_sidebar_paths()]
    # Always set (even empty) so Qt default XDG places are replaced.
    dialog.setSidebarUrls(urls)
    _label_system_volume_sidebar(dialog)


def get_existing_directory(
    parent,
    caption: str,
    directory: str = "",
) -> str:
    """QFileDialog.getExistingDirectory replacement with volume sidebar."""
    global _dialog_open
    from PyQt6.QtWidgets import QFileDialog

    with _dialog_open_lock:
        if _dialog_open:
            return ""
        _dialog_open = True

    try:
        start = safe_start_directory(directory or "")
        dialog = QFileDialog(parent, caption, start)
        configure_directory_dialog(dialog, start_dir=start)
        if dialog.exec():
            selected = dialog.selectedFiles()
            return selected[0] if selected else ""
        return ""
    finally:
        with _dialog_open_lock:
            _dialog_open = False
