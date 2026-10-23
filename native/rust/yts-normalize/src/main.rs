//! Batch URL / path normalize for YTSDownloader.
//! IPC: one JSON object on stdin → one JSON object on stdout.
//!
//! Request:
//!   {"op":"urls","items":["https://a.example/x","  https://a.example/x  "]}
//!   {"op":"paths","items":["./foo/../bar"]}
//! Response:
//!   {"ok":true,"items":["https://a.example/x"]}

use std::collections::HashSet;
use std::io::{self, Read};
use std::path::PathBuf;

fn main() {
    let mut raw = String::new();
    if let Err(e) = io::stdin().read_to_string(&mut raw) {
        emit_err(&format!("stdin read failed: {e}"));
        std::process::exit(1);
    }
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        emit_ok(Vec::new());
        return;
    }
    let value: serde_json::Value = match serde_json::from_str(trimmed) {
        Ok(v) => v,
        Err(e) => {
            emit_err(&format!("invalid JSON: {e}"));
            std::process::exit(1);
        }
    };
    let op = value
        .get("op")
        .and_then(|v| v.as_str())
        .unwrap_or("urls")
        .to_ascii_lowercase();
    let items = match value.get("items").and_then(|v| v.as_array()) {
        Some(arr) => arr
            .iter()
            .filter_map(|v| v.as_str().map(|s| s.to_string()))
            .collect::<Vec<_>>(),
        None => {
            emit_err("missing string array field \"items\"");
            std::process::exit(1);
        }
    };
    let out = match op.as_str() {
        "urls" | "url" | "normalize_urls" => normalize_urls(items),
        "paths" | "path" | "normalize_paths" => normalize_paths(items),
        other => {
            emit_err(&format!("unknown op: {other}"));
            std::process::exit(1);
        }
    };
    emit_ok(out);
}

fn normalize_urls(items: Vec<String>) -> Vec<String> {
    let mut seen = HashSet::new();
    let mut out = Vec::with_capacity(items.len());
    for raw in items {
        let candidate = clean_url_token(&raw);
        if candidate.is_empty() {
            continue;
        }
        if !(candidate.starts_with("http://") || candidate.starts_with("https://")) {
            continue;
        }
        // Require a non-empty authority (host) after the scheme.
        let rest = candidate
            .strip_prefix("https://")
            .or_else(|| candidate.strip_prefix("http://"))
            .unwrap_or("");
        let host = rest.split(['/', '?', '#']).next().unwrap_or("");
        if host.is_empty() {
            continue;
        }
        if seen.insert(candidate.clone()) {
            out.push(candidate);
        }
    }
    out
}

fn clean_url_token(raw: &str) -> String {
    let mut s = raw.trim().to_string();
    // Strip common trailing punctuation from paste noise.
    while let Some(last) = s.chars().last() {
        if ").,;]'\"".contains(last) {
            s.pop();
        } else {
            break;
        }
    }
    s
}

fn normalize_paths(items: Vec<String>) -> Vec<String> {
    let mut seen = HashSet::new();
    let mut out = Vec::with_capacity(items.len());
    for raw in items {
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            continue;
        }
        let path = PathBuf::from(trimmed);
        let canon = path.canonicalize().unwrap_or_else(|_| {
            // Non-existent paths: collapse . and .. components best-effort.
            let mut parts = Vec::new();
            for comp in path.components() {
                match comp {
                    std::path::Component::CurDir => {}
                    std::path::Component::ParentDir => {
                        parts.pop();
                    }
                    other => parts.push(other.as_os_str().to_os_string()),
                }
            }
            if path.is_absolute() {
                let mut abs = PathBuf::from("/");
                for p in parts {
                    abs.push(p);
                }
                abs
            } else {
                std::env::current_dir()
                    .unwrap_or_else(|_| PathBuf::from("."))
                    .join(PathBuf::from_iter(parts))
            }
        });
        let text = canon.to_string_lossy().to_string();
        if seen.insert(text.clone()) {
            out.push(text);
        }
    }
    out
}

fn emit_ok(items: Vec<String>) {
    let payload = serde_json::json!({ "ok": true, "items": items });
    println!("{payload}");
}

fn emit_err(msg: &str) {
    let payload = serde_json::json!({ "ok": false, "error": msg, "items": [] });
    println!("{payload}");
}
