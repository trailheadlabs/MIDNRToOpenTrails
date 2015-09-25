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

# http://www.lfd.uci.edu/~gohlke/pythonlibs/#requests
import requests

import hashlib, collections, csv, os, sys, zipfile

import json

import xlrd

import csv

from support import *

# http://www.codeforamerica.org/specifications/trails/spec.html

STEWARD_FIELDS = ['OBJECTID', 'name', 'id', 'url', 'address', 'publisher', 'license', 'phone' ]
STEWARDS = []
STEWARD_MAP = {}
NAMED_TRAILS = []
NAMED_TRAIL_IDS = []
NAMED_TRAIL_MAP = {}
NAMED_TRAIL_SEGMENT_ID_MAP = {}
SEGMENT_ID_NAMED_TRAIL_MAP = {}
TRAIL_SEGMENTS = []
TRAIL_SEGMENT_IDS = []
TRAILHEADS = []

if not os.path.exists(os.getcwd()+'/output'):
    """
    Create a directory to hold the output
    """
    os.makedirs(os.getcwd()+'/output')


### PARSING FUNCTIONS
def xls_to_csv(ExcelFile, SheetIndex, CSVFile):
    workbook = xlrd.open_workbook(ExcelFile)
    worksheet = workbook.sheet_by_index(SheetIndex)
    csvfile = open(CSVFile, 'wb')
    wr = csv.writer(csvfile, quoting=csv.QUOTE_ALL)

    for rownum in xrange(worksheet.nrows):
        wr.writerow(
            list(x.encode('utf-8') if type(x) == type(u'') else x
                for x in worksheet.row_values(rownum)))

    csvfile.close()

def parse_stewards_csv():
    xls_to_csv("./input/stewards.xls",0,"./input/stewards.csv")
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
    xls_to_csv("./input/named_trails.xls",0,"./input/named_trails.csv")
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
            row['description'] = row['Description']
            print "** Named Trail"
            print row
            NAMED_TRAIL_MAP[row['name']] = row['id']
            NAMED_TRAIL_IDS.append(row['id'])

    print "* Done parsing named_trails.csv"


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
        props['steward_id'] = atr['STEWARD_ID']
        props['motor_vehicles'] = is_motor_vehicles(atr)
        props['foot'] = 'yes' if atr['HIKE'] == 'Yes' else 'no'
        props['bicycle'] = 'yes' if atr['BIKE'] == 'Yes' else 'no'
        props['horse'] = 'yes' if atr['EQUESTRIAN'] == 'Yes' else 'no'
        props['ski'] = 'yes' if atr['SKI'] == 'Yes' else 'no'

        # spec: "yes", "no", "permissive", "designated"
        props['wheelchair'] = 'yes' if atr['ADA'] == 'Yes' else 'no'

        props['osm_tags'] = atr['OSM_TAGS']

        geom = sr.shape.__geo_interface__
        geom_type = geom['type']
        n_geom = transform_geometry(geom)

        segment= collections.OrderedDict()
        segment['type']='Feature'
        segment['properties'] = props
        segment['geometry'] = {"type":geom_type, "coordinates":n_geom}

        # NEED TO PARSE THE TRAIL_CODE FIELD TO NAMED_TRAIL_SEGMENT_ID_MAP

        _codes = atr['TRAIL_CODE'].split(";")
        if len(_codes) > 0:
            SEGMENT_ID_NAMED_TRAIL_MAP[id] = _codes
            for code in _codes:
                if code in NAMED_TRAIL_SEGMENT_ID_MAP:
                    NAMED_TRAIL_SEGMENT_ID_MAP[code].append(id)
                else:
                    NAMED_TRAIL_SEGMENT_ID_MAP[code] = [id]

        TRAIL_SEGMENTS.append(segment)
        TRAIL_SEGMENT_IDS.append(id)


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
        props['kiosk'] = 'yes' if atr['INFO'] == 'Yes' else 'no'
        props['address'] = atr['ADDRESS']

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
    writer = csv.writer(stewards_out, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(OUT_STEWARD_FIELDS)

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
        writer.writerow(_row_data)
    stewards_out.close()

    print "* Done writing stewards.csv"

def write_named_trails_csv():
    print "* Writing named_trails.csv"
    named_trails_out = open(os.getcwd() + "/output/named_trails.csv", "w")
    writer = csv.writer(named_trails_out, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["id","name","segment_ids","description","part_of"])

    for named_trail in NAMED_TRAILS:
        # LEAVE EMPTY TRAILS OUT OF THE named_trails.csv file
        if named_trail['id'] in NAMED_TRAIL_SEGMENT_ID_MAP:
            _segment_ids = ';'.join(NAMED_TRAIL_SEGMENT_ID_MAP[named_trail['id']]) if (named_trail['id'] in NAMED_TRAIL_SEGMENT_ID_MAP) else ''
            _row_data = [ \
                str(named_trail['id']), \
                named_trail['name'], \
                _segment_ids, \
                named_trail['description'],'']
            writer.writerow(_row_data)
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

def validate():

    # Check for empty trails
    empty_count = 0
    missing_count = 0

    print "* Validating Trails "
    for trail in NAMED_TRAILS:
        print "** Validating Trail " + str(trail['id'])
        if trail['id'] not in NAMED_TRAIL_SEGMENT_ID_MAP:
            print trail['id'] + " has no segments"
            empty_count = empty_count + 1
        else:
            segments = NAMED_TRAIL_SEGMENT_ID_MAP[trail['id']]
            for id in segments:
                if id not in TRAIL_SEGMENT_IDS:
                    missing_count = missing_count + 1
                    print 'INVALID Missing trail segment : ' + str(id)
                else:
                    print "Found trail segment " + str(id)
    print str(len(NAMED_TRAILS)) + " trails"
    print str(empty_count) + " empty trails"
    print str(missing_count) + " missing segments"

    print("* Validating Trailheads")
    # Check for empty trails
    missing_th_segment_count = 0
    for trailhead in TRAILHEADS:
        print( "** Validating Trailhead " + str(trailhead['properties']['id']))
        segments = trailhead['properties']['segment_ids'].split(';')
        for id in segments:
            if id not in TRAIL_SEGMENT_IDS:
                missing_th_segment_count = missing_th_segment_count + 1
                print 'INVALID: Missing trail segment : ' + str(id)
            else:
                print "Found trail segment " + str(id)
    print str(len(TRAILHEADS)) + " trailheads"
    print str(missing_th_segment_count) + " missing segments"

    print("* Validating Trail Segments")
    # Check for trail segments without trails
    for segment in TRAIL_SEGMENTS:
        unused_count = 0
        if segment['properties']['id'] not in SEGMENT_ID_NAMED_TRAIL_MAP:
            unused_count = unused_count + 1
            print "Unused trail segment : " + segment['properties']['id']

    #

    print str(len(TRAIL_SEGMENTS)) + " trail segments"
    print str(unused_count) + " unused trail segments"

if __name__ == "__main__":

    # unzip the input zip file
    unzip_input("marquette_pilot_open_data")

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

    # Report on the quality of the data
    validate()

    # zip the individual OpenTrails files up
    zip_output()
    print '* Process complete'
