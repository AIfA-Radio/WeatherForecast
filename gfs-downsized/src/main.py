import os
import json
import logging
from client import Client
from gfs_retrieve import extract, write_forecast

# logging.basicConfig(level=logging.DEBUG)

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = "{}/../data".format(SOURCE_DIR)

STEPS = list(range(1, 121)) + list(range(123, 385, 3))
# STEPS = [0,1,2]


def defined_kwargs(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None}


def main():

    dict_x: dict = {}
    date_creation_string: str = None

    config_file = "{}/parameter.json".format(DATA_DIR)
    with open(config_file, "r") as f:
        config = json.load(f)

    for step in STEPS:

        # grid: mandatory [SLS|GLOB]
        client = Client(grid=config["grid"])

        params = defined_kwargs(
            # validity optional, list of substrings, e.g. "fcst" and/or "anl"
            validity=config.get('validity'),
            # only used with grid="GLOB"
            paramset=config.get('paramset'),
            # only used with grid="GLOB"
            resol=config.get('resol'),
            target=config.get('target'),
            # if missing, most recent date and/or time
            date=config.get('date'),
            time=config.get('time')
        )

        results = client.retrieve(
            step=[step],
            parameter=config['parameter'],
            **params
        )
        # success, match file size(s)
        print(f"File size matched: {results}")

        for target in sorted(os.listdir(DATA_DIR)):  # ToDo
            if target.endswith(".grib2"):
                date_creation_string, r = extract(f"{DATA_DIR}/{target}")

                for k, v in r.items():
                    try:
                        dict_x[k]['time'].extend(v['time'])
                        dict_x[k]['value'].extend(v['value'])
                    except KeyError:
                        dict_x[k] = v

                print(
                    json.dumps(dict_x, indent=4)
                )

                # if os.path.exists("{}/{}".format(DATA_DIR, target)):
                os.remove("{}/{}".format(DATA_DIR, target))
                print("File '{}' deleted".format(target))

        write_forecast(datetimestr=date_creation_string,
                       forecast=dict_x)  # always update


if __name__ == "__main__":
    main()
