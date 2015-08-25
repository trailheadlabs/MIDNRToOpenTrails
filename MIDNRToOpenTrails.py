#
#  _____   _____  _______ __   _      _______  ______ _______ _____
# |     | |_____] |______ | \  |         |    |_____/ |_____|   |   |
# |_____| |       |______ |  \_|         |    |    \_ |     | __|__ |_____
#
# _______  _____  __   _ _    _ _______  ______ _______ _____  _____  __   _
# |       |     | | \  |  \  /  |______ |_____/ |______   |   |     | | \  |
# |_____  |_____| |  \_|   \/   |______ |    \_ ______| __|__ |_____| |  \_|
#

# This is the OpenTrails conversion script for MI DNR to OpenTrails

# Huge thank you to Ben Sainsbury (formerly Oregon Metro) for the initial work done on this script.

# http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyshp
import shapefile

# http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyproj
import pyproj

# http://www.lfd.uci.edu/~gohlke/pythonlibs/#requests
import requests

import hashlib, collections, csv, os, sys, zipfile

import json

import csv

# http://www.codeforamerica.org/specifications/trails/spec.html

TRAILS_URL = 'http://library.oregonmetro.gov/rlisdiscovery/trails.zip'

WGS84 = pyproj.Proj("+init=EPSG:4326") # LatLon with WGS84 datum used for geojson
MIDNR = pyproj.Proj("+init=EPSG:3078", preserve_units=True) # datum used by Michigan

#OBJECTID,name,id,url,address,publisher,license,phone
STEWARD_FIELDS = ['OBJECTID', 'name', 'id', 'url', 'address', 'publisher', 'license', 'phone' ]
MOTOR_VEHICLE_FIELDS = ['AllTerVeh','FourWD','ATV','Motorbike','MCCCT','Snowmobile']
STEWARDS = []
STEWARD_MAP = {}
NAMED_TRAILS = []
NAMED_TRAIL_MAP = {}
NAMED_TRAIL_SEGMENT_ID_MAP = {}
TRAIL_SEGMENTS = []
TRAILHEADS = []

if not os.path.exists(os.getcwd()+'/output'):
    """
    Create a directory to hold the output
    """
    os.makedirs(os.getcwd()+'/output')

### SUPPORT FUNCTIONS

def unzip(file):
    zfile = zipfile.ZipFile(os.getcwd()+'/src/'+file+'.zip')
    for name in zfile.namelist():
        (dirname, filename) = os.path.split(name)
        zfile.extract(name, os.getcwd()+'/src/')
    zfile.close()

def get_steward_id(steward_name):
    result = None
    if steward_name in STEWARD_MAP:
        result = STEWARD_MAP[steward_name]
    return result

def is_motor_vehicles(atr):
    result = False
    for field in MOTOR_VEHICLE_FIELDS:
        if field.upper() in atr:
            result = (atr[field.upper()] == 'Yes') or result
    yesno = 'yes' if result else 'no'
    return yesno

### PARSING FUNCTIONS

def parse_stewards_csv():
    print "* Parsing stewards.csv"
    with open(os.getcwd() + "/input/stewards.csv", mode='r') as infile:
        reader = csv.DictReader(infile, STEWARD_FIELDS) #stewards.csv header
        reader.next()
        for row in reader:
            STEWARDS.append(row)
        for row in STEWARDS:
            row['id'] = str(row['id'])
            print "** Steward"
            print row
            STEWARD_MAP[row['name']] = row['id']
    print "* Done parsing stewards.csv"

def parse_named_trails_csv():

    print "* Parsing named_trails.csv"
    with open(os.getcwd() + "/input/named_trails.csv", mode='r') as infile:
        reader = csv.DictReader(infile, ['OBJECTID','Code', 'Name']) # named_trails.csv header
        reader.next() #skip header line
        for row in reader:
            NAMED_TRAILS.append(row)
        for row in NAMED_TRAILS:
            row['id'] = str(row['Code'])
            row['name'] = row['Name']
            row['segment_ids'] = ""
            row['description'] = ""
            print "** Named Trail"
            print row
            NAMED_TRAIL_MAP[row['name']] = row['id']

    print "* Done parsing named_trails.csv"


def build_osm_tags(atr):
    result = ""
    tags = []
    if atr['SURFACE'].strip():
        tags.append('surface=' + atr['SURFACE'])
    if atr['WIDTH'].strip():
        tags.append('width=' + atr['WIDTH'])
    return ";".join(tags)

def transform_geometry(geom):
    if geom['type'] == 'LineString':
        return transform_linestring(geom['coordinates'])
    elif geom['type'] == 'MultiLineString':
        return transform_multilinestring(geom['coordinates'])
    elif geom['type'] == 'Point':
        return transform_coordinates(geom['coordinates'])


def transform_linestring(linestring):
    n_geom = []
    for point in linestring:
        n_geom.append(transform_coordinates(point))
    return n_geom

def transform_multilinestring(multilinestring):
    n_geom = []
    for linestring in multilinestring:
        n_geom.append(transform_linestring(linestring))
    return n_geom

def transform_coordinates(coordinates):
    return pyproj.transform(MIDNR, WGS84, coordinates[0], coordinates[1])

