import importlib
import os
import sys


def load_config():

    config_name = os.environ.get("TG_CONF")

    if config_name is None:
        config_name = "local_keys"  #Чтобы явно не указывать переменное окружение при работе с локальной машины.

    try:
        config = importlib.import_module("settings.{}".format(config_name))
        print("Loaded config \"{}\" - OK".format(config_name))
        return config

    except (TypeError, ValueError, ImportError):
        print("Invalid config \"{}\"".format(config_name))
        sys.exit(1) # Любой статус-код отличный от 0 означает ошибку