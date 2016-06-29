#!/usr/bin/env python

import mapnik, ogr, osr, pyproj, os, sys, getopt
from PIL import Image

###
# Draw a Rhumb line with nPoints nodes
# @author jonnyhuck
###
def getRhumb(startlong, startlat, endlong, endlat, nPoints):

    # calculate distance between points
    g = pyproj.Geod(ellps='WGS84')

    # calculate line string along path with segments <= 1 km
    lonlats = g.npts(startlong, startlat, endlong, endlat, nPoints)

    # npts doesn't include start/end points, so prepend/append them and return
    lonlats.insert(0, (startlong, startlat))
    lonlats.append((endlong, endlat))
    return lonlats


###
# Write a geometry to a Shapefile
# @author jonnyhuck
###
def makeShapefile(geom, name, layer_name): 

    # set up the shapefile driver
    driver = ogr.GetDriverByName("ESRI Shapefile")
    
    # remove old shapefile if required     
    if os.path.exists(name):
        driver.DeleteDataSource(name)

    # create the data source
    data_source = driver.CreateDataSource(name)

    # create the spatial reference, WGS84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    # create the layer
    layer = data_source.CreateLayer(layer_name, srs, ogr.wkbPolygon)

    # create the feature
    feature = ogr.Feature(layer.GetLayerDefn())

    # Set the feature geometry using the point
    feature.SetGeometry(geom)
    
    # Create the feature in the layer (shapefile)
    layer.CreateFeature(feature)
    
    # Destroy the feature to free resources
    feature.Destroy()

    # Destroy the data source to free resources
    data_source.Destroy()


###
# Make a single Gore
# @author jonnyhuck
###
def makeGore(central_meridian, gore_width, number, width, gore_stroke):

    # WGS84
    source = osr.SpatialReference()
    source.ImportFromEPSG(4326)

    # Spherical Sinusoidal
    original = osr.SpatialReference()
    original.ImportFromProj4("+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +a=6371000 +b=6371000 +units=m +no_defs ")
    
    # Spherical Sinusoidal with gore-specific central meridian
    target = osr.SpatialReference()
    target.ImportFromProj4('+proj=sinu +lon_0=' + str(central_meridian) + ' +x_0=0 +y_0=0 +a=6371000 +b=6371000 +units=m +no_defs') 

    # get the main points of the area of interest and transform
    halfWidth = gore_width / 2
    mainPoints = ogr.Geometry(ogr.wkbLinearRing)
    mainPoints.AddPoint(central_meridian, 90)
    mainPoints.AddPoint(central_meridian - halfWidth, 0)
    mainPoints.AddPoint(central_meridian, -90)
    mainPoints.AddPoint(central_meridian + halfWidth, 0)

    # make the gore  (using mainPoints in their wgs84 form)
    gore = getRhumb(mainPoints.GetX(1), mainPoints.GetY(0), mainPoints.GetX(1), mainPoints.GetY(2), 100) # get the first rhumb (N-S)     
    gore2 = getRhumb(mainPoints.GetX(3), mainPoints.GetY(2), mainPoints.GetX(3), mainPoints.GetY(0), 100) # get the second rhumb (S-N)
    gore.extend(gore2) # combine them into one
    
    # create ring for the gore
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for p in gore:
        ring.AddPoint(p[0], p[1])
    
    # if invalid, do something  more elegant than the fix below
#     if ring.IsValid() == False:

    # create polygon for the gore
    clipper = ogr.Geometry(ogr.wkbPolygon)
    clipper.AddGeometry(ring)
    clipper.CloseRings()