def parse_trail_segments():
    print "* Parsing trail segments"
    # read the trails shapefile
    reader = shapefile.Reader(os.getcwd()+'/input/trail_segments.shp')
    fields = reader.fields[1:]
    field_names = [field[0].upper() for field in fields]

    #iterate trails
    for sr in reader.shapeRecords():

        atr = dict(zip(field_names, sr.record))

        # we're only allowing open existing trails to pass

        props = collections.OrderedDict()

        #effectively join to the stewards table
        id = props['id'] = atr['TRAIL_ID']
        props['steward_id'] = "000000"
        props['motor_vehicles'] = is_motor_vehicles(atr)
        props['foot'] = 'yes' if atr['HIKE'] == 'Yes' else 'no'
        props['bicycle'] = 'yes' if atr['BIKE'] == 'Yes' else 'no'
        props['horse'] = 'yes' if atr['EQUESTRIAN'] == 'Yes' else 'no'
        props['ski'] = 'yes' if atr['SKI'] == 'Yes' else 'no'

        # spec: "yes", "no", "permissive", "designated"
        props['wheelchair'] = 'yes' if atr['ADA'] == 'Yes' else 'no'

        props['osm_tags'] = build_osm_tags(atr)

        # Assumes single part geometry == our (RLIS) trails.shp

        geom = sr.shape.__geo_interface__
        geom_type = geom['type']
        n_geom = transform_geometry(geom)

        segment= collections.OrderedDict()
        segment['type']='Feature'
        segment['properties'] = props
        segment['geometry'] = {"type":geom_type, "coordinates":n_geom}

        # NEED TO PARSE THE TRAIL_CODE FIELD TO NAMED_TRAIL_SEGMENT_ID_MAP

        _codes = atr['TRAIL_CODE'].split(";")
        for code in _codes:
            if code in NAMED_TRAIL_SEGMENT_ID_MAP:
                NAMED_TRAIL_SEGMENT_ID_MAP[code].append(id)
            else:
                NAMED_TRAIL_SEGMENT_ID_MAP[code] = [id]

        TRAIL_SEGMENTS.append(segment)


    #Release the trails shapefile

    reader = None

    print ("* Done parsing trail segments")

def parse_trailheads():
    print ("* Parsing trailheads")
    # read the trails shapefile
    reader = shapefile.Reader(os.getcwd()+'/input/trailheads.shp')
    fields = reader.fields[1:]
    field_names = [field[0].upper() for field in fields]

    #iterate trails
    for sr in reader.shapeRecords():

        atr = dict(zip(field_names, sr.record))

        # we're only allowing open existing trails to pass

        props = collections.OrderedDict()

        #effectively join to the stewards table
        id = props['id'] = str(atr['ID'])
        props['steward_id'] = str(atr['STEWARD_ID'])
        props['segment_ids'] = atr['TRAIL_SEG_']
        props['name'] = atr['THNAME']
        props['restrooms'] = 'yes' if atr['RESTROOM'] == 'Yes' else 'no'
        props['drinkwater'] = 'yes' if atr['WATER'] == 'Yes' else 'no'
        props['parking'] = 'yes' if atr['PARKING'] == 'Yes' else 'no'
        props['address'] = atr['ADDRESS']

        # Assumes single part geometry == our (RLIS) trails.shp

        geom = sr.shape.__geo_interface__

        n_geom = transform_coordinates(geom['coordinates'])

        segment= collections.OrderedDict()
        segment['type']='Feature'
        segment['properties'] = props
        segment['geometry'] = {"type":"Point", "coordinates":n_geom}

        TRAILHEADS.append(segment)


    #Release the trails shapefile

    reader = None

    print ("* Done parsing trailheads")

### WRITING FUNCTIONS

def write_stewards_csv():
    OUT_STEWARD_FIELDS = ['id', 'name', 'url', 'phone', 'address','publisher', 'license']
    print "* Writing stewards.csv"
    stewards_out = open(os.getcwd() + "/output/stewards.csv", "w")
    stewards_out.write(",".join(OUT_STEWARD_FIELDS)+"\n")

    for steward in STEWARDS:
        _row_data = [ \
            str(steward['id']), \
            steward['name'], \
            steward['url'], \
            steward['phone'], \
            steward['address'], \
            steward['publisher'], \
            steward['license'] \
            ]
        stewards_out.write(','.join(_row_data)+"\n")
    stewards_out.close()

    print "* Done writing stewards.csv"

def write_named_trails_csv():
    print "* Writing named_trails.csv"
    named_trails_out = open(os.getcwd() + "/output/named_trails.csv", "w")
    named_trails_out.write('"id","name","segment_ids","description","part_of"\n')

    for named_trail in NAMED_TRAILS:
        _segment_ids = ';'.join(NAMED_TRAIL_SEGMENT_ID_MAP[named_trail['id']]) if (named_trail['id'] in NAMED_TRAIL_SEGMENT_ID_MAP) else ''
        _row_data = [ \
            str(named_trail['id']), \
            named_trail['name'], \
            _segment_ids, \
            '','']
        named_trails_out.write(','.join(_row_data)+"\n")
    named_trails_out.close()
    print "* Done writing named_trails.csv"

def write_trail_segments_geojson():
    trail_segments_out = open(os.getcwd() + "/output/trail_segments.geojson", "w")
    trail_segments_out.write(json.dumps({"type": "FeatureCollection",\
    "features": TRAIL_SEGMENTS}, indent=2) + "\n")
    trail_segments_out.close()

def write_trailheads_geojson():
    trailheads_out = open(os.getcwd() + "/output/trailheads.geojson", "w")
    trailheads_out.write(json.dumps({"type": "FeatureCollection",\
    "features": TRAILHEADS}, indent=2) + "\n")
    trailheads_out.close()

if __name__ == "__main__":

    # PARSE PARSE PARSE
    parse_stewards_csv()

    parse_named_trails_csv()

    parse_trail_segments()

    parse_trailheads()

    # WRITE WRITE WRITE
    write_stewards_csv()

    write_named_trails_csv()

    write_trail_segments_geojson()

    write_trailheads_geojson()

    print '* Process complete'
