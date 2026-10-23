"""Shared helpers."""

from __future__ import annotations


def clean_filename(filename: str) -> str:
    valid_chars = (
        "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789áéíóúÁÉÍÓÚñÑ#"
    )
    return "".join(c for c in filename if c in valid_chars)
