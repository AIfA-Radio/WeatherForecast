import os
import json

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = "{}/../data".format(SOURCE_DIR)
LOG_DIR = "{}/../logs".format(SOURCE_DIR)

config_file = "{}/parameter.json".format(DATA_DIR)
with open(config_file, "r") as f:
    config = json.load(f)

def defined_kwargs(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None}