#!/usr/bin/env python

"""
Forecast quick viewer of the ECMWF and GFS wind forecasts provided in
forecast.json
"""

import os
import sys
import signal
import re
import json
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


def read_log(log_file: str) -> dict:
    """
    read forecast JSON file
    :param log_file: location of forecast.json
    :return:
    """
    if not os.path.exists(log_file):
        raise FileNotFoundError
    with open(log_file, "r") as jsonfile:
        res = json.load(jsonfile)

    return res


def main(
        provider: str,
        datetimestr: str
) -> None:
    """
    plots forecasts after datetime string (YYYYMMDDHH), default=current date
    :param provider: weather forecast provider ecmwf | gfs
    :param datetimestr: format YYYYMMDDHH
    :return:
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    regex_datetime = re.compile(
        r"^(20[234][0-9])(0?[1-9]|1[012])(0[1-9]|[12]\d|3[01])(00|06|12|18)$"
    )
    if datetimestr:
        if not re.match(regex_datetime, datetimestr):
            raise ValueError("Invalid Date/Time provided.")

    if provider == "ecmwf":
        log_file = "{}/ecmwf-opendata/data/forecast.json".format(DATA_DIR)
    elif provider == "gfs":
        log_file = "{}/gfs/data/forecast.json".format(DATA_DIR)
    else:
        raise NotImplementedError("Wrong provider!")

    dict_x = read_log(log_file=log_file)

    try:
        last_issue_date = sorted(
            {k: v for k, v in dict_x.items() if k == datetimestr + "00"}.items()
        )[0] \
            if datetimestr else sorted(
            {k: v for k, v in dict_x.items()}.items()
        )[-1]
        print("Issue Date: {}".format(last_issue_date[0]))
        if provider == "ecmwf":
            u = last_issue_date[1]['10 metre U wind component']['value']
            v = last_issue_date[1]['10 metre V wind component']['value']
            time = last_issue_date[1]['10 metre U wind component']['time']
        else:
            u = last_issue_date[1]['U component of wind']['value']
            v = last_issue_date[1]['V component of wind']['value']
            time = last_issue_date[1]['U component of wind']['time']
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
    fig.suptitle("Windspeed [m/s] and Direction [°] at Cerro Chajnantor")

    def animate(i):
        if i == number_entries - 1:
            ax.clear()
        fig.canvas.manager.set_window_title(
            datetime.strptime(time[i], '%Y%m%d%H%M')
        )
        ax.set_rlim(0, math.ceil(V_MAX + 0.5))
        fig.suptitle("Windspeed [m/s] and Direction [°] at Cerro Chajnantor")
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
        repeat=True,
        blit=False,
        frames=number_entries,
        interval=1000
    )

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
             "default=current datetime"
    )
    parser.add_argument(
        '-p',
        '--provider',
        type=str,
        required=True,
        choices=["ecmwf", "gfs"],
        help="Select provider 'ecmwf' | 'gfs', defualt=ecmwf"
    )

    main(
        provider=parser.parse_args().provider,
        datetimestr=parser.parse_args().datetimestr
    )
