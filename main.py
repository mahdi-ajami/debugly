import flet as ft
from app.main_view import MainView


def main():
    app = MainView()
    ft.app(target=app.build)


if __name__ == "__main__":
    main()
