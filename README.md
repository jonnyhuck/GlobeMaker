#makeGlobe.py
**makeGlobe.py** is a simple Python script that allows you to create a globe.

You can read all about the process at my [blog](http://).

###Dependencies:
* [Python 2.7](http://)
* [OGR](http://)
* [PyProj](http://)
* [Mapnik](http://)
* [PIL](http://)
* [Natural Earth Landmass Data](http://)

###Usage:

#####Parameters:
* `-h` Print out the command usage
* `-p` The width of each gore in pixels. Default: **500**.
* `-d` The width of each gore in degrees (must multiply into 360). Default: **60**.
* `-g` The width of the outline around each gore in pixels . Default: **4**.
* `-o` The name of the output file . Default: **globe.png**.

#####Command:

`python makeGlobe.py -p [GORE_WIDTH_PX] -d [GORE_WIDTH_DEGREES] -g [GORE_OUTLINE_WIDTH] -o [OUT_PATH]`

e.g.:

`python makeGlobe.py -p 100 -d 30 -g 1 -o example.png`

would give you:

![image](http://)

whereas:

`python makeGlobe.py -p 500 -d 120 -g 4 -o example.png`

would give you:

![image](http://)