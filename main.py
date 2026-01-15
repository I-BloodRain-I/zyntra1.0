import logging
from src import App, SelectProductScreen, APP_TITLE
from src.screens.common import *
from src.screens.nonsticker import *
from src.screens.sticker import *
from src.core.state import close_sdk_client

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s %(name)s] [%(levelname)s] %(message)s")
    logging.getLogger("PIL").setLevel(logging.WARNING)
    app = App(title=APP_TITLE)
    app.show_screen(SelectProductScreen)
    # app.show_screen(NStickerCanvasScreen)
    try:
        app.mainloop()
    finally:
        close_sdk_client()