# Weather Forecasts of ECMWF and GFS

Download weather forecasts of the European Centre for Medium-Range Weather 
Forecasts (ECMWF) and the Global Forecast System of the National Oceanic and 
Atmospheric Administration (NOAA). Main focus is to predict 
the precipitable water vapor (PWV) on Cerro Chajnantor in the Atacama 
Astronomical Park. Data will be accompanied by a radiometer and a weather
station providing the atmospheric transparency, air temperature, pressure, 
humidity, and wind, presumably after Q2/25.

Weather forecasts will assist in planning near-future observations, particularly
at higher wavelengths < 350 micrometer, and to enable the telescope operator to
take action in case of upcoming severe weather conditions.

Applications are available to be executed in docker container. A cron 
timer, as defined in "mycron", will start the forecasts after the dissemination
schedules. A "parameter.json" file defines the parameters to be
considered and the geolocation for the forecasts.

Side note: weather foreasts are downloaded into local grib2 files. They can be 
extracted utilizing the [pygrib](https://jswhit.github.io/pygrib/) package. 

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
[forecast_viewer](https://github.com/AIfA-Radio/WeatherForecast/blob/master/tools/src/forecast_viewer.py)
for ECMWF and GFS. Select via option "-p". Also, the windspeed and direction is
displayed in a windrose, by calling [forecast_windrose](https://github.com/AIfA-Radio/WeatherForecast/blob/master/tools/src/forecast_windrose.py).
Always the last forecast is considered, unless a different forecast is chosen 
by option "-d". Option "-v" provides a save to mp4 file option. However, for 
utilizing the download mp4 function, the FFmpeg package is to be installed on 
the OS.

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

## ECMWF HRES Model "High Frequency products" 
development discontinued - license is free of charge for research organisations, but 
subject to service fee

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

[gfs_download.py](https://github.com/AIfA-Radio/WeatherForecast/blob/master/gfs/src/gfs_download.py)
can be run with option "-t". In this case only the very first files
are downloaded (and deleted) for testing the performance. Disable it in mycron
when running productive!!! Option "-s \<hour>" runs the script to reduce the 
temporal resolution (and bandwidth required) to every \<hour>th hour.

## GFS-Downsized
Current application is a derivative of the GFS application as of above. The 
download sizes of the grib2 files were significantly reduced. 
The package https://github.com/ecmwf/multiurl needs to be cloned and installed
separately, if not already installed along with the 
https://github.com/ecmwf/ecmwf-opendata package

Status: development, as of 2025/01/30 

## Epilogue

Problems? Issues? Drop us an email.

contact: Ralf Antonius Timmermann (AIfA, University Bonn), 
email: rtimmermann@astro.uni-bonn.de