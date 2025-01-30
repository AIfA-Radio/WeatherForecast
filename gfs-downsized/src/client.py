#!/usr/bin/env python
"""

draft version, 2025-01-23
"""
import requests
import json
import os
from time import sleep
from multiurl import download
from datetime import datetime, timedelta, timezone

COMMON = "{_url}/{_model}.{_yyyymmdd}/{_H}/atmos/{_model}.t{_H}z."

SEMI_LAGRANGIAN_GRID = COMMON + "sfluxgrbf{_fc_hour}.{_extension}"
GLOBAL_LONGITUDE_LATITUDE_GRID = COMMON + "{_params}{_set}.{_resol}.f{_fc_hour}"

PATTERNS = {
    "SLS": SEMI_LAGRANGIAN_GRID,
    "GLOB": GLOBAL_LONGITUDE_LATITUDE_GRID
}
URLS = {
    "gfs": "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"
}

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = "{}/../data".format(SOURCE_DIR)
LOG_DIR = "{}/../logs".format(SOURCE_DIR)


class Client(object):
    def __init__(
            self,
            *,
            model="gfs",  # gdas, enkfgdas
            grid="GLOB",
            resol="0p25", # SLS has a resolution of 360 / 1536 !
            verify=True
    ):
        self.model = model
        self.grid = grid
        self.resol = resol
        self.verify = verify
        self.session = requests.Session()
        self.target = "download.grib2"
        self.lower_by_fc = False

    def retrieve(
            self,
            *,
            target=None,
            resol=None,
            **kwargs
    ):
        expected_size = list()
        results = list()
        files = list()
        urls = self._get_urls(resol=resol,
                              **kwargs)
        target = target if target else self.target
        counter = 0
        for url in urls:
            print(url)
            file = "{}{}.grib2".format(
                target.split(".grib2")[0],
                counter)
            files.append(file)  # list of out files
            expected_size.append(sum([j[1] for j in url['parts']]))
            results.append(download(
                **url,
                target="{}/{}".format(DATA_DIR, file),
                verify=self.verify,
                session=self.session
            ))
            os.chmod("{}/{}".format(DATA_DIR, file), 0o666)  # under Docker owner is root
            counter += 1

        return expected_size == results

    def _dateandtime(
            self,
            **kwargs
    ) -> dict:
        """
        set the time at [0|6|12|18] UTC before now. If lower_by_fc scale down
        by -6 hrs.
        :param lower_by_fc:
        :param kwargs:
        :return: kwargs (date and time) modified
        """
        now = datetime.now(timezone.utc)
        time = int(now.strftime("%H"))
        if (kwargs.get('date')
                and (False if kwargs.get("time") in [0, 6, 12, 18] else True)):
            kwargs['time'] = 18  # last fc of the day
        kwargs['date'] = kwargs.get('date', now.strftime("%Y%m%d"))
        kwargs['time'] = kwargs.get('time', time - time % 6)

        assert kwargs['time'] in [0, 6, 12, 18], \
            "Value for time (UTC): [0|6|12|18]"

        if self.lower_by_fc:
            dt = datetime.strptime(
                f"{kwargs['date']}{kwargs['time']}",
                "%Y%m%d%H"
            ) - timedelta(hours=6)  # one fc earlier
            kwargs['date'] = dt.strftime("%Y%m%d")
            kwargs['time'] = int(dt.strftime("%H"))

        return kwargs

    def _get_urls(
            self,
            resol,
            **kwargs
    ) -> list:
        """
        prepare data and configure url string
        :param kwargs:
        :return:
        """
        idx: list = None
        kwargs = self._dateandtime(**kwargs)
        step = kwargs.get("step",
                          list(range(0, 121))
                          + list(range(123, 385, 3)))

        def _configure():
            args = dict()
            pattern = PATTERNS[self.grid]
            args['_url'] = URLS['gfs']
            args['_model'] = self.model
            args['_extension'] = "grib2"
            args['_params'] = "pgrb2"
            args['_set'] = "" if not kwargs.get('paramset') \
                else kwargs.get('paramset')
            args['_resol'] = resol if resol else self.resol
            args['_yyyymmdd'] = kwargs['date']
            args['_H'] = "{:02d}".format(kwargs['time'])

            urls = list()
            for item in step:
                args['_fc_hour'] = "{:03d}".format(item)
                # kwargs['fc_hours'] = "{:03d}".format(item)
                url = pattern.format(**args)
                urls.append(url)

            return urls
        # end module

        try:
            idx = self._call_index(_configure())
        except Exception as e:  # ToDo specify exception
            print(e)
            print("Resources not available. Trying a forecast 6 hrs earlier...")
            kwargs = self._dateandtime(**kwargs)
            try:
                idx = self._call_index(_configure())
            except Exception as e:  # ToDo specify exception
                print(e)
                print("Resources not available. Revise your parameter set ...")
                exit(1)

        return self._prepare_request(idx, **kwargs)

    def _call_index(
            self,
            urls: list[str]
    ) -> dict[str, dict[int, dict]]:
        """
        extract the index files for offset and length of each parameter layer,
        can be filtered by shortName, level, and type.
        :param urls:
        :return: index file in dict format
        """
        dix = dict()
        dict_keys = \
            ["offset", "datetime", "shortName", "level", "validity"]

        for url in urls:
            try:
                # size of grib data file
                resp = requests.get(url, stream=True)
                resp.raise_for_status()
                length = int(resp.headers.get("Content-length"))

                # and its appropriate index file
                url_index = "{}.idx".format(url)
                response = self.session.get(url_index)
                response.raise_for_status()
                dix[url] = dict()
                print(f"Index file {url_index} downloaded")
            except requests.exceptions.HTTPError as e:
                # try again for most recent available fc
                self.lower_by_fc = True
                raise e  # return empty dict for current url

            for line in response.iter_lines():
                item = line.decode('utf-8').split(":")[:-1]
                no = int(item[0])

                # convert list to dict by merging lists, skip first element that
                # is number of parameter entry
                dix[url][no] = dict(zip(dict_keys, item[1:]))

                dix[url][no]['datetime'] = \
                    dix[url][no]['datetime'].replace("d=", "")
                dix[url][no]['offset'] = int(dix[url][no]['offset'])
                # replace length by offset minus offset of last record
                if no > 1:
                    dix[url][no - 1]['length'] = \
                        dix[url][no]['offset'] - dix[url][no - 1]['offset']
                    dix[url][no]['length'] = length - dix[url][no]['offset']
                # print(json.dumps( dix, indent=2))

            # caveat: rate limit of <120/minute to the NOMADS site.
            # hits are considered to be head/listing commands as well as actual
            # data download attempts, i.e. each get requests
            # The block is temporary and typically lasts for 10 minutes
            # the system is automatically configured to blacklist an IP if it
            # continually hits the site over the threshold.
            # source: ncep.pmb.dataflow@noaa.gov (Brian)
            sleep(.5)
        # end for loop url

        out_file = open(f"{LOG_DIR}/indices.json", "w")
        json.dump(dix, out_file, indent=2)
        out_file.close()

        return dix

    @staticmethod
    def _prepare_request(
            idx: dict[str, dict[int, dict]],
            **kwargs
    ) -> list:
        """
        prepare data multirange downloads of single url, see
        https://github.com/ecmwf/multiurl
        :param idx:
        :param kwargs:
        :return:
        """
        url_download = list()
        parameter: list = kwargs.get('parameter')

        for url, v in idx.items():
            t = tuple()
            # size of the entire grib2 file
            highest_id = sorted(v, key=lambda x: x, reverse=True)[0]
            size = v[highest_id]['offset'] + v[highest_id]['length']

            if not parameter:  # download entire parameter set
                url_download.append(
                    {"url": url,
                     "parts": ((0, size),)}
                )
                continue

            # number of parameter is key
            for k, value in v.items():
                for p in parameter:  # parameter to be selected
                    predicate = False
                    # checks
                    assert p.get('shortName'), "shortName must not be empty!"
                    if p.get('level'):
                        assert p.get('typeOfLevel'), \
                            "typeOfLevel must not be empty!"
                    # evaluate fields shortName is compared in lower case
                    if value['shortName'].lower() in p['shortName']:
                        if p.get('typeOfLevel'):
                            if p.get('level'):
                                if p['typeOfLevel'] in value['level'] \
                                        and p['level'] in value['level']:
                                    predicate = True
                            else:
                                if p['typeOfLevel'] in value['level']:
                                    predicate = True
                        else:
                            predicate = True

                    if predicate and kwargs.get('validity'):
                        if not any(i in value['validity']
                                   for i in kwargs['validity']):
                            predicate = False
                    if predicate:
                        print("{}:{}:{}:{}".format(
                            value['datetime'],
                            value['shortName'],
                            value['level'],
                            value['validity'])
                        )
                        t += ((value['offset'], value['length']),)

            # only if filtered but filter did apply,
            if t:
                # remove duplicates and sort according to offset, but
                # slow with big numbers
                t = tuple(sorted(set(t), key=t.index))
                url_download.append(
                    {"url": url,
                     "parts": t}
                )
            else:
                raise KeyError("No filter applied.")
            # end for loop item number each url
            print("\n")
        # end for loop url

        return url_download
