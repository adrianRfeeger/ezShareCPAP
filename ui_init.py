import pathlib
import pygubu


PROJECT_PATH = pathlib.Path(__file__).parent
PROJECT_UI = PROJECT_PATH / "ezshare.ui"
RESOURCE_PATHS = [PROJECT_PATH]


def initialize_ui(master, config, app_instance):
    builder = pygubu.Builder()
    builder.add_resource_paths(RESOURCE_PATHS)
    builder.add_from_file(PROJECT_UI)

    mainwindow = builder.get_object('mainwindow', master)
    builder.connect_callbacks(app_instance)

    return builder, mainwindow
