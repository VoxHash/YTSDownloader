"""Output-folder picker helpers with Linux volume sidebar URLs."""

from __future__ import annotations

import os
import sys
from typing import List, Optional, Sequence

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


def _user_name() -> str:
    return (
        os.environ.get("USER")
        or os.environ.get("LOGNAME")
        or os.path.basename(os.path.expanduser("~"))
        or "user"
    )


def _existing_dir(path: str) -> Optional[str]:
    try:
        if path and os.path.isdir(path):
            return os.path.abspath(path)
    except OSError:
        return None
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


def discover_mount_points(proc_mounts: Optional[str] = None) -> List[str]:
    """
    Return absolute mount points for user-visible volumes.

    Reads ``/proc/mounts`` (or ``proc_mounts`` text) and keeps paths under
    ``/run/media/$USER``, ``/media/$USER``, ``/mnt``, plus other real device
    mounts with common filesystem types. Does **not** add XDG user folders.
    Under ``/mnt``, only real mount points are included (empty stubs like
    ``/mnt/test`` are skipped).
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
        abs_path = _existing_dir(path)
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
        source, target, fstype = parts[0], parts[1], parts[2]
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
        try:
            for name in sorted(os.listdir(root)):
                child = os.path.join(root, name)
                add(child)
        except OSError:
            pass

    # Under /mnt only real mounts — never empty stubs (e.g. /mnt/test).
    try:
        for name in sorted(os.listdir("/mnt")):
            child = os.path.join("/mnt", name)
            if _is_mount_point(child):
                add(child)
    except OSError:
        pass

    return found


def volume_sidebar_paths(
    *,
    home: Optional[str] = None,
    downloads: Optional[str] = None,
    proc_mounts: Optional[str] = None,
    extra: Optional[Sequence[str]] = None,
) -> List[str]:
    """
    Ordered sidebar paths: discovered volume/mount roots only.

    ``home`` / ``downloads`` are accepted for API compatibility but ignored —
    XDG places must not appear in the dialog sidebar. Pure path helper (no Qt)
    so unit tests can run without a display.
    """
    del home, downloads  # unused; kept for call-site compatibility
    paths: List[str] = []
    seen = set()

    def add(path: str) -> None:
        abs_path = _existing_dir(path)
        if not abs_path or abs_path in seen:
            return
        if _is_xdg_user_place(abs_path):
            return
        seen.add(abs_path)
        paths.append(abs_path)

    for m in discover_mount_points(proc_mounts=proc_mounts):
        add(m)
    if extra:
        for p in extra:
            add(p)
    return paths


def configure_directory_dialog(dialog, *, start_dir: str = "") -> None:
    """
    Apply volume sidebar URLs and Linux non-native option to a QFileDialog.

    Native GTK/KDE pickers often hide removable volumes; Qt's dialog plus
    ``setSidebarUrls`` lists mount roots only (no Desktop/Downloads/Trash).
    """
    from PyQt6.QtCore import QUrl
    from PyQt6.QtWidgets import QFileDialog

    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    if start_dir:
        dialog.setDirectory(start_dir)
    if sys.platform.startswith("linux"):
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    urls = [QUrl.fromLocalFile(p) for p in volume_sidebar_paths()]
    # Always set (even empty) so Qt default XDG places are replaced.
    dialog.setSidebarUrls(urls)


def get_existing_directory(
    parent,
    caption: str,
    directory: str = "",
) -> str:
    """QFileDialog.getExistingDirectory replacement with volume sidebar."""
    from PyQt6.QtWidgets import QFileDialog

    start = directory or ""
    dialog = QFileDialog(parent, caption, start)
    configure_directory_dialog(dialog, start_dir=start)
    if dialog.exec():
        selected = dialog.selectedFiles()
        return selected[0] if selected else ""
    return ""
