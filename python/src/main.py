"""
Neutralized entrypoint.

Phase 1 safety: src/ is importable code only.
Use scripts/ as entry points.
"""

def main():
    raise RuntimeError(
        "Phase 1 safety: do not run python/src/main.py. "
        "Use: python -m scripts.run_simulation (Phase 1a) or "
        "python -m scripts.run_recorder (Phase 1b)."
    )


if __name__ == "__main__":
    main()