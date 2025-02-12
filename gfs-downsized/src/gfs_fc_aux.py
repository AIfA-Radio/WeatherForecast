import os
import json

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = "{}/../data".format(SOURCE_DIR)
LOG_DIR = "{}/../logs".format(SOURCE_DIR)

config_file = "{}/parameter.json".format(DATA_DIR)
with open(config_file, "r") as config_handle:
    CONFIG = json.load(config_handle)

DATA_FILE = "{}/forecast.json".format(DATA_DIR)

STEPS = list(range(0, 121)) + list(range(123, 385, 3))  # 0 step is "anl"

def defined_kwargs(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None}
