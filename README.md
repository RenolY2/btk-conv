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
* loop mode: 0 and 1: plays once; 2: loops; 3: Play once forward, then backward; 4: Like 3 but on repeat
* angle scale: Signed byte; Bigger values means bigger angles are possible but steps are more coarse; Vice versa for smaller values
* duration: How long the animation plays in frames
* unknown: Some sort of address? Often 0x801514a8, sometimes zero

Animations:
* material name: Name of the material to which the animation is applied. Name needs to match a material name from the BMD model to which the BTK belongs
* material texture index: For materials with multiple textures, this is the texture to which the animation will be applied
* center: Center coordinates in relation to the UV map, used for rotation

BTK works with keyframes. Each entry in the scale, rotation and translation sections is made of a group of 4 values that form a keyframe. 
First value is the frame number of the keyframe. 
Second is the scale/rotation/translation value, third and fourth are the ingoing and outgoing tangents. 
Tangents affect the interpolation between two consecutive keyframes. BTK uses Cubic Hermite Interpolation for this.

* scale u, v scales the u and v components of the coordinates
* rotate w rotates the UV coords around the center specified above
* translate u, v translates the u and v components, resulting in scrolling

The W component of scale and translate appears to go unused and can likely be ignored.
In contrast, the u and v components for rotation seem to go unused, only the w component actually does rotations.

## Tips
* Having trouble making animations? Take existing BTKs, change the material name of the animation to one from your model and experiment with it!
* An angle scale of 1 means you can have rotations between -180 and 180. An angle scale of 2 allows for -360 to 360.
* For a simple infinite scrolling or rotation animation you only need two keyframes. 
You calculate the tangent value as (key2.val - key1.val) / (key2.frame - key1.frame) and put it as the ingoing and outgoing tangents for the two keyframes.
This gives you an infinite linear animation.
* When making custom models, usually the material names in the modelling program matches the material names in the resulting BMD. Sometimes
a suffix might be appended to the material name on conversion to BMD though (in my testing with exporting DAE in Blender, the material names received
the suffix -material). In this case the material name in the BTK will also need to have the suffix.
* If you are sure you've done everything correct but the animation still doesn't play, it could be that the material you want to animate isn't properly
configured for texture animations.

