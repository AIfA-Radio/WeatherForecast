#!/usr/bin/env python

"""
The NOAA Big Data Program also provides access to gridded 0.25°- and 0.5°-resolution
analysis and forecast data in a trailing 30-day window in the AWS Open Data Registry for GFS.
Download GFS forecast data
https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/ via HTTP
"""

import pygrib
import os
import numpy as np
import json
from multiprocessing import Queue
from scipy.interpolate import RegularGridInterpolator

# data directory relative to source
SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = "{}/../data".format(SOURCE_DIR)
LOG_DIR = "{}/../logs".format(SOURCE_DIR)


config_file = "{}/parameter.json".format(DATA_DIR)
with open(config_file, "r") as f:
    config = json.load(f)


def defined_kwargs(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None}


def write_forecast(
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
        lats: np.array,
        lons: np.array
) -> dict:
    """
    create square in the coordinate grid that enclosed location
    :param coordinates:
    :param lats:
    :param lons:
    :return:
    """
    lat1, lat2, lon1, lon2 = -90., 90., 0., 360.
    # lats scales from 90° to -90°
    for i in range(len(lats)):
        if coordinates[0] > lats[i]:
            lat1 = lats[i]
            break
        else:
            lat2 = lats[i]
    # longs scales from 0° to 360°  # for GFS, ECMWF ranges from -180° to 180°
    for i in range(len(lons)):
        if coordinates[1] < lons[i]:
            lon2 = lons[i]
            break
        else:
            lon1 = lons[i]

    return {
        "lat1": lat1,
        "lat2": lat2,
        "lon1": lon1,
        "lon2": lon2
    }


def extract(
        target: str,
        q: Queue = None
) -> tuple[bool, dict] | None:
    """

    :param target: full path
    :param q: queue for multiprocessing
    :return:
    """
    fs: list = list()
    result: dict = dict()

    coords = np.array([config['geo_coordinates']['latitude'],
                       (config['geo_coordinates']['longitude'] + 360) % 360])

    # open grib file
    fsss = pygrib.open(target)
    fsss.seek(0)
    item = fsss.read(1)[0]
    # date of creation
    date_creation_str = "{}{:04d}".format(
        item['dataDate'],
        item['dataTime']
    )
    # figure out spatial resolution from 1st item
    # print(item.values.shape)
    resolution = 360 / item.values.shape[1]  # longitude
    print(f"Spatial resolution: {resolution} degree")
    lats, lons = item.latlons()
    # place a rectangle over the region to be used for forecast
    grid = create_grid(coordinates=coords,
                       lats=lats[:, 0],
                       lons=lons[0, :])

    for item in config['parameter']:
        params = defined_kwargs(
            shortName=item.get('shortName'),
            typeOfLevel=item.get('typeOfLevel'),
            level=item.get('level'),
            stepType=item.get('stepType')
            # ... more keys here if applicable
        )
        try:
            fs.extend(fsss.select(**params))
        except ValueError:
            print("Filter parameter ", params, "not found. Skipping ...")

    fsss.close()

    for item in fs:
        print(item["shortName"], item)
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
        result[item['name']] = {
            "unit": item['units'],
            "time": [dt_str],
            "value": [value_at_coordinates]
        }

    os.remove(target)  # ToDo keep or remove
    print("Target file '{}' deleted".format(target))

    if q:
        q.put((date_creation_str, result))
    else:
        return date_creation_str, result
