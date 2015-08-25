Michigan DNR to Open Trails Converter
=================

A working python conversion script for Michigan DNR data to the [Open Trail specification](http://www.codeforamerica.org/specifications/trails/spec.html)

* Aims to be lean on dependencies.
  * Does not require GDAL, shapely, arcpy etc.
* Not web-based.

In Brief
========
Order of operations

1. Download lookup tables and shapefiles
2. Unzip
3. Read shapefile (into memory)
4. Create trails_segments.geojson
5. Create named_trails.csv
6. Create stewards.csv
7. Create areas.geojson

Dependencies
============

* Check if you have Python 2.7+ by running `python --version` from a terminal
* Install Python 2.7+ if not already installed.
* Run `pip install -r requirements.txt` to install dependent libraries, or you can download and install the individually:

 * [pyshp](http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyshp)
 * [pyproj](http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyproj)
 * [requests](http://www.lfd.uci.edu/~gohlke/pythonlibs/#requests)

Instructions
===========

* Clone or download the zipped repository
* Satisfy dependencies (see above)
* `>python MIDNRToOpenTrails.py`

Disclaimers
==========

* Does not include areas.geojson
