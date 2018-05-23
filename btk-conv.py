import struct 
import json 
import codecs
import io
from collections import OrderedDict
BTKFILEMAGIC = b"J3D1btk1"
PADDING = b"This is padding data to align"

def read_uint32(f):
    return struct.unpack(">I", f.read(4))[0]
def read_uint16(f):
    return struct.unpack(">H", f.read(2))[0]
def read_sint16(f):
    return struct.unpack(">h", f.read(2))[0]
def read_uint8(f):
    return struct.unpack(">B", f.read(1))[0]
def read_float(f):
    return struct.unpack(">f", f.read(4))[0]
    
    
def write_uint32(f, val):
    f.write(struct.pack(">I", val))
def write_uint16(f, val):
    f.write(struct.pack(">H", val))
def write_sint16(f, val):
    f.write(struct.pack(">h", val))
def write_uint8(f, val):
    f.write(struct.pack(">B", val))
def write_float(f, val):
    f.write(struct.pack(">f", val))

def write_padding(f, multiple):
    next_aligned = (f.tell() + (multiple - 1)) & ~(multiple - 1)
    
    diff = next_aligned - f.tell()
    
    for i in range(diff):
        pos = i%len(PADDING)
        f.write(PADDING[pos:pos+1])

# Optional rounding
def opt_round(val, digits):
    if digits is None:
        return val
    else:
        return round(val, digits)

def write_indented(f, text, level):
    f.write(" "*level)
    f.write(text)
    f.write("\n")

# Find the start of the sequence seq in the list in_list, if the sequence exists
def find_sequence(in_list, seq):
    matchup = 0
    start = -1

    found = False
    started = False

    for i, val in enumerate(in_list):
        if val == seq[matchup]:
            if not started:
                start = i
                started = True

            matchup += 1
            if matchup == len(seq):
                #start = i-matchup
                found = True
                break
        else:
            matchup = 0
            start = -1
            started = False
    if not found:
        start = -1


    return start

class StringTable(object):
    def __init__(self):
        self.strings = []
    
    @classmethod
    def from_file(cls, f):
        stringtable = cls()
        
        start = f.tell()
        
        string_count = read_uint16(f)
        f.read(2) # 0xFFFF
        
        offsets = []
        
        print("string count", string_count)
        
        for i in range(string_count):
            hash = read_uint16(f)
            string_offset = read_uint16(f)
            
            offsets.append(string_offset)
        
        for offset in offsets:
            f.seek(start+offset)
            
            # Read 0-terminated string 
            string_start = f.tell()
            string_length = 0
            
            while f.read(1) != b"\x00":
                string_length += 1 
            
            f.seek(start+offset)
            
            if string_length == 0:
                stringtable.strings.append("")
            else:
                stringtable.strings.append(f.read(string_length).decode("shift-jis"))
            
        return stringtable 
            
    def hash_string(self, string):
        hash = 0
        
        for char in string:
            hash *= 3 
            hash += ord(char)
            hash = 0xFFFF & hash  # cast to short 
        
        return hash

    def write(self, f):
        start = f.tell()
        f.write(struct.pack(">HH", len(self.strings), 0xFFFF))
        
        for string in self.strings:
            hash = self.hash_string(string)
            
            f.write(struct.pack(">HH", hash, 0xABCD))
        
        offsets = []
        
        for string in self.strings:
            offsets.append(f.tell())
            f.write(string.encode("shift-jis"))
            f.write(b"\x00")

        end = f.tell()

        for i, offset in enumerate(offsets):
            f.seek(start+4 + (i*4) + 2)
            write_uint16(f, offset-start)

        f.seek(end)
        
class MatrixAnimation(object):
    def __init__(self, index, matindex, name, center):
        self._index = index 
        self.matindex = matindex 
        self.name = name 
        self.center = center
        
        self.scale = {"U": [], "V": [], "W": []}
        self.rotation = {"U": [], "V": [], "W": []}
        self.translation = {"U": [], "V": [], "W": []}

        self._scale_offsets = {}
        self._rot_offsets = {}
        self._translation_offsets = {}

    def add_scale(self, axis, scale):
        self.scale[axis].append(scale)
    
    def add_rotation(self, axis, rotation):
        self.rotation[axis].append(rotation)

    def add_scale_vec(self, u, v, w):
        self.add_scale("U", u)
        self.add_scale("V", v)
        self.add_scale("W", w)

    def add_rotation_vec(self, u, v, w):
        self.add_rotation("U", u)
        self.add_rotation("V", v)
        self.add_rotation("W", w)

    def add_translation(self, axis, t1, t2, t3, t4):
        self.translation[axis].append((t1, t2, t3, t4))

    # These functions are used for keeping track of the offset
    # in the json->btk conversion and are otherwise not useful.
    def _set_scale_offsets(self, axis, val):
        self._scale_offsets[axis] = val

    def _set_rot_offsets(self, axis, val):
        self._rot_offsets[axis] = val

    def _set_translation_offsets(self, axis, val):
        self._translation_offsets[axis] = val


