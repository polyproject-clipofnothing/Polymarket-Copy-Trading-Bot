from src.services.recorder.recorder_service import main as service_main


def main() -> int:
    return service_main()


if __name__ == "__main__":
    # Correct entrypoint when run as a module
    raise SystemExit(main())
