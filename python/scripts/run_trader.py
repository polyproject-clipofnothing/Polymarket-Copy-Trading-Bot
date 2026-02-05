import os

def main():
    if os.getenv("ENABLE_TRADING", "false").lower() != "true":
        raise RuntimeError(
            "Trading is disabled. Set ENABLE_TRADING=true to run live trader."
        )

    from services.trader.trader_service import TraderService
    TraderService().run()

if __name__ == "__main__":
    main()
