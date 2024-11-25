# Weather Forecasts of ECMWF and GFS

Download weather forecasts of the European Centre for Medium-Range Weather 
Forecasts (ECMWF) and the Global Forecast System of the National Oceanic and 
Atmospheric Administration (NOAA). Main focus is to predict 
the precipitable water vapor (PWV) on Cerro Chajnantor in the Atacama 
Astronomical Park. Data will be accompanied by a radiometer and a weather
station providing the atmospheric transparency, air temperature, pressure, 
humidity, and wind, presumably after Q2/25.

Weather forecasts will assist in planning future observations, particularly at 
higher wavelengths < 350 micrometer and to warn the telescope operator in case of 
severe weather conditions.

Applications are available to be executed in docker container. A cron 
timer, as defined in "mycron", will start the forecasts after the dissemination
schedules. A "parameter.json" file defines the parameters to be
considered and the geolocation for the forecasts.

Aside: weather are downloaded into local grib2 files. They can be extracted 
utilizing the [pygrib](https://jswhit.github.io/pygrib/) package. 

Install and run - in background - though 

    docker compose build
    docker compose up -d
    
Find the logs in

    docker exec <container name> cat /var/log/out.log
    docker exec <container name> cat /var/log/err.log

Results are available under data/forecast.json

```json
{
  "datetime of analysis run": {
    "parameter1": {
      "time": [
        "202411201200",
        "202411201300",
        "202411201400"
      ],
      "unit": "kg m**-2",
      "value": [
        1.2944075213209638,
        1.272625504353056,
        1.3436186093485039
      ]
    }, 
      "parameter2": {
          
      }
  }
}
```
The forecasts can be viewed through a quick
[viewer](https://github.com/AIfA-Radio/WeatherForecast/blob/master/ecmwf-opendata/src/ecmwf_forecast_viewer.py)

## ECMWF Opendata
At no additional cost (research license) an atmospheric model high 
resolution 10-day forecast 
is available on https://www.ecmwf.int/en/forecasts/datasets/set-i with
4 forecast runs per day (00/06/12/18) (see dissemination schedule for details)
The open data is downgraded to a spatial resolution of 0.25 degree and temporal
resolution of 3 hrs, though.

Forecasts for the following parameter will be downloaded:
- precipitable water vapor column
- surface pressure
- temperature 2m above ground
- dew point 2m above ground
- wind speed in u direction 10 m above ground
- wind speed in v direction 10 m above ground

Note: Forecast runs issued at 0 and 12 UTC provide a forecast horizon of 240 hrs,
whilst it's 90 hrs for those issued at 6 and 18 UTC. This pecularity needs to be
considered by the "--extended" option to be provided for 
[ecmwf_download.py](https://github.com/AIfA-Radio/WeatherForecast/blob/master/ecmwf-opendata/src/ecmwf_download.py)
(see [mycron](https://github.com/AIfA-Radio/WeatherForecast/blob/master/ecmwf-opendata/mycron))

The current forecast is based on ECMWF’s Integrated Forecasting System, a 
physical model. Unforetunetely, the Artificial Intelligence/Integrated 
Forecasting System (AIFS) is in a beta version, that cannot be downloaded with 
Opendata.

## ECMWF
to be developed - subject to approval of license (applied from 2024/12/01)

## GFS
The GFS is run four times a day (00, 06, 12, 18 UTC), 
providing forecasts up to 16 days in advance
and delivering a spatial resolution 0.25 degree grid (28 km edge length). 
The model is divided into 127 vertical layers. It produces hourly forecast 
output for the first 120 hours, then 3 hourly for days 5-16. 
For the full description see 
[GFS](https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gfs.php).

The application downloads - via FTP - file by file (total number of 209)
each forecast. Forecasts comprise the following parameter:
- Precipitable water - atmosphereSingleLayer:level 0 considered as a single layer
- U component of wind - heightAboveGround:level 20 m
- V component of wind - heightAboveGround:level 20 m
- Temperature - heightAboveGround:level 80 m
- Pressure - heightAboveGround:level 80 m

Caveat: please note that it requires data of about 115 GB!!! to be downloaded
each forecast run, hence 460 GB a day. Since data is immediately deleted 
after being processed, <0.6 GB of storage space needs to be provided at a time.

The quick viewer available under ECMWF may be applied as well to reveal the 
forecast.

## Epilogue

Problems? Issues? Drop us an email.

contact: Ralf Antonius Timmermann (AIfA, University Bonn), 
email: rtimmermann@astro.uni-bonn.de