# Changelog 
## x.x.x (xxxx-xx-xx)
### Added
### Changed
### Fixed
### Deprecated
### Removed
### Security
## 0.2.0 (2025-02-12)
### Added
### Changed
- Extraction of grib2 file run as threads reniced by 19.
- Permit a retention period between http GET requests of the .idx and .grib2 
files to avoid an "abuse blocking" of the requesting IP.
- Selection of parameter done through index files, select * on grib2 file
### Fixed
- Check completeness of files on "https://nomads.ncep.noaa.gov/ domain before 
downloading most recent forecast, otherwise choose a forecast @ -6 hrs. 
### Deprecated
### Removed
### Security
## 0.1.1 (2025-02-06)
### Added
- Docker for GFS-DOWNSIZED
### Changed
### Fixed
### Deprecated
### Removed
### Security
## 0.1.0 (2025-01-30)
### Added
- GFS downloads reduced by get requests with byte ranges implemented in 
gfs-downsized. This reveals a very first draft, that requires some more work to 
be done.
### Changed
### Fixed
### Deprecated
### Removed
### Security
## 0.0.4 (2024-12-08)
### Added
- Quick viewer of the the last forecast for windspeed and direction (windrose)
### Changed
- Quick viewer updated: toggle lines (in-)visible
- Quick viewer moved to tools directory, one for all 
### Fixed
### Deprecated
### Removed
### Security
## 0.0.3 (2024-11-29)
### Added
- download a subset of GFS files by selecting the ?th hour utilizing "-s" option
### Changed
- Grid is reduced to a single cell with edge sizes of the resolution
### Fixed
- Ubuntu 22.04 image loaded instead of python:3.10.15-slim for cron issues 
### Deprecated
### Removed
### Security
## 0.0.2 (2024-11-25)
### inital version
