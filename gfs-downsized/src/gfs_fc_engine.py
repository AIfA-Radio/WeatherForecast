#!/usr/bin/env python

"""

draft version, 2025-02-03
"""

import json
import sys
import os
from gfs_fc_client import Client
from argparse import ArgumentParser
from multiprocessing import Process, Queue
# internal
from gfs_fc_download import extract, write_forecast
from gfs_fc_aux import defined_kwargs, CONFIG, STEPS


def main(
        process: bool = False,
        keep_target: bool = False
) -> None:
    """

    :param process: engage multiprocessing, if True
    :param keep_target: keep target, if True
    :return:
    """
    dict_x = dict()

    def collect(r: dict) -> dict:
        for k, v in r.items():
            try:
                dict_x[k]['time'].extend(v['time'])
                dict_x[k]['value'].extend(v['value'])
            except KeyError:
                dict_x[k] = v
        return dict_x
    # end module collect

    date_creation_string: str = None
    ps = list()  # list of processes
    qs = list()  # list of queues

    client = Client(
        # grid: mandatory [SLS|GLOB]
        grid=CONFIG["grid"],
        **defined_kwargs(
            # if parameter missing, entire parameter set
            parameter=CONFIG.get('parameter'),
            # validity optional, list of substrings, e.g. "fcst" and/or "anl"
            validity=CONFIG.get('validity'),
            # only used with grid="GLOB"
            paramset=CONFIG.get('paramset'),
            # only used with grid="GLOB"
            resol=CONFIG.get('resol'),
            # if missing, most recent date and/or time with data available
            date=CONFIG.get('date'),
            time=CONFIG.get('time')
        )
    )

    for step in CONFIG.get("steps", STEPS):
        results = client.retrieve(
            step=step,
            **defined_kwargs(
                target=CONFIG.get('target')
            )
        )
        # success, match file size(s)
        print(f"File size matched: {results.rc}")
        if not results.target:
            sys.exit(1)

        if process:
            queue = Queue()
            p = Process(target=extract,
                        args=(results.target, queue, keep_target),
                        daemon=True)
            # no join() required
            p.start()
            # renice on raspberry Pi
            os.system("renice -n 19 -p {}".format(p.pid))
            ps.append(p)
            qs.append(queue)
            print("Number of processes: {} alive"
                  .format(sum([i.is_alive() for i in ps])))
        else:
            date_creation_string, res = extract(target=results.target)
            dict_x = collect(res)

    for q in qs:  # collecting from queue
        date_creation_string, res = q.get()
        dict_x = collect(res)

    print(json.dumps(dict_x, indent=2))

    write_forecast(datetimestr=date_creation_string,
                   forecast=dict_x)  # always update entire json

    sys.exit(0)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Downloads weather forecasts from ECMWF")
    parser.add_argument(
        '-p',
        '--process',
        action="store_true",
        help="Apply Multiprocessing, if hardware permits the load."
    )
    parser.add_argument(
        '-k',
        '--keep_target',
        action="store_true",
        help="Deletion of target files disabled."
    )

    main(process=parser.parse_args().process,
         keep_target=parser.parse_args().keep_target)
