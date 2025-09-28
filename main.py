import logging
from src import App, SelectProductScreen, APP_TITLE
from src.screens.nonsticker import NStickerCanvasScreen
from src.screens.sticker import StickerFontInfoScreen, StickerBasicInfoScreen

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s %(name)s] [%(levelname)s] %(message)s")
    logging.getLogger("PIL").setLevel(logging.WARNING)
    app = App(title=APP_TITLE)
    # app.show_screen(StickerFontInfoScreen)
    app.show_screen(SelectProductScreen)
    app.mainloop()