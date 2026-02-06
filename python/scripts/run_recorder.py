from src.services.recorder.recorder_service import main as service_main


def main() -> int:
    return service_main()


if __name__ == "__main__":
    raise RuntimeError("Run as: python -m scripts.run_recorder")
