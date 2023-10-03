from pyxbar import Menu, MenuItem

if __name__ == "__main__":
    Menu("some title").with_items(
        MenuItem(
            "👁️ overview",
        ),
    ).print()
