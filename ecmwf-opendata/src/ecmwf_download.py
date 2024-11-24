#!/usr/bin/env python

"""
ECMWF 10-day weather forecast for the Cerro Chajnantor coordinates, at Atacama,
Chile. For public access - with no license - temporal and spatiol resolution is
downgraded. See specs.

ECMWF HRS
https://www.ecmwf.int/en/forecasts/datasets/set-i

ecmwf-opendata
https://github.com/ecmwf/ecmwf-opendata

pygrib docu
https://jswhit.github.io/pygrib/index.html
"""

from ecmwf.opendata import Client
import pygrib
import os
import argparse
from scipy.interpolate import RegularGridInterpolator
import numpy as np
import json
import math

# data directory relative to source
DATA_DIR = "{}/../data".format(os.path.dirname(os.path.realpath(__file__)))


def write_log(
        datetimestr: str,
        forecast: dict
) -> None:
    """
    update log.json
    :param datetimestr: YYYYMMDDHH
    :param forecast:
    :return: None
    """
    log_file = "{}/forecast.json".format(DATA_DIR)
    if not os.path.exists(log_file):
        with open(log_file, "w") as create_empty:
            json.dump({}, create_empty)
            os.chmod(log_file, 0o666)  # docker owner is root, anyone can delete
    with open(log_file, "r+") as jsonFile:
        data = json.load(jsonFile)
        data[datetimestr] = forecast
        jsonFile.seek(0)  # rewind
        json.dump(data,
                  jsonFile,
                  indent=2,
                  sort_keys=True)
        jsonFile.truncate()


def create_grid(
        coordinates: np.array,
        res: float = 0.25
) -> dict:
    """
    create grid on coordinates
    :param coordinates:
    :param res:
    :return:
    """

    def flip(x):
        return (x + 180) % 360 - 180  # [-180, 180[
#        return x % 360  # [0, 360]

    return {
        "lat1": max(-90, math.floor(coordinates[0] - 4 * res)),
        "lat2": min(90, math.ceil(coordinates[0] + 4 * res)),
        "lon1": flip(math.floor(coordinates[1] - 4 * res)),
        "lon2": flip(math.ceil(coordinates[1] + 4 * res))
    }


def main(
        extended: bool = False,
        delete: bool = False
) -> None:
    file_default = "data.grib2"
    date_creation = None
    dict_x: dict = {}
    spatial_resolution: float = 0.25

    config_file = "{}/parameter.json".format(DATA_DIR)
    config = json.load(open(config_file, "r"))
    target: str = "{}/{}".format(DATA_DIR, file_default)
    params: list = config['parameter']

    if extended:
        # HRES 	00 and 12 	0 to 144 by 3, 144 to 240 by 6
        steps: list = list(range(0, 144, 3)) + list(range(144, 241, 6))
        print("Fetching 10-day Forecast")
    else:
        # HRES 	06 and 18 	0 to 90 by 3
        steps: list = list(range(0, 91, 3))
        print("Fetching 90-hr Forecast")

    coords = np.array([config['geo_coordinates']['latitude'],
                       config['geo_coordinates']['longitude']])
    # place a rectangle over the region to be used for forecast
    grid = create_grid(coords, spatial_resolution)

    if not os.path.exists(target):
        client = Client()
        results = client.retrieve(
            step=steps,
            type="fc",  # default
            param=params,
            # levelist=levelist,
            model="ifs",  # ifs for the physics-driven model and aifs for the data-driven model
            resol="0p25",
            # preserve_request_order=True,  # ignored anyway
            target=target,
            #date='20241118',
            #time=00
        )
        print(
            "Target file: {0}\n"
            "Forecast Run (base time): {1}\n"
            "URL(s) requested: {2}\n"
            .format(results.target, results.datetime, results.urls)
        )
        date_creation = results.datetime.strftime("%Y%m%d%H%M")
    os.chmod(target, 0o666)  # docker owner is root, anyone can delete

    fsss = pygrib.open(target)
    fss = fsss.read()
    fsss.close()
    for item in fss:
        print(item)
        data, lats, lons = item.data(**grid)
        nearest_neighbor = RegularGridInterpolator(
            (lats[:, 0], lons[0, :]),
            data,
            method='linear'
        )
        value_at_coordinates = list(nearest_neighbor(coords))[0]
        dt_str = "{}{:04d}".format(
                item['validityDate'],
                item['validityTime']
            )
        # create a global dict
        try:
            dict_x[item['name']]['time'].append(dt_str)
            dict_x[item['name']]['value'].append(value_at_coordinates)
        except KeyError:
            dict_x[item['name']] = {
                "unit": item['units'],
                "time": [dt_str],
                "value": [value_at_coordinates]
            }

        if not date_creation:
            date_creation = "{}{:04d}".format(
                item["dataDate"],
                item["dataTime"]
            )  # grab from last message if temp file exists

    print(
        json.dumps(
        {date_creation: dict_x},
        indent=2,
        sort_keys=True
        )
    )
    write_log(datetimestr=date_creation,
              forecast=dict_x)

    if not delete and os.path.exists("{}/{}".format(DATA_DIR, file_default)):
        os.remove("{}/{}".format(DATA_DIR, file_default))
        print("File '{}' deleted".format(file_default))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Downloads weather forecasts from ECMWF")
    parser.add_argument(
        '-e',
        '--extended',
        action="store_true",
        help="Fetch 10-day Forecast at 00 or 12 hrs, 90-hr Forecast otherwise"
    )
    parser.add_argument(
        '-d',
        '--delete',
        action="store_true",
        help="No deletion of temporary 'data.grib2' file, default=delete)"
    )

    main(
        extended=parser.parse_args().extended,
        delete=parser.parse_args().delete
    )
