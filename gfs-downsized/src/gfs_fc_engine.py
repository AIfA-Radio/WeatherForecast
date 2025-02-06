#!/usr/bin/env python

"""

draft version, 2025-02-03
"""

import json
from gfs_fc_client import Client
from argparse import ArgumentParser
from multiprocessing import Process, Queue
from gfs_fc_retrieve import extract, write_forecast
# internal
from gfs_fc_aux import defined_kwargs, config

STEPS = list(range(1, 121)) + list(range(123, 385, 3))  # 0 step is "anl"


def main(
        process: bool = False
) -> None:
    """

    :param process: engage multiprocessing if True
    :return:
    """
    dict_x: dict = {}

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

    params = defined_kwargs(
        # validity optional, list of substrings, e.g. "fcst" and/or "anl"
        validity=config.get('validity'),
        # only used with grid="GLOB"
        paramset=config.get('paramset'),
        # if missing, most recent date and/or time
        target=config.get('target'),
        # only used with grid="GLOB"
        resol=config.get('resol'),
        parameter=config.get('parameter'),
        date=config.get('date'),
        time=config.get('time')
    )
    steps = config.get("steps")

    # grid: mandatory [SLS|GLOB]
    client = Client(grid=config["grid"])

    for step in steps if steps else STEPS:
        results = client.retrieve(
            step=step,
            **params
        )
        # success, match file size(s)
        print(f"File size matched: {results.rc}")

        if not results.targets:
            exit(1)

        if process:
            queue = Queue()
            p = Process(target=extract,
                        args=(results.targets[0], queue))
            # no join() required
            p.start()
            ps.append(p)
            qs.append(queue)
            print("Number of processes: {} alive"
                  .format(sum([i.is_alive() for i in ps])))
        else:
            date_creation_string, res = extract(target=results.targets[0])
            dict_x = collect(res)
            print(json.dumps(dict_x, indent=2))

    for q in qs:  # collecting from queue if filled
        date_creation_string, res = q.get()
        dict_x = collect(res)
        print(json.dumps(dict_x, indent=2))

    write_forecast(datetimestr=date_creation_string,
                   forecast=dict_x)  # always update

    exit(0)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Downloads weather forecasts from ECMWF")
    parser.add_argument(
        '-p',
        '--process',
        action="store_true",
        help="Apply Multiprocessing, if hardware permits the load."
    )

    main(process=parser.parse_args().process)
