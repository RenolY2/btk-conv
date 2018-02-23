# btk-conv
Converter between the BTK format and JSON. BTK is used for texture animations (by transformation) in some Nintendo games on the GC, e.g. Super Mario Sunshine and Pikmin 2.

# Requirements
* newest version of Python 3 

The newest version as of the making of this file is 3.6.4: https://www.python.org/downloads/ <br>
When installing it on Windows, make sure you check "Add Python to PATH" so that the included .bat files will work properly.

# Usage
## Drag & Drop
if you are on Windows, the provided btkconvert.bat file allows simply dropping a file on it to convert it.
BTK files will be converted to JSON, and JSON will be converted to BTK. The bat file is set up so that floating point values are rounded to 6 digits after the decimal point and can be modified if more or less precision is wanted.

## Command line usage
```
python ./btk-conv.py [-h] [--ndigits NDIGITS] input [output]

positional arguments:
  input              Path to btk or json-formatted text file.
  output             Path to which the converted file should be written. If
                     input was a BTK, writes a json file. If input was a json
                     file, writes a BTK.If left out, output defaults to
                     <input>.json or <input>.btk.

optional arguments:
  -h, --help         show this help message and exit
  --ndigits NDIGITS  The amount of digits after the decimal point to which
                     values should be rounded when converting btk to json. -1
                     for no rounding.
```

## About the JSON structure
Header:
* loop mode: Effect unknown but might affect how the animation loops
* angle scale: Effect unknown 
* duration: How long the animation plays, unit unknown 
* unknown: Some sort of address? Often 0x801514a8, sometimes zero

Animations:
* material name: Name of the material to which the animation is applied. Name needs to match a material name from the BMD model to which the BTK belongs (when you make custom BMDs, material name in the BMD will be what the material name you are using in the 3d modelling program is)
* material index: Purpose unknown, but when there are two animations with the same material name, one animation has the index 0 and the other has the index 1 (Might apply to more than two too)
* center: Center coordinates in the UVW map?
* scale uvw: Coordinates are scaled by these values. 1.0 for all three for neutral scale.
* rotation uvw: Rotation of coordinates in degrees. Goes from -180 to 180. 0.0 for all three values for neutral.
* translation u, v, w: Moves coordinates (Allows for scrolling textures). 4 values per entry. First value is time at which the translation happens (compare with duration from above). Second is position to which the coordinates are moved. Third and fourth are unknown, but might affect interpolation or speed.

## Tips
* Having trouble making animations? Take existing BTKs, change the material name of the animation to one from your model and experiment with it!
