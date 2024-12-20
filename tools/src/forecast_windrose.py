#!/usr/bin/env python

"""
Forecast quick viewer of the ECMWF and GFS wind forecasts provided in
forecast.json
"""

import os
import sys
import re
import json
import signal
import argparse
import matplotlib.pyplot as plt
import numpy as np
import math
from matplotlib import colormaps
from matplotlib import animation
from datetime import datetime

# data directory relative to source
DATA_DIR = "{}/../../".format(
    os.path.dirname(
        os.path.realpath(__file__)
    ))
COLOR_MAP = 'jet'
V_MAX = 20.  # max abs. windspeed on windrose
TITLE = "{} Windspeed [m/s] and (from) Direction [°] at {}"


def read_json(json_file: str) -> dict:
    """
    read forecast JSON file
    :param json_file: location of forecast.json
    :return:
    """
    if not os.path.exists(json_file):
        raise FileNotFoundError
    with open(json_file, "r") as jsonfile:
        res = json.load(jsonfile)

    return res


def main(
        provider: str,
        datetimestr: str = None,
        video: bool = False
) -> None:
    """
    plots forecasts after datetime string (YYYYMMDDHH), default=current date
    :param provider: weather forecast provider ECMWF | GFS
    :param datetimestr: format YYYYMMDDHH
    :param video: if video is downloaded to mp4 
    :return:
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    regex_datetime = re.compile(
        r"^(20[234][0-9])(0?[1-9]|1[012])(0[1-9]|[12]\d|3[01])(00|06|12|18)$"
    )
    if datetimestr:
        if not re.match(regex_datetime, datetimestr):
            raise ValueError("Invalid Date/Time provided.")

    if provider == "ECMWF":
        forecast_file = "{}/ecmwf-opendata/data/forecast.json".format(DATA_DIR)
        parameter_file = "{}/ecmwf-opendata/data/parameter.json".format(DATA_DIR)
        u_key = "10 metre U wind component"
        v_key = "10 metre V wind component"
    elif provider == "GFS":
        forecast_file = "{}/gfs/data/forecast.json".format(DATA_DIR)
        parameter_file = "{}/gfs/data/parameter.json".format(DATA_DIR)
        u_key = "U component of wind"
        v_key = "V component of wind"
    else:
        raise NotImplementedError("Wrong provider!")

    dict_x = read_json(json_file=forecast_file)
    location = read_json(json_file=parameter_file)["geo_coordinates"]["location"]

    try:
        last_issue_date = sorted(
            {k: v for k, v in dict_x.items() if k == datetimestr + "00"}.items()
        )[0] \
            if datetimestr else sorted(
            {k: v for k, v in dict_x.items()}.items()
        )[-1]
        print("Issue Date: {}".format(last_issue_date[0]))
        u = last_issue_date[1][u_key]['value']
        v = last_issue_date[1][v_key]['value']
        time = last_issue_date[1][u_key]['time']
    except KeyError:
        raise KeyError("Wind forecast data not found!")
    except IndexError:
        raise IndexError("Forecast date/time not found in forecast.json!")

    v_abs = (np.sqrt(np.power(u, 2) + np.power(v, 2)))
    v_abs_max = max(v_abs)  # ToDo max be used
    number_entries = len(v_abs)
    v_dir = (np.pi + np.atan2(u, v)) % (2 * np.pi)

    fig = plt.figure(figsize=(8, 8))
    # initialize settings
    ax = plt.subplot(projection='polar')
    ax.set_rlim(0, math.ceil(V_MAX + 0.5))
    fig.suptitle(TITLE.format(provider, location))

    def animate(i):
        if not video and i == number_entries - 1:
            ax.clear()
        fig.suptitle(TITLE.format(provider, location))
        ax.set_title(datetime.strptime(time[i], '%Y%m%d%H%M'))
        ax.set_rlim(0, math.ceil(V_MAX + 0.5))
        ax.bar(
            x=v_dir[i],
            height=v_abs[i],
            width=np.pi / 16,
            bottom=0.0,
            color=colormaps[COLOR_MAP](v_abs[i] / V_MAX),
            alpha=0.5
        )

    anim = animation.FuncAnimation(
        fig,
        animate,
        repeat=(not video),
        blit=False,
        frames=range(number_entries),
        interval=250  # msec
    )
    if video:
        ffwriter = animation.FFMpegWriter()
        anim.save(
            '{}/tools/plots/forecast_windrose.mp4'.format(DATA_DIR),
            writer=ffwriter)

    plt.show()
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plots downloaded weather forecasts from ECMWF or GFS.")
    parser.add_argument(
        '-d',
        '--datetimestr',
        type=str,
        help="Start forecasts after datetime string (YYYYMMDDHH), "
             "default=current"
    )
    parser.add_argument(
        '-p',
        '--provider',
        type=str,
        required=True,
        choices=["ECMWF", "GFS"],
        help="Select forecast provider (mandatory)"
    )
    parser.add_argument(
        '-v',
        '--video',
        help="Store video on tools/plots/plot.mp4, default=No",
        action='store_true'
    )

    main(
        provider=parser.parse_args().provider,
        datetimestr=parser.parse_args().datetimestr,
        video=parser.parse_args().video,
    )
