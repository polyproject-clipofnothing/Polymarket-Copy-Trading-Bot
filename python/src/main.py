def main() -> None:
    raise RuntimeError(
        "Phase 1 safety: do not run python/src/main.py.\n"
        "Use:\n"
        "  - python -m scripts.run_simulation   (Phase 1a)\n"
        "  - python -m scripts.run_recorder     (Phase 1b)\n"
        "  - ENABLE_TRADING=true python -m scripts.run_trader  (Phase 2+)\n"
    )

if __name__ == "__main__":
    main()