#     print clipper.ExportToJson()

    # write to shapefile
    makeShapefile(clipper, "tmp/tmp_gore" + str(number) + ".shp", "gore")

    # open countries file and get all of the geometry
    shapefile = "ne_110m_land/ne_110m_land.shp"
    driver = ogr.GetDriverByName("ESRI Shapefile")
    dataSource = driver.Open(shapefile, 0)
    layer = dataSource.GetLayer()
    land = ogr.Geometry(ogr.wkbGeometryCollection)
    for feature in layer:
        land.AddGeometry(feature.GetGeometryRef())

    # clip against the gore
    landPanel = clipper.Intersection(land)

    # write to shapefile
    makeShapefile(landPanel, "tmp/tmp_land" + str(number) + ".shp", "land")

    # clean up
    clipper.Destroy()
    landPanel.Destroy()

    # make bounding box for the output
    transform = osr.CoordinateTransformation(source, original)
    
    # points for the bounding box
    bbPoints = ogr.Geometry(ogr.wkbLinearRing)
    bbPoints.AddPoint(0, 90)
    bbPoints.AddPoint(-halfWidth, 0)
    bbPoints.AddPoint(0, -90)
    bbPoints.AddPoint(halfWidth, 0)
    bbPoints.Transform(transform)

    # make the map
    map = mapnik.Map(width, width)   
    map.srs = target.ExportToProj4()  
    map.background = mapnik.Color('#ffffff')
    
    # add and style gore
    s = mapnik.Style()
    r = mapnik.Rule()
    polygon_symbolizer = mapnik.PolygonSymbolizer(mapnik.Color('#000000'))
    r.symbols.append(polygon_symbolizer)
    s.rules.append(r)
    map.append_style('land_style',s)
    ds = mapnik.Shapefile(file="./tmp/tmp_land" + str(number) + ".shp")
    land = mapnik.Layer('land')
    land.datasource = ds
    land.styles.append('land_style')
    map.layers.append(land)
    
    # add and style gore
    s = mapnik.Style()
    r = mapnik.Rule()
    line_symbolizer = mapnik.LineSymbolizer(mapnik.Color('#000000'), gore_stroke)
    r.symbols.append(line_symbolizer)
    s.rules.append(r)
    map.append_style('gore_style',s)
    ds = mapnik.Shapefile(file="./tmp/tmp_gore" + str(number) + ".shp")
    gore = mapnik.Layer('gore')
    gore.datasource = ds
    gore.styles.append('gore_style')
    map.layers.append(gore)
    
    # this grows the image if the map dimensions do not fit the canvas dimensions
    map.aspect_fix_mode = mapnik.aspect_fix_mode.GROW_CANVAS

    # Set the extent (need to set this to around 0 post transformation as this is the central meridian)
    map.zoom_to_box(mapnik.Envelope(bbPoints.GetX(1), bbPoints.GetY(0), bbPoints.GetX(3), bbPoints.GetY(2)))

    # render to file (and show me it)
    mapnik.render_to_file(map, "tmp/gore" + str(number) + ".png")
    
    
##
# Main Function
# @author jonnyhuck
##
def main(argv):

    # make sure the tmp folder exists
    if not os.path.exists("tmp"):
        os.makedirs("tmp")

    # set defaults
    GORE_WIDTH_PX = 500
    GORE_WIDTH_DEG = 60
    OUT_PATH = "globe.png"
    GORE_OUTLINE_WIDTH = 4

    # read in arguments
    try:
        opts, args = getopt.getopt(argv, "hp:d:g:o:")
    except getopt.GetoptError:
        print 'python makeGlobe.py -p [GORE_WIDTH_PX] -d [GORE_WIDTH_DEGREES] -g [GORE_OUTLINE_WIDTH] -o [OUT_PATH]'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'python makeGlobe.py -p [GORE_WIDTH_PX] -d [GORE_WIDTH_DEGREES] -g [GORE_OUTLINE_WIDTH] -o [OUT_PATH]'
            sys.exit()
        elif opt == '-p':
            GORE_WIDTH_PX = int(arg)
        elif opt == '-d':
            GORE_WIDTH_DEG = int(arg)
        elif opt == '-g':
            GORE_OUTLINE_WIDTH = int(arg)
        elif opt == '-o':
            OUT_PATH = arg

    # verify values
    if GORE_WIDTH_PX < 0:
        print "invalid -p (GORE_WIDTH_PX) value: " + str(GORE_WIDTH_PX)
        print "GORE_WIDTH_DEG must be >0."
        sys.exit(0)
    if GORE_WIDTH_DEG < 15 or GORE_WIDTH_DEG > 120 or 360 % GORE_WIDTH_DEG > 0:
        print "invalid -d (GORE_WIDTH_DEG) value: " + str(GORE_WIDTH_PX)
        print "GORE_WIDTH_DEG must be >=15, <=120 and multiply into 360."
        print "Valid numbers include: 120, 90, 60, 30, 20, 15"
        sys.exit(0)

    # how many gores?
    I = 360 / GORE_WIDTH_DEG

    # make a test gore to see how big it is
    makeGore(0, GORE_WIDTH_DEG, 666, GORE_WIDTH_PX, 0)
    im666 = Image.open("tmp/gore666.png")
    w,h = im666.size

    # make 6 gores and join them together into a single image
    # TODO: HOW CAN I WORK OUT 1497?
    im = Image.new("RGB", (GORE_WIDTH_PX * I, h), "white")
    for i in range(0, I):
        cm = -180 + (GORE_WIDTH_DEG/2) + (GORE_WIDTH_DEG * i)
        # blunt fix - stops data wrapping around the world     
        if i == I-1:
            cm -= 0.01
        print cm
        makeGore(cm, GORE_WIDTH_DEG, i, GORE_WIDTH_PX, GORE_OUTLINE_WIDTH)
        im1 = Image.open("tmp/gore" + str(i) + ".png")
        im.paste(im1, (GORE_WIDTH_PX * i,0))

    # clean up all tmp files
    files = os.listdir("tmp")
    for f in files:
        os.remove("tmp/"+f)
    
    # export and display
    im.save(OUT_PATH)
    im.show()

##
# Python nonsense...
# @author jonnyhuck
##
if __name__ == "__main__":
    main(sys.argv[1:])