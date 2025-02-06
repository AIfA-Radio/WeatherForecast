#!/usr/bin/env python

"""
The NOAA Big Data Program also provides access to gridded 0.25°- and 0.5°-resolution
analysis and forecast data in a trailing 30-day window in the AWS Open Data Registry for GFS.
Download GFS forecast data
https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/ via HTTP
"""

import pygrib
import os
import json
from numpy import array as np_array
from multiprocessing import Queue
from scipy.interpolate import RegularGridInterpolator
# internal
from gfs_fc_aux import data_file, config, defined_kwargs


def write_forecast(
        datetimestr: str,
        forecast: dict
) -> None:
    """
    update forecast.json
    :param datetimestr: YYYYMMDDHH
    :param forecast:
    :return: None
    """
    if not os.path.exists(data_file):
        with open(data_file, "w") as create_empty:
            json.dump({}, create_empty)
            os.chmod(data_file, 0o666)  # docker owner is root, anyone can delete
    with open(data_file, "r+") as jsonFile:
        data = json.load(jsonFile)
        data[datetimestr] = forecast
        jsonFile.seek(0)  # rewind
        json.dump(data,
                  jsonFile,
                  indent=2,
                  sort_keys=True)
        jsonFile.truncate()


def create_grid(
        coordinates: np_array,
        lats: np_array,
        lons: np_array
) -> dict:
    """
    create square in the coordinate grid that encloses location
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
    extract grib2 file according to select parameter
    :param target: full path
    :param q: queue per fc hour for multiprocessing
    :return:
    """
    fs: list = list()
    result: dict = dict()

    coords = np_array([config['geo_coordinates']['latitude'],
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
