import logging
import sys

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
for lg in ["core", "core.cache", "core.hf_models", "core.vlm_handler", "core.web_search",
            "core.agent", "core.rag_pipeline", "core.reward_system", "core.guardrails"]:
    logging.getLogger(lg).setLevel(logging.DEBUG)
logging.getLogger("flet").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

import flet as ft
from app.main_view import MainView


def main():
    app = MainView(is_dark_default=True)
    ft.run(app.build)


if __name__ == "__main__":
    main()
