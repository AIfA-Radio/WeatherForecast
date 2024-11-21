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
from datetime import datetime
import argparse
import matplotlib.pyplot as plt
from matplotlib.backend_bases import KeyEvent
from scipy.interpolate import RegularGridInterpolator
import numpy as np
import json

DATA_DIR = os.path.dirname(os.path.realpath(__file__))  # current dir


def press_key(event: KeyEvent) -> None:
    if event.key == '1':
        plt.close('all')


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
    log_file = "{}/data/forecast.json".format(DATA_DIR)
    if not os.path.exists(log_file):
        with open(log_file, "w") as create_empty:
            json.dump({}, create_empty)
            os.chmod(log_file, 0o666)  # owner is root, however any can delete
    with open(log_file, "r+") as jsonFile:
        data = json.load(jsonFile)
        data[datetimestr] = forecast
        jsonFile.seek(0)  # rewind
        json.dump(data, jsonFile, indent=4, sort_keys=True)
        jsonFile.truncate()


def main(
        *,
        file: str,
        extended: bool
) -> None:
    date_creation = None
    target: str = "{}/data/{}".format(DATA_DIR, file)
    params: list = ["tcwv", "sp", "2t", "2d", "10u", "10v"]
    if extended:
        # HRES 	00 and 12 	0 to 144 by 3, 144 to 240 by 6
        steps: list = list(range(0, 144, 3)) + list(range(144, 241, 6))
        print("Fetching 10-day Forecast")
    else:
        # HRES 	06 and 18 	0 to 90 by 3
        steps: list = list(range(0, 91, 3))
        print("Fetching 90-hr Forecast")
    # place a rectangle over the region to be used for forecast
    grid: dict = {"lat1":-23., "lat2":-22., "lon1":-68., "lon2":-67.}
    # CCAT coordinates. Correct?
    chajnantor_coords = np.array([-22.72712, -67.33196])
    dict_x: dict = {}

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
    os.chmod(target, 0o666)  # owner is root, however any can delete

    fsss = pygrib.open(target)
    fss = fsss.read()
    fsss.close()
    for item in fss:
        print(item)
        data, lats, lons = item.data(**grid)
        nearest_neighbor = RegularGridInterpolator(
            (lats[:,0], lons[0,:]),
            data,
            method='linear'
        )
        value_at_coordinates = list(nearest_neighbor(chajnantor_coords))[0]
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

        date_creation = "{}{:04d}".format(
            item["dataDate"],
            item["dataTime"]
        )

    print(
        json.dumps(
        {date_creation: dict_x},
        indent=2,
        sort_keys=True
        )
    )
    write_log(datetimestr=date_creation,
              forecast=dict_x)

    for item, values in dict_x.items():
        converted_dates = [
            datetime.strptime(i, '%Y%m%d%H%M') for i in values['time']
        ]
        print("Parameter: {}".format(item))
        fig = plt.figure(item)
        plt.ylabel(values['unit'])
        plt.xlabel("Time")
        plt.plot(converted_dates, values['value'])
        fig.canvas.mpl_connect('key_press_event', press_key)
    print("\nClose all figures by pressing key '1'")
    # plt.show()

    if file == file_default and os.path.exists(
            "{}/data/{}".format(DATA_DIR, file_default)
    ):
        os.remove("{}/data/{}".format(DATA_DIR, file_default))
        print("File '{}' deleted".format(file_default))


if __name__ == "__main__":
    file_default = "data.grib2"
    parser = argparse.ArgumentParser(
        description="Downloads weather forecasts from ECMWF")
    parser.add_argument(
        '-o',
        '--output',
        default=file_default,
        nargs='?',
        help='Output file (.grib2)'
             '(default: data.grib2 will be deleted after exit)')
    parser.add_argument(
        '-e',
        '--extended',
        action="store_true",
        help="Fetch 10-day Forecast at 00 or 12 hrs, 90-hr Forecast otherwise"
    )

    main(
        file=parser.parse_args().output,
        extended=parser.parse_args().extended
    )
