#!/bin/sh

# Thin POSIX entry point for Aura's canonical, non-mutating runtime.
case $0 in
    /*) script_path=$0 ;;
    *) script_path=$PWD/$0 ;;
esac
script_dir=${script_path%/*}

if ! repository_root=$(CDPATH= cd -- "$script_dir" 2>/dev/null && pwd -P); then
    printf '%s\n' "Aura: repository root could not be resolved." >&2
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    printf '%s\n' \
        "Aura: uv is required. See https://docs.astral.sh/uv/getting-started/installation/" \
        >&2
    exit 127
fi

if ! cd -- "$repository_root"; then
    printf '%s\n' "Aura: repository root is unavailable." >&2
    exit 1
fi

exec uv run --locked --no-sync python -m aura_backend.runtime serve "$@"
