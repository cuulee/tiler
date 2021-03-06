#!/usr/bin/python2.7
import sys
import os
import subprocess
import gzip
import shutil
from validate_geojson import validate_geojson
from tiler_helpers import absolute_file_paths

def create_mbtiles(GEOJSON_FILES, MBTILES_NAME, MIN_ZOOM, MAX_ZOOM, SIMPLIFICATION, SPLIT=True):
    """Create an .mbtiles file for a set of GeoJSON files"""

    # Validate GeoJSON
    print "\n Validating GeoJSON"
    if type(GEOJSON_FILES) != list:
        raise TypeError("GEOJSON_FILES is not a list")
    for geojson in GEOJSON_FILES:
        validate_geojson(geojson)
    print "\n GeoJSON is valid!"

    # Create .mbtiles file
    OUTPUT_PATH = "/tiler-data/tiles/{}.mbtiles".format(MBTILES_NAME)

    # Remove the current mbtiles file if it's there
    try:
        print "MBTiles file of that name already exists, removing it so it can be recreated"
        os.remove(OUTPUT_PATH)
    except OSError:
        pass

    if not os.path.exists("/tiler-data/tiles/"):
        os.makedirs("/tiler-data/tiles/")

    print "Commencing running creation of mbiles from GeoJSON files : ", str(GEOJSON_FILES)

    GEOJSON_FILES_STR = ""
    for geojson_file in GEOJSON_FILES:
        GEOJSON_FILES_STR += geojson_file + " "

    if SPLIT == False and MIN_ZOOM != None and MAX_ZOOM != None:
        command = "tippecanoe -o {} {} --minimum-zoom={}  --maximum-zoom={} --read-parallel --simplification={} --drop-smallest-as-needed --coalesce".format(OUTPUT_PATH, GEOJSON_FILES_STR, MIN_ZOOM, MAX_ZOOM, SIMPLIFICATION)

    elif MIN_ZOOM != None and MAX_ZOOM != None:
        print "\n Min Zoom: ", MIN_ZOOM
        print "\n Max Zoom: ", MAX_ZOOM
        command = "tippecanoe -o {} {} --minimum-zoom={}  --maximum-zoom={} --read-parallel --no-polygon-splitting --simplification={} --drop-smallest-as-needed --coalesce".format(OUTPUT_PATH, GEOJSON_FILES_STR, MIN_ZOOM, MAX_ZOOM, SIMPLIFICATION)
    else:
        command = "tippecanoe -o {} {} --read-parallel --no-polygon-splitting --simplification={} --drop-smallest-as-needed --coalesce".format(OUTPUT_PATH, GEOJSON_FILES_STR, SIMPLIFICATION)

    print "\n Running: ", command
    FNULL = open(os.devnull, 'w')
    tippecanoe_exit_code = subprocess.call(command, shell=True)# stdout=FNULL, stderr=subprocess.STDOUT)
    # stdout, stderr = tippecanoe_process.communicate()
    # if stderr:
    #     raise IOError(stderr)  
    # exit_code = tippecanoe_process.wait()
    print "\n Tippecanoe exit code: ", tippecanoe_exit_code
    if tippecanoe_exit_code != 0:
        raise IOError("Exit code was not 0 for tippecanoe process")

    print "\n Created mbtiles file from " + str(GEOJSON_FILES)


def extract_pbf(MBTILES_NAME, UPDATE=False):
    """Extract a set of protobufs from a .mbtiles file"""

    MBTILES_DIR = "/tiler-data/tiles/" + MBTILES_NAME

    if UPDATE:
        MBTILES_DIR = "/tiler-data/updates/" + MBTILES_NAME

    # Create unzipped .pbf
    if os.path.isdir(MBTILES_DIR):
        print "\n Vector Tiles folder (", MBTILES_DIR, ") already exists removing it..."
        try:
            shutil.rmtree(MBTILES_DIR)
        except OSError as shutil_err:
            print shutil_err
            print "\n shutil.rmtree failed for one reason or another, trying rm -rf ..."
            try:
                os.system("rm -rf " + MBTILES_DIR)
            except OSError as os_err:
                print "\n That failed too... unable to remove the directory"
                raise os_err

        print "\n Vector Tiles folder removed!"

    print "\n Commencing extraction from mbtiles to", MBTILES_DIR
    command = "mb-util --image_format=pbf --silent /tiler-data/tiles/{}.mbtiles {}".format(
        MBTILES_NAME,
        MBTILES_DIR
    )
    print "\n Running: ", command
    mbutil_process = subprocess.Popen(command, shell=True)
    exit_code = mbutil_process.wait()
    stdout, stderr = mbutil_process.communicate()
    if stderr:
        raise IOError(stderr)
    if exit_code != 0:
        raise IOError("Exit code was not 0 for mbutil process")

    # print stdout, stderr
    print "\n Decompress exit code: ", exit_code


