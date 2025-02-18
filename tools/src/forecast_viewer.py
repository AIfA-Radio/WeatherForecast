#!/usr/bin/env python

"""
Forecast quick viewer of the ECMWF and GFS forecast parameter values provided in
forecast.json
"""

import os
import sys
import re
import signal
import json
import argparse
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from matplotlib.backend_bases import (KeyEvent, PickEvent, MouseButton,
                                      MouseEvent)
from matplotlib.figure import Figure

# data directory relative to source
DATA_DIR = "{}/../../".format(os.path.dirname(os.path.realpath(__file__)))
PICKRADIUS = 5  # Points. How close the click needs to be to trigger an event.


class _Onpick(object):
    """
    actions to be performed on canvas.mpl_connect events
    """

    def __init__(
            self,
            fig: Figure,
            map_legend_to_ax: dict
    ):
        self.fig = fig
        self.map_legend_to_ax = \
            map_legend_to_ax if map_legend_to_ax is not None else dict()

    def onpick(
            self,
            event: PickEvent
    ) -> None:
        """
        toggle individual plots (in-)visible if line is clicked in legend
        :param event: called through canvas.mpl_connect
        :return:
        """
        legend_line = event.artist
        # Do nothing if the source of the event is not a legend line.
        if legend_line not in self.map_legend_to_ax:
            return
        ax_line = self.map_legend_to_ax[legend_line]
        visible = not ax_line.get_visible()
        ax_line.set_visible(visible)
        # Change the alpha on the line in the legend, so we can see what lines
        # have been toggled.
        legend_line.set_alpha(1.0 if visible else 0.2)
        self.fig.canvas.draw()

    def invert(
            self,
            event: MouseEvent
    ) -> None:
        """
        toggle all plots (in-)visible on right mouse button
        :param event: called through canvas.mpl_connect
        :return:
        """
        if event.button is MouseButton.RIGHT:
            for legend_line, ax_line in self.map_legend_to_ax.items():
                visible = not ax_line.get_visible()
                ax_line.set_visible(visible)
                # Change the alpha on the line in the legend, so we can see
                # what lines have been toggled.
                legend_line.set_alpha(1.0 if visible else 0.2)
                self.fig.canvas.draw()


def press_key(event: KeyEvent) -> None:
    """
    exit all plot on key 1
    :param event: called through canvas.mpl_connect
    :return:
    """
    if event.key == '1':
        plt.close('all')


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
    :param provider: weather forecast provider ECMWF | GFS
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

    dict_fig: dict = dict()

    match provider:
        case "ECMWF":
            log_file = "{}/ecmwf-opendata/data/forecast.json".format(DATA_DIR)
        case  "GFS":
            log_file = "{}/gfs/data/forecast.json".format(DATA_DIR)
        case "GFS-DOWNSIZED":
            log_file = "{}/gfs-downsized/data/forecast.json".format(DATA_DIR)
        case _:
           raise NotImplementedError("Wrong provider!")

    dict_x = read_log(log_file=log_file)

    after = datetimestr if datetimestr else datetime.strftime(
        datetime.now(timezone.utc), '%Y%m%d%H%M'
    )

    for issue_date, forecast in dict_x.items():  # loop through forecast dates
        for item, values in forecast.items():  # loop through parameters
            # disregard if most recent datapoint is before after date
            if values['time'][-1] < after:
                print("Disregarded Forecast - Issue Date: {}, Parameter: {}"
                      .format(issue_date, item))
                continue
            print("Issue Date: {}, Parameter: {}".format(issue_date, item))

            converted_dates = [
                datetime.strptime(i, '%Y%m%d%H%M') for i in values['time']
            ]

            # define parameters at first time
            if not dict_fig.get(item):
                fig, ax = plt.subplots()
                dict_fig[item] = {
                    "fig": fig,
                    "ax": ax,
                    "lines": list(),
                    "values": values['unit'],
                    "map_legend_to_ax": dict()
                }

            dict_fig[item]['lines'].append(
                # plot each line and append line to lines
                dict_fig[item]['ax'].plot(
                    converted_dates,
                    values['value'],
                    label=issue_date[:-2])[0]
            )

    for item in dict_fig.keys():
        dict_fig[item]['ax'].set_title(item)
        dict_fig[item]['ax'].set_ylabel(dict_fig[item]['values'])
        dict_fig[item]['ax'].set_xlabel("Time")
        dict_fig[item]['leg'] = dict_fig[item]['ax'].legend(
            loc='upper left',
            bbox_to_anchor=(1, 1),
            fancybox=True,
            shadow=True
        )
        for legend_line, ax_line in zip(
                dict_fig[item]['leg'].get_lines(),
                dict_fig[item]['lines']):
            # Enable picking on the legend line.
            legend_line.set_picker(PICKRADIUS)
            dict_fig[item]['map_legend_to_ax'][legend_line] = ax_line

        dict_fig[item]['on_pick'] = _Onpick(
            fig=dict_fig[item]['fig'],
            map_legend_to_ax=dict_fig[item]['map_legend_to_ax']
        )

        dict_fig[item]['leg'].set_draggable(True)
        # close on key 1
        dict_fig[item]['fig'].canvas.mpl_connect(
            'key_press_event',
            press_key
        )
        # toggle visibility of individual line
        dict_fig[item]['fig'].canvas.mpl_connect(
            'pick_event',
            dict_fig[item]['on_pick'].onpick
        )
        # toggle visibilities of all lines
        dict_fig[item]['fig'].canvas.mpl_connect(
            'button_press_event',
            dict_fig[item]['on_pick'].invert
        )

    print(
        "\nClose all figures by pressing key '1'."
        "\nClick right mouse button to toggle visibilities of all lines."
        "\nClick on individual line in legend to toggle its visibility."
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
        choices=["ECMWF", "GFS", "GFS-DOWNSIZED"],
        help="Select forecast provider (mandatory)"
    )

    main(
        provider=parser.parse_args().provider,
        datetimestr=parser.parse_args().datetimestr
    )
