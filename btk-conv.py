import struct 
import json 
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

def write_padding(f, multiple):
    next_aligned = (f.tell() + (multiple - 1)) & ~(multiple - 1)
    
    diff = next_aligned - f.tell()
    
    for i in range(diff):
        pos = i%len(PADDING)
        f.write(PADDING[pos:pos+1])

def format_floatlist(floatlist):
    return " ".join(str(round(val, 5)) for val in floatlist)
        
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
        
        write_padding(f, 4) #pad to multiple of 4
            
        
class MatrixAnimation(object):
    def __init__(self, index, matindex, name, center):
        self._index = index 
        self.matindex = matindex 
        self.name = name 
        self.center = center
        
        self.scale = {"U": [], "V": [], "W": []}
        self.rotation = {"U": [], "V": [], "W": []}
        self.translation = {"U": [], "V": [], "W": []}
    
    def add_scale(self, axis, scale):
        self.scale[axis].append(scale)
    
    def add_rotation(self, axis, rotation):
        self.rotation[axis].append(rotation)
    
    def add_translation(self, axis, t1, t2, t3, t4):
        self.translation[axis].append((t1, t2, t3, t4))
        
        
class BTKAnim(object):
    def __init__(self, loop_mode, anglescale, duration):
        self.animations = []
        self.loop_mode = loop_mode
        self.anglescale = anglescale
        self.duration = duration
    
    def dump(self, f):
        out = OrderedDict()
        out["Loop mode"] = self.loop_mode
        out["Angle scale"] = self.anglescale 
        out["Duration"] = self.duration
        out["Animations"] = []
        
        for animation in self.animations:
            anim = OrderedDict()
            anim["Name"] = animation.name 
            anim["Center"] = animation.center 
            anim["Material Index"] = animation.matindex
            anim["Scale U"] = animation.scale["U"]
            anim["Scale V"] = animation.scale["V"]
            anim["Scale W"] = animation.scale["W"]
            anim["Rotation U"] = animation.rotation["U"]
            anim["Rotation V"] = animation.rotation["V"]
            anim["Rotation W"] = animation.rotation["W"]
            
            anim["Translation U"] = [
                format_floatlist(val) for val in animation.translation["U"]
                ]
            
            anim["Translation V"] = [
                format_floatlist(val) for val in animation.translation["V"]
                ]
            anim["Translation W"] = [
                format_floatlist(val) for val in animation.translation["W"]
                ]

            out["Animations"].append(anim)
        
        json.dump(out, f, indent=4)
        
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
            
            
            
            
        
        
    def from_txt(self, f):
        pass
    
if __name__ == "__main__":
    with open("sea.btk", "rb") as f:
        mybtk = BTKAnim.from_btk(f)
        
    with open("btkdumped.txt", "w") as f:
        mybtk.dump(f)