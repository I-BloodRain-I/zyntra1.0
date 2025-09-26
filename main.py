import logging
from src import App, SelectProductScreen, APP_TITLE
from src.screens.nonsticker import NStickerCanvasScreen

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = App(title=APP_TITLE)
    app.show_screen(NStickerCanvasScreen)
    # app.show_screen(SelectProductScreen)
    app.mainloop()