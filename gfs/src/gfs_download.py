#!/usr/bin/env python

"""
"""

import pygrib
import os
import sys
import re
from datetime import date
import argparse
from scipy.interpolate import RegularGridInterpolator
import numpy as np
import json
from ftplib import FTP
import math

NO_FILES: int = 209
NO_FILE_TEST: int = 2  # stops download after this

# data directory relative to source
SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = "{}/../data".format(SOURCE_DIR)
LOG_DIR = "{}/../logs".format(SOURCE_DIR)
FTP_HOST = "ftp.ncep.noaa.gov"
PATH = "/pub/data/nccf/com/gfs/prod"


def defined_kwargs(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None}


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
        return x % 360  # [0, 360]

    return {
        "lat1": max(-90, math.floor(coordinates[0] - 4 * res)),
        "lat2": min(90, math.ceil(coordinates[0] + 4 * res)),
        "lon1": flip(math.floor(coordinates[1] - 4 * res)),
        "lon2": flip(math.ceil(coordinates[1] + 4 * res))
    }


def extract(target: str) -> dict:
    fs: list = []
    tmp: dict = {}
    config_file = "{}/parameter.json".format(DATA_DIR)
    config = json.load(open(config_file, "r"))
    spatial_resolution: float = 0.25
    coords = np.array([config['geo_coordinates']['latitude'],
                       (config['geo_coordinates']['longitude'] + 360) % 360])
    # place a rectangle over the region to be used for forecast
    grid = create_grid(coordinates=coords,
                       res=spatial_resolution)
    # print(grid, coords)

    fsss = pygrib.open("{}/{}".format(DATA_DIR, target))
    # for item in fsss:
    #     print(item["shortName"], item)
    # print("\n")
    for item in config['parameter']:
        params = defined_kwargs(
            shortName=item.get('shortName'),
            typeOfLevel=item.get('typeOfLevel'),
            level=item.get('level')
        )
        fs.extend(fsss.select(**params))

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
        tmp[ item['name'] ] = {
            "unit": item['units'],
            "time": [dt_str],
            "value": [value_at_coordinates]
        }
    fsss.close()

    return tmp


def ftp_fetch(
        datetimestr: str = None,
        test: bool = False
) -> None:
    """
    be absolutely careful
    !!! This routine will download 115 GB of data from GFS' NCEP server of NOAA !!!
    :param datetimestr: YYYYMMDDHH forecast time to be downloaded overwrites
    :param test: test with few files only
    the current date & times if specified
    :return:
    """
    l_datetime: list = []
    last_hour: str = None
    targets: list = []
    msg: str = None
    cnt_files: int = 0
    dict_x: dict = {}

    regex = re.compile(r"^gfs.t[0-9]{2}z.pgrb2.0p25.f[0-9]{3}$")
    regex_datetime = re.compile(
        r"^(20[234][0-9])(0?[1-9]|1[012])(0[1-9]|[12]\d|3[01])(00|06|12|18)$"
    )

    if datetimestr:
        l_datetime = re.findall(regex_datetime, datetimestr)
        if l_datetime:
            date_string = "".join(l_datetime[0][:3])
            last_hour = l_datetime[0][3]
        else:
            raise ValueError("Invalid Date/Time provided.")
    else:
        date_string = "{}{}{}".format(
            date.today().year,
            date.today().month,
            date.today().day
        )

    try:
        ftp = FTP(FTP_HOST)
        ftp.login()
        ftp.cwd("{}/gfs.{}".format(PATH, date_string))
        if not l_datetime:
            last_hour = ftp.nlst()[-1]
            # reuse datetime for current date/time
            datetimestr = "{}{}".format(date_string, last_hour)
        ftp.cwd("{}/atmos".format(last_hour))
        for filename in sorted(ftp.nlst()):
            if re.search(regex, filename):
                targets.append(filename)
        print("Number of files to download: {}".format(len(targets)))
        # print(targets)
        if len(targets) == NO_FILES:
            msg = "Success"
            for target in targets:
                with open(
                        "{}/{}".format(DATA_DIR, target),
                        'wb'
                ) as fp:
                    ftp.retrbinary("RETR {}".format(target), fp.write)
                print("{} downloaded".format(target))

                r = extract(target=target)

                # create a global dict
                if dict_x:
                    for k, v in r.items():
                        dict_x[k]['time'].extend(v['time'])
                        dict_x[k]['value'].extend(v['value'])
                else:
                    dict_x = r
                if os.path.exists("{}/{}".format(DATA_DIR, target)):
                    os.remove("{}/{}".format(DATA_DIR, target))
                    print("File '{}' deleted".format(target))
                cnt_files += 1
                datetimestr += "00"  # append 00 minutes
                print(
                    json.dumps(
                        {datetimestr: dict_x},
                        indent=2,
                        sort_keys=True,
                        default=str
                    )
                )
                write_log(datetimestr=datetimestr,
                          forecast=dict_x)  # always update
                if test and cnt_files > NO_FILE_TEST:  # for testing -d option
                    break
        else:
            msg = "File set is incomplete"
    except Exception as e:
        msg = str(e)
        sys.exit(1)
    finally:
        print("{}: {}".format(datetimestr, msg))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Downloads weather forecasts from GFS")
    parser.add_argument(
        '-d',
        '--datetimestr',
        type=str,
        help="Datetime string (YYYYMMDDHH), default=current datetime"
    )
    parser.add_argument(
        '-t',
        '--test',
        action="store_true",
        help="Test with 3 files only, default=all"
    )

    ftp_fetch(
        datetimestr=parser.parse_args().datetimestr,
        test=parser.parse_args().test
    )
