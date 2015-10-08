Michigan DNR to Open Trails Converter
=================

A working python conversion script for Michigan DNR data to the [Open Trail specification](http://www.codeforamerica.org/specifications/trails/spec.html)

Getting Started
===============

1. Clone the repo `git clone git@github.com:trailheadlabs/MIDNRToOpenTrails.git`
2. Ensure you have Python 2.7+ installed by running `python --version`
3. [Install Python 2.7+](https://www.python.org/downloads/) if not already installed.
4. Install dependencies by running `pip install -r requirements.txt`
5. Copy latest marquette_pilot_open_data.zip to input directory
6. Run `python MIDNRToOpenTrails.py`
7. A new MI_DNR_OpenTrails.zip will be placed in the output directory. Enjoy!

What this script does.
========
Order of operations

1. Unzips input files (stewards.xls, named_trails.xls, trailheads and trail_segments shapefiles)
2. Reads input files (into memory)
3. Builds OpenTrails compliant data structures in memory
4. Writes data structures to OpenTrails files (stewards.csv, named_trails.csv, trailheads.geojson, trail_segments.geojson)
5. Creates simplified versions of the trail_segments.geojson file, using the rdp package.
5. Zips files in output directory into MT_DNR_OpenTrails.zip

Dependencies 
============

 * [pyshp](http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyshp)
 * [pyproj](http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyproj)
 * [requests](http://www.lfd.uci.edu/~gohlke/pythonlibs/#requests)

Notes
==========

* Does not include areas.geojson
