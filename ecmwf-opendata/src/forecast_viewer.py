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

import os
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backend_bases import KeyEvent
import json

# data directory relative to source
DATA_DIR = "{}/../data".format(os.path.dirname(os.path.realpath(__file__)))


def press_key(event: KeyEvent) -> None:
    if event.key == '1':
        plt.close('all')


def read_log() -> dict:
    log_file = "{}/forecast.json".format(DATA_DIR)
    if not os.path.exists(log_file):
        raise FileNotFoundError
    jsonfile = open(log_file, "r")

    return json.load(jsonfile)


def main() -> None:
    dict_x = read_log()
    for issue_date, forecast in dict_x.items():
        for item, values in forecast.items():
            print("Issue Date: {}, Parameter: {}".format(issue_date, item))
            converted_dates = [
                datetime.strptime(i, '%Y%m%d%H%M') for i in values['time']
            ]
            fig = plt.figure(item)
            plt.ylabel(values['unit'])
            plt.xlabel("Time")
            plt.plot(converted_dates, values['value'])
            fig.canvas.mpl_connect('key_press_event', press_key)
    print("\nClose all figures by pressing key '1'")
    plt.show()


if __name__ == "__main__":
    main()
