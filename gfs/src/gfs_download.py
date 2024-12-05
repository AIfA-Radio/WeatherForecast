#!/usr/bin/env python

"""
The NOAA Big Data Program also provides access to gridded 0.25°- and 0.5°-resolution
analysis and forecast data in a trailing 30-day window in the AWS Open Data Registry for GFS.
Download GFS forecast data
https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/
via FTP into a GRIB2 file and extract each parameter
"""

import pygrib
import os
import sys
import re
import argparse
from scipy.interpolate import RegularGridInterpolator
import numpy as np
import json
from ftplib import FTP
import math

NO_FILES: int = 209  # total number to download from https://www.nco.ncep.noaa.gov/pmb/products/gfs/
NO_FILE_TEST: int = 3  # test option "-t" stops after NO_FILE_TEST grib2 files
SPATIAL_RESOLUTION: float = 0.25  # spatial resolution of the model

# data directory relative to source
SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = "{}/../data".format(SOURCE_DIR)
LOG_DIR = "{}/../logs".format(SOURCE_DIR)
FTP_HOST = "ftp.ncep.noaa.gov"
PATH = "/pub/data/nccf/com/gfs/prod"


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
        resolution: float
) -> dict:
    """
    create grid on coordinates
    :param coordinates:
    :param resolution:
    :return:
    """

    def transpose(x): return x % 360  # [0, 360[

    def floor(x): return math.floor(x / resolution) * resolution

    def ceil(x): return math.ceil(x / resolution) * resolution

    return {
        "lat1": max(-90, floor(coordinates[0])),
        "lat2": min(90, ceil(coordinates[0])),
        "lon1": transpose(floor(coordinates[1])),
        "lon2": transpose(ceil(coordinates[1]))
    }


def extract(target: str) -> dict:
    fs: list = []
    tmp: dict = {}
    config_file = "{}/parameter.json".format(DATA_DIR)
    with open(config_file, "r") as f:
        config = json.load(f)
    coords = np.array([config['geo_coordinates']['latitude'],
                       (config['geo_coordinates']['longitude'] + 360) % 360])
    # place a rectangle over the region to be used for forecast
    grid = create_grid(coordinates=coords,
                       resolution=SPATIAL_RESOLUTION)

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
        tmp[item['name']] = {
            "unit": item['units'],
            "time": [dt_str],
            "value": [value_at_coordinates]
        }
    fsss.close()

    return tmp


def ftp_fetch(
        datetimestr: str = None,
        *,
        test: bool = False,
        subset: int = 1
) -> None:
    """
    be absolutely careful
    !!! This routine will download 115 GB of data from GFS' NCEP server of NOAA !!!
    :param datetimestr: YYYYMMDDHH forecast time to be downloaded overwrites
    the current date & times if specified
    :param test: test with few files only
    :param subset: download every subset^th hour only
    :return:
    """
    targets: list = []
    msg: str = None
    cnt_files: int = 0
    dict_x: dict = {}
    regex = re.compile(
        r"^gfs.t[0-9]{2}z.pgrb2.0p25.f([0-9]{3})$"
    )
    regex_datetime = re.compile(
        r"^(20[234][0-9])(0?[1-9]|1[012])(0[1-9]|[12]\d|3[01])(00|06|12|18)$"
    )

    try:
        ftp = FTP(FTP_HOST)
        ftp.login()
        if datetimestr:
            l_datetime = re.findall(regex_datetime, datetimestr)
            if l_datetime:
                date_string = "".join(l_datetime[0][:3])
                last_hour = l_datetime[0][3]
            else:
                raise ValueError("Invalid Date/Time provided.")
            ftp.cwd("{}/gfs.{}".format(PATH, date_string))
        else:
            ftp.cwd(PATH)
            last_entry = sorted(list(filter(
                lambda x: x.startswith("gfs."), ftp.nlst()
            )))[-1]
            ftp.cwd(last_entry)
            date_string = last_entry.lstrip("gfs.")
            last_hour = ftp.nlst()[-1]
            # reuse datetime for current date/time
            datetimestr = "{}{}".format(date_string, last_hour)
        ftp.cwd("{}/atmos".format(last_hour))
        for filename in sorted(ftp.nlst()):
            if re.search(regex, filename):
                targets.append(filename)
        print("Number of files to download: {}".format(len(targets)))
        # print(targets)
        datetimestr += "00"  # append 00 minutes
        if len(targets) == NO_FILES:
            msg = "Success"
            for target in targets:
                hrs = int(re.findall(regex, target)[0])
                if hrs % subset != 0: # download every ?th hour
                    print("Skipping hour: {} forecast".format(hrs))
                    continue
                print("File '{}' download started".format(target))
                with open(
                        "{}/{}".format(DATA_DIR, target),
                        'wb'
                ) as fp:
                    ftp.retrbinary("RETR {}".format(target), fp.write)
                print("File '{}' downloaded".format(target))
                # docker owner is root, anyone can delete in case of failure
                os.chmod("{}/{}".format(DATA_DIR, target), 0o666)

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
                if test: print(
                    json.dumps(
                        {datetimestr: dict_x},
                        indent=2,
                        sort_keys=True,
                        default=str
                    )
                )
                write_forecast(datetimestr=datetimestr,
                               forecast=dict_x)  # always update
                if test and cnt_files == NO_FILE_TEST:  # for testing -d option
                    msg = "File set is incomplete due to option"
                    break
        else:
            msg = "File set is incomplete. Try again later."
    except Exception as e:
        msg = str(e)
        sys.exit(1)
    finally:
        print("Datetime {}: {}".format(datetimestr, msg))


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
        help="Test with first {} files only, default=all".format(NO_FILE_TEST)
    )
    parser.add_argument(
        '-s',
        '--subset',
        type=int,
        default=1,
        help="Download every ?(2nd, 3rd, 4th, ...) hour, default=entire set"
    )

    ftp_fetch(
        datetimestr=parser.parse_args().datetimestr,
        test=parser.parse_args().test,
        subset=parser.parse_args().subset
    )