def decompress_pbf(MBTILES_NAME, UPDATE=False):
    """Decompress a set of protobufs"""

    # We need to rename everything and then unzip it
    print "\n Decompressing gzipped Vector Tiles"
    extension = ".pbf"
    length = len(extension)
    counter = 0
    if UPDATE:
        files = absolute_file_paths("/tiler-data/updates/" + MBTILES_NAME)
    else:
        files = absolute_file_paths("/tiler-data/tiles/" + MBTILES_NAME)

    for filename in files:

        if counter % 500 == 0:
            print "\n 500 more tiles decompressed..."

        if filename.endswith(".pbf"):

            # Renaming
            old_name = os.path.abspath(filename)
            new_name = old_name[:-length] + '.pbf.gz'
            os.rename(old_name, new_name)

            file_to_unzip = new_name
            if UPDATE:
                path_list = filename.split(os.sep)
                zxy = os.path.join(*path_list[-3:])
                file_to_overwrite = "/tiler-data/tiles/" + MBTILES_NAME + "/" + zxy

            else:
                file_to_overwrite = old_name

            # Loop through and unzip everything to actually be a real .pbf file
            with gzip.open(file_to_unzip, 'rb') as infile:
                with open(file_to_overwrite, 'wb') as outfile:
                    #if UPDATE: print "\n Overwiting", file_to_overwrite
                    for line in infile:
                        outfile.write(line)

            # Get rid of the renamed, unzipped file
            os.remove(new_name)

        counter += 1

    print "\n Vector Tiles decompressed!"
    print "\n Finished! See tiles/" + MBTILES_NAME, " for the resulting files \n"


def create_demo_config(MBTILES_NAME):
    """ Generate a config for the web demos """

    demo_config = "/tiler-data/configs/web-demo-config.js"
    with open(demo_config, 'w+') as f:
        config = "var vectortiles = '" + MBTILES_NAME + "';"
        f.seek(0)
        f.write(config)
        f.truncate()

def geojson2tiles(GEOJSON_FILES, MBTILES_NAME, MIN_ZOOM, MAX_ZOOM, SIMPLIFICATION=0, UPDATE=False):
    """ From a set of GeoJSON files generate a set of raw protobuf vector tiles """

    print "\n Running geojson2tiles..."

    assert isinstance(SIMPLIFICATION, int)

    if MIN_ZOOM != None and MAX_ZOOM != None:
        assert isinstance(MIN_ZOOM, int)
        assert isinstance(MAX_ZOOM, int)
        assert MAX_ZOOM > MIN_ZOOM

    create_mbtiles(GEOJSON_FILES, MBTILES_NAME, MIN_ZOOM, MAX_ZOOM, SIMPLIFICATION, SPLIT=UPDATE)
    extract_pbf(MBTILES_NAME, UPDATE)
    decompress_pbf(MBTILES_NAME, UPDATE)
    create_demo_config(MBTILES_NAME)


if __name__ == '__main__':

    print "\n Checking input variables are valid..."

    if len(sys.argv) > 1:
        GEOJSON_FILE = sys.argv[1]
    else:
        raise ValueError("GEOJSON_FILE not defined")

    if len(sys.argv) > 2:
        MIN_ZOOM = int(sys.argv[2])
    else:
        MIN_ZOOM = "0" #raise ValueError("MAX_ZOOM not defined")

    if len(sys.argv) > 3:
        MAX_ZOOM = int(sys.argv[3])
    else:
        raise ValueError("MAX_ZOOM not defined")

    if len(sys.argv) > 4:
        SIMPLIFICATION = int(sys.argv[4])
    else:
        SIMPLIFICATION = "0"

    if not os.path.isfile(GEOJSON_FILE):
        raise IOError(GEOJSON_FILE + " does not exist")

    print "\n Input variables are valid!"

    MBTILES_NAME = os.path.basename(os.path.splitext(GEOJSON_FILE)[0])
    geojson2tiles([GEOJSON_FILE], MBTILES_NAME, MIN_ZOOM, MAX_ZOOM, SIMPLIFICATION)
