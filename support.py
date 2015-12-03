import hashlib, collections, csv, os, sys, zipfile

from zipfile import ZipFile

from rdp import rdp

import geojson

# http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyproj
import pyproj

WGS84 = pyproj.Proj("+init=EPSG:4326") # LatLon with WGS84 datum used for geojson
MIDNR = pyproj.Proj("+init=EPSG:4326", preserve_units=True) # datum used by Michigan

MOTOR_VEHICLE_FIELDS = ['ORV','ATV','Motorbike','MCCCT','Snowmobile']

### SUPPORT FUNCTIONS

def unzip_input(file):
    print "* Unzipping" + file
    zfile = zipfile.ZipFile(os.getcwd()+'/input/'+file)
    for name in zfile.namelist():
        (dirname, filename) = os.path.split(name)
        zfile.extract(name, os.getcwd()+'/input/unzipped/')
    zfile.close()

def zip_output():
    with ZipFile('./output/MI_DNR_OpenTrails.zip', 'w', zipfile.ZIP_DEFLATED) as myzip:
        myzip.write('./output/named_trails.csv','named_trails.csv')
        myzip.write('./output/stewards.csv','stewards.csv')
        myzip.write('./output/trailheads.geojson','trailheads.geojson')
        myzip.write('./output/trail_segments.geojson','trail_segments.geojson')

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

def round_me(coord):
    return [round(coord[0],7),round(coord[1],7)]

def simplify_coords(coords,tolerance):
    new_coords = rdp(coords,epsilon=tolerance)
    new_coords = map(round_me,new_coords)
    return new_coords

def simplify_geojson(geojson,tolerance=1.0):
    print('* Simplifying geojson at tolerance ' + str(tolerance))
    for feature in geojson.features:
        if feature['geometry']['type'] == 'LineString':
            feature['geometry']['coordinates'] = simplify_coords(feature['geometry']['coordinates'],tolerance)
        if feature['geometry']['type'] == 'MultiLineString':
            new_coords = []
            for coords in feature['geometry']['coordinates']:
                new_coords.append(simplify_coords(coords,tolerance))
            feature['geometry']['coordinates'] = new_coords
    return geojson

def simplify_geojson_file(in_path,out_path,tolerance=1.0):
    infile = open(os.getcwd() + in_path, mode='r')
    geo = geojson.load(infile)
    geo = simplify_geojson(geo,tolerance)
    outfile=open(os.getcwd() + out_path, mode='w')
    outfile.write(geojson.dumps(geo))

def simplify_trail_segments():
    simplify_geojson_file('/output/trail_segments.geojson','/output/trail_segments_simplified_001.geojson',0.001)
    simplify_geojson_file('/output/trail_segments.geojson','/output/trail_segments_simplified_0001.geojson',0.0001)
    simplify_geojson_file('/output/trail_segments.geojson','/output/trail_segments_simplified_00001.geojson',0.00001)
