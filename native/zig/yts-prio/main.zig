//! Alternate Zig entry for yts-prio.
//!
//! Zig 0.17 `build-exe` no longer supports `@cImport` in this toolchain mode.
//! The build script therefore prefers:
//!   1. `cc` / `gcc` compiling `native/c/yts-prio.c`
//!   2. `zig cc` compiling the same C sources (Zig as C toolchain)
//!
//! Pure-Zig rewrite is deferred until Zig 0.17 process/Io APIs settle; behavior
//! must match `native/c/yts-prio.c` (JSON stdout, `--pid` / `--nice` / `--ionice-idle`).

comptime {
    @compileError(
        "Build yts-prio via scripts/build_natives.sh (cc or zig cc on native/c/yts-prio.c). " ++
            "Pure Zig 0.17 port is deferred; see ROADMAP.",
    );
}