class BTKAnim(object):
    def __init__(self, loop_mode, anglescale, duration, unknown_address=0):
        self.animations = []
        self.loop_mode = loop_mode
        self.anglescale = anglescale
        self.duration = duration
        self.unknown_address = unknown_address
    
    def dump(self, f, digits=None):
        write_indented(f, "{", level=0)

        write_indented(f, "\"loop_mode\": {},".format(self.loop_mode), level=4)
        write_indented(f, "\"angle_scale\": {},".format(self.anglescale), level=4)
        write_indented(f, "\"duration\": {},".format(self.duration), level=4)
        write_indented(f, "\"unknown\": \"0x{:x}\",".format(self.unknown_address), level=4)
        write_indented(f, "", level=4)
        write_indented(f, "\"animations\": [", level=4)

        anim_count = len(self.animations)
        for i, animation in enumerate(self.animations):
            write_indented(f, "{", level=8)

            write_indented(f, "\"material_name\": \"{}\",".format(animation.name), level=12)
            write_indented(f, "\"material_index\": {},".format(animation.matindex), level=12)
            write_indented(f,
                           "\"center\": [{}, {}, {}],".format(
                               *(opt_round(x, digits) for x in animation.center)),
                           level=12)

            write_indented(f, "", level=12)

            write_indented(f, "\"scale_uvw\": [", level=12)
            scales = len(animation.scale["U"])
            for j, vals in enumerate(zip(animation.scale["U"], animation.scale["V"], animation.scale["W"])):
                u,v,w = vals
                if j < scales-1:
                    write_indented(f,
                                   "[{}, {}, {}],".format(
                                       opt_round(u, digits), opt_round(v, digits), opt_round(w, digits)),
                                   level=16)
                else:
                    write_indented(f,
                                   "[{}, {}, {}]".format(
                                       opt_round(u, digits), opt_round(v, digits), opt_round(w, digits)),
                                   level=16)

            write_indented(f, "],", level=12)
            write_indented(f, "", level=12)

            write_indented(f, "\"rotation_uvw\": [", level=12)
            rotations = len(animation.rotation["U"])
            for j, vals in enumerate(zip(animation.rotation["U"], animation.rotation["V"], animation.rotation["W"])):
                u,v,w = vals
                if j < rotations-1:
                    write_indented(f,
                                   "[{}, {}, {}],".format(
                                       opt_round(u, digits), opt_round(v, digits), opt_round(u, digits)),
                                    level=16)
                else:
                    write_indented(f,
                                   "[{}, {}, {}]".format(
                                       opt_round(u, digits), opt_round(v, digits), opt_round(u, digits)),
                                   level=16)

            write_indented(f, "],", level=12)
            write_indented(f, "", level=12)

            for axis in "UVW":
                write_indented(f, "\"translation_{}\": [".format(axis.lower()), level=12)
                trans_count = len(animation.translation[axis])
                for j, vals in enumerate(animation.translation[axis]):
                    if j < trans_count-1:
                        write_indented(f,
                                       "[{}, {}, {}, {}],".format(
                                           *(opt_round(x, digits) for x in vals)),
                                       level=16)
                    else:
                        write_indented(f,
                                       "[{}, {}, {}, {}]".format(
                                           *(opt_round(x, digits) for x in vals)),
                                       level=16)
                if axis != "W":
                    write_indented(f, "],", level=12)
                else:
                    write_indented(f, "]", level=12)

            if i < anim_count-1:
                write_indented(f, "},", level=8)
            else:
                write_indented(f, "}", level=8)

        write_indented(f, "]", level=4)
        write_indented(f, "}", level=0)

    def write_btk(self, f):
        f.write(BTKFILEMAGIC)
        filesize_offset = f.tell()
        f.write(b"ABCD") # Placeholder for file size
        write_uint32(f, 1) # Always a section count of 1
        f.write(b"SVR1" + b"\xFF"*12)

        ttk1_start = f.tell()
        f.write(b"TTK1")

        ttk1_size_offset = f.tell()
        f.write(b"EFGH")  # Placeholder for ttk1 size
        write_uint8(f, self.loop_mode)
        write_uint8(f, self.anglescale)
        write_uint16(f, self.duration)
        write_uint16(f, len(self.animations)*3) # Three times the matrix animations
        count_offset = f.tell()
        f.write(b"1+1=11")  # Placeholder for scale, rotation and translation count
        data_offsets = f.tell()
        f.write(b"--OnceUponATimeInALandFarAway---")
        f.write(b"\x00"*(0x7C - f.tell()))

        write_uint32(f, self.unknown_address)

        matrix_anim_start = f.tell()
        f.write(b"\x00"*(0x36*len(self.animations)))
        write_padding(f, multiple=4)

        index_start = f.tell()
        for i in range(len(self.animations)):
            write_uint16(f, i)

        write_padding(f, multiple=4)

        stringtable = StringTable()

        for anim in self.animations:
            stringtable.strings.append(anim.name)

        stringtable_start = f.tell()
        stringtable.write(f)

        write_padding(f, multiple=4)

        matindex_start = f.tell()
        for anim in self.animations:
            write_uint8(f, anim.matindex)

        write_padding(f, multiple=4)

        center_start = f.tell()
        for anim in self.animations:
            for val in anim.center:
                write_float(f, val)

        write_padding(f, multiple=4)


        all_scales = []
        all_rotations = []
        all_translations = []
        for anim in self.animations:
            for axis in "UVW":
                # Set up offset for scale
                offset = find_sequence(all_scales, anim.scale[axis])
                if offset == -1:
                    offset = len(all_scales)
                    all_scales.extend(anim.scale[axis])

                anim._set_scale_offsets(axis, offset)

                # Set up offset for rotation
                offset = find_sequence(all_rotations, anim.rotation[axis])
                if offset == -1:
                    offset = len(all_rotations)
                    all_rotations.extend(anim.rotation[axis])

                anim._set_rot_offsets(axis, offset)

                # Set up offset for translation
                offset = find_sequence(all_translations, anim.translation[axis])
                if offset == -1:
                    offset = len(all_translations)
                    all_translations.extend(anim.translation[axis])

                anim._set_translation_offsets(axis, offset)

        scale_start = f.tell()
        for val in all_scales:
            write_float(f, val)

        write_padding(f, 4)

        rotations_start = f.tell()
        for val in all_rotations:
            angle = ((val+180) % 360) - 180  # Force the angle between -180 and 180 degrees
            print(val, "becomes", angle)
            if angle >= 0:
                angle = (angle/180.0)*(2**15-1)
            else:
                angle = (angle/180.0)*(2**15)
            write_sint16(f, int(angle))

        write_padding(f, 4)

        translations_start = f.tell()
        for t1, t2, t3, t4 in all_translations:
            write_float(f, t1)
            write_float(f, t2)
            write_float(f, t3)
            write_float(f, t4)

        write_padding(f, 4)

        total_size = f.tell()

        f.seek(matrix_anim_start)
        for anim in self.animations:
            for axis in "UVW":
                write_uint16(f, len(anim.scale[axis])) # Scale count for this animation
                write_uint16(f, anim._scale_offsets[axis]) # Offset into scales
                write_uint16(f, 1) # Unknown but always 1?


                write_uint16(f, len(anim.rotation[axis])) # Rotation count for this animation
                write_uint16(f, anim._rot_offsets[axis]) # Offset into scales
                write_uint16(f, 1) # Unknown but always 1?


                write_uint16(f, len(anim.translation[axis])) # Translation count for this animation

                # Offset into scales. Note that the offset is into separate float values
                # while every translation has 4 float values per count
                write_uint16(f, anim._translation_offsets[axis]*4)
                write_uint16(f, 1) # Unknown but always 1?


        # Fill in all the placeholder values
        f.seek(filesize_offset)
        write_uint32(f, total_size)

        f.seek(ttk1_size_offset)
        write_uint32(f, total_size - ttk1_start)

        f.seek(count_offset)
        write_uint16(f, len(all_scales))
        write_uint16(f, len(all_rotations))
        write_uint16(f, len(all_translations)*4)
        # Next come the section offsets

        write_uint32(f, matrix_anim_start   - ttk1_start)
        write_uint32(f, index_start         - ttk1_start)
        write_uint32(f, stringtable_start   - ttk1_start)
        write_uint32(f, matindex_start      - ttk1_start)
        write_uint32(f, center_start        - ttk1_start)
        write_uint32(f, scale_start         - ttk1_start)
        write_uint32(f, rotations_start     - ttk1_start)
        write_uint32(f, translations_start  - ttk1_start)

    @classmethod
    def from_json(cls, f):
        btkanimdata = json.load(f)

        btk = cls(
            btkanimdata["loop_mode"], btkanimdata["angle_scale"],
            btkanimdata["duration"], unknown_address=int(btkanimdata["unknown"], 16)
        )

        for i, animation in enumerate(btkanimdata["animations"]):
            matanim = MatrixAnimation(i, animation["material_index"], animation["material_name"], animation["center"])

            for scale in animation["scale_uvw"]:
                matanim.add_scale_vec(*scale)
            for rotation in animation["rotation_uvw"]:
                matanim.add_rotation_vec(*rotation)
            for translation in animation["translation_u"]:
                matanim.add_translation("U", *translation)
            for translation in animation["translation_v"]:
                matanim.add_translation("V", *translation)
            for translation in animation["translation_w"]:
                matanim.add_translation("W", *translation)
            btk.animations.append(matanim)

        return btk

    @classmethod
    def from_btk(cls, f):
        header = f.read(8)
        if header != BTKFILEMAGIC:
            raise RuntimeError("Invalid header. Expected {} but found {}".format(BTKFILEMAGIC, header))

        size = read_uint32(f)
        print("Size of btk: {} bytes".format(size))
        sectioncount = read_uint32(f)
        assert sectioncount == 1

        svr_data = f.read(16)
        
        ttk_start = f.tell()
        
        ttk_magic = f.read(4)
        ttk_sectionsize = read_uint32(f)

        loop_mode = read_uint8(f)
        anglescale = read_uint8(f)
        duration = read_uint16(f)
        btk = cls(loop_mode, anglescale, duration)


        threetimestexmatanims = read_uint16(f)
        scale_count = read_uint16(f)
        rotation_count = read_uint16(f)
        translation_count = read_uint16(f)

        print("three times texmat anims", threetimestexmatanims)
        print("scale count", scale_count)
        print("rotation count", rotation_count)
        print("translation count", translation_count)

        texmat_anim_offset  = read_uint32(f) + ttk_start    # J3DAnmTransformKeyTable
        index_offset        = read_uint32(f) + ttk_start    # unsigned short
        stringtable_offset  = read_uint32(f) + ttk_start    # 0 terminated strings 
        texmat_index_offset = read_uint32(f) + ttk_start    # unsigned byte
        center_offset       = read_uint32(f) + ttk_start    # Vector with 3 entries
        scale_offset        = read_uint32(f) + ttk_start    # float 
        rotation_offset     = read_uint32(f) + ttk_start    # signed short 
        translation_offset  = read_uint32(f) + ttk_start    # float 



        print("Position:", hex(f.tell()))
        print("tex anim offset", hex(texmat_anim_offset))
        print("index offset", hex(index_offset))
        print("mat name offset", hex(stringtable_offset))
        print("texmat index offset", hex(texmat_index_offset))
        print("center offset", hex(center_offset))
        print("scale offset", hex(scale_offset))
        print("rotation offset", hex(rotation_offset))
        print("translation offset", hex(translation_offset))
        
        anim_count = threetimestexmatanims//3
        print("Animation count:", anim_count)

        f.seek(0x7C)
        unknown_address = read_uint32(f)
        btk.unknown_address = unknown_address
        # Read indices
        indices = []
        f.seek(index_offset)
        for i in range(anim_count):
            indices.append(read_uint16(f))
        
        # Read matrix indices 
        mat_indices = []
        f.seek(texmat_index_offset)
        for i in range(anim_count):
            mat_indices.append(read_uint8(f))
        
        # Read stringtable 
        f.seek(stringtable_offset)
        stringtable = StringTable.from_file(f)
        
        
        # Read scales 
        scales = []
        f.seek(scale_offset)
        for i in range(scale_count):
            scales.append(read_float(f))
        
        # Read rotations
        rotations = []
        f.seek(rotation_offset)
        for i in range(rotation_count):
            rotations.append((read_sint16(f)/32768.0)*180)
        
        # Read translations 
        translations = []
        f.seek(translation_offset)
        for i in range(translation_count):
            translations.append(read_float(f))
        
        # Read data per animation
        for i in indices:
            mat_index = mat_indices[i]
            
            # Read center for this animation
            f.seek(center_offset + 12*i)
            center = struct.unpack(">fff", f.read(12))
            
            name = stringtable.strings[i]
            print("================")
            print("anim", i)
            print("mat index", mat_index, "name", name, "center", center)
            
            f.seek(texmat_anim_offset + i*0x36)
            print(hex(texmat_anim_offset + i*0x36))
            values = struct.unpack(">"+"H"*27, f.read(0x36))
            
            u_scale, u_rot, u_trans = values[:3], values[3:6], values[6:9]
            v_scale, v_rot, v_trans = values[9:12], values[12:15], values[15:18]
            w_scale, w_rot, w_trans = values[18:21], values[21:24], values[24:27]
            
            matrix_animation = MatrixAnimation(i, mat_index, name, center)
            
            for scale, axis in ((u_scale, "U"), (v_scale, "V"), (w_scale, "W")):
                count, offset, unknown = scale 
                print(axis, count)
                for j in range(count):
                    scale_val = scales[offset+j]
                    matrix_animation.add_scale(axis, scale_val)
            
            for rotation, axis in ((u_rot, "U"), (v_rot, "V"), (w_rot, "W")):
                count, offset, unknown = rotation 
                for j in range(count):
                    rot_val = rotations[offset+j]
                    matrix_animation.add_rotation(axis, rot_val)
                    
            for translation, axis in ((u_trans, "U"), (v_trans, "V"), (w_trans, "W")):
                count, offset, unknown = translation
                for j in range(count):
                    t1, t2, t3, t4 = translations[offset+j*4:offset+(j+1)*4]
                    matrix_animation.add_translation(axis, t1, t2, t3, t4)        
            
            
       
            print(u_scale, u_rot, u_trans)
            
            print(v_scale, v_rot, v_trans)
            
            print(w_scale, w_rot, w_trans)
            btk.animations.append(matrix_animation)
            
        return btk
    
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input",
                        help="Path to btk or json-formatted text file.")
    parser.add_argument("--ndigits", default=-1, type=int,
                        help="The amount of digits after the decimal point to which values should be rounded "
                             "when converting btk to json. -1 for no rounding.")
    parser.add_argument("output", default=None, nargs = '?',
                        help=(
                            "Path to which the converted file should be written. "
                            "If input was a BTK, writes a json file. If input was a json file, writes a BTK."
                            "If left out, output defaults to <input>.json or <input>.btk."
                        ))

    args = parser.parse_args()

    if args.ndigits < 0:
        ndigits = None
    else:
        ndigits = args.ndigits


    with open(args.input, "rb") as f:
        if f.read(8) == BTKFILEMAGIC:
            btk_to_json = True
        else:
            btk_to_json = False

    if args.output is None:
        if btk_to_json:
            output = args.input+".json"
        else:
            output = args.input+".btk"
    else:
        output = args.output

    if btk_to_json:
        with open(args.input, "rb") as f:
            btk = BTKAnim.from_btk(f)
        with open(output, "w") as f:
            btk.dump(f, digits=ndigits)
    else:
        # Detect BOM of input file
        with open(args.input, "rb") as f:
            bom = f.read(4)
        
        if bom.startswith(codecs.BOM_UTF8):
            encoding = "utf-8-bom"
        elif bom.startswith(codecs.BOM_UTF32_LE) or bom.startswith(codecs.BOM_UTF32_BE):
            encoding = "utf-32"
        elif bom.startswith(codecs.BOM_UTF16_LE) or bom.startswith(codecs.BOM_UTF16_BE):
            encoding = "utf-16"
        else:
            encoding = "utf-8"
        
        print("Assuming encoding of input file:", encoding)
        
        with io.open(args.input, "r", encoding=encoding) as f:
            #with open(args.input, "rb") as f:
            btk = BTKAnim.from_json(f)
        with open(output, "wb") as f:
            btk.write_btk(f)
