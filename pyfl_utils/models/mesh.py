import json
import struct
import hashlib


class MeshHeader(object):
    def __init__(self):
        self.material_id = None
        self.start_vertex = None
        self.end_vertex = None
        self.num_ref_vertices = None
        self.padding = 204
        self.triangle_start = None
        

class MeshTriangle(object):
    def __init__(self):
        self.vertex_1 = None
        self.vertex_2 = None
        self.vertex_3 = None
        
        
class MeshVertex(object):
    def __init__(self):
        self.vertex_format = None
        self.x = None
        self.y = None   
        self.z = None   
        self.normal_x = None  
        self.normal_y = None   
        self.normal_z = None   
        self.diffuse = None   
        self.s = None  
        self.t = None  
        self.u = None  
        self.v = None  
        self.tangent_x = None  
        self.tangent_y = None   
        self.tangent_z = None    
        self.binormal_x = None   
        self.binormal_y = None   
        self.binormal_z = None

    @property
    def hash(self):
        self.update_vertex_format()
        return hashlib.sha1(json.dumps({
            'vertex_format': self.vertex_format,
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'normal_x': self.normal_x,
            'normal_y': self.normal_y,
            'normal_z': self.normal_z,
            'diffuse': self.diffuse,
            's': self.s,
            't': self.t,
            'u': self.u,
            'v': self.v,
            'tangent_x': self.tangent_x,
            'tangent_y': self.tangent_y,
            'tangent_z': self.tangent_z,
            'binormal_x': self.binormal_x,
            'binormal_y': self.binormal_y,
            'binormal_z': self.binormal_z,
        }).encode('utf-8')).hexdigest()

    def update_vertex_format(self):
        format = 0x00

        if self.binormal_x is not None and self.u is not None:
            format = format | MeshConstants.D3DFVF_TEX5
        elif self.binormal_x is not None:
            format = format | MeshConstants.D3DFVF_TEX4
        elif self.u is not None:
            format = format | MeshConstants.D3DFVF_TEX2
        elif self.s is not None:
            format = format | MeshConstants.D3DFVF_TEX1
        else:
            format = format | MeshConstants.D3DFVF_TEX0

        if self.x is not None:
            format = format | MeshConstants.D3DFVF_XYZ

        if self.normal_x is not None:
            format = format | MeshConstants.D3DFVF_NORMAL

        if self.diffuse is not None:
            format = format | MeshConstants.D3DFVF_DIFFUSE

        self.vertex_format = format


class FixNode(object):    
    def __init__(self):
        self.parent_name = None
        self.child_name = None
        
        self.origin_x = None
        self.origin_y = None
        self.origin_z = None
        
        self.offset_x = 0
        self.offset_y = 0
        self.offset_z = 0
        
        self.rot_mat_xx = None
        self.rot_mat_xy = None
        self.rot_mat_xz = None
        
        self.rot_mat_yx = None
        self.rot_mat_yy = None
        self.rot_mat_yz = None
        
        self.rot_mat_zx = None
        self.rot_mat_zy = None
        self.rot_mat_zz = None
        
        
class RevNode(FixNode):
    def __init__(self):
        super(RevNode, self).__init__()
        
        self.axis_rot_x = None
        self.axis_rot_y = None
        self.axis_rot_z = None
        
        self.min = None
        self.max = None
        
        
class SphNode(FixNode):
    def __init__(self):
        super(SphNode, self).__init__()
          
        self.min_x = None
        self.max_x = None
        
        self.min_y = None
        self.max_y = None   
        
        self.min_z = None
        self.max_z = None
        

class PrisNode(RevNode):
    def __init__(self):
        super(PrisNode, self).__init__()
        

class Texture(object):
    def __init__(self):
        self.ix = None
        self.iy = None
        self.rgb_matrix = None
        self.inversion = None


class MeshReader(object):

    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.read_position = 0
        
    def rewind(self):
        self.read_position = 0
    
    def get_dword(self):
        start = self.read_position
        end = self.read_position + 4
        
        self.read_position = end
        
        return struct.unpack('L', self.raw_data[start:end])[0]
        
    def get_float(self):
        start = self.read_position
        end = self.read_position + 4
        
        self.read_position = end
        
        return struct.unpack('f', self.raw_data[start:end])[0]
        
    def get_word(self):
        start = self.read_position
        end = self.read_position + 2
                
        self.read_position = end
        
        return struct.unpack('H', self.raw_data[start:end])[0]
        
    def get_string(self, max_length):
        start = self.read_position        
        self.read_position += max_length
        
        string = ''
        for i in range(max_length):
            offset = start + i
            char = chr(self.raw_data[offset])
            if char != '\x00':
                offset += 1
                string += char
            else:
                break
                
        return string


class MeshWriter(object):

    def __init__(self):
        self.raw_data = bytes()

    def set_dword(self, data):
        self.raw_data += struct.pack('L', data)

    def set_float(self, data):
        self.raw_data += struct.pack('f', data)

    def set_word(self, data):
        self.raw_data += struct.pack('H', data)

    def set_string(self, data, padded_length=None):
        if not padded_length:
            padded_length = len(data)

        self.raw_data += data.encode('UTF-8')
        add_nulls = padded_length - len(data)
        for _ in range(add_nulls):
            self.raw_data += b'\x00'

        
class MeshConstants(object):

    D3DFVF_RESERVED0 = 0x001
    D3DFVF_XYZ = 0x002
    D3DFVF_XYZRHW = 0x004
    D3DFVF_XYZB1 = 0x006
    D3DFVF_XYZB2 = 0x008
    D3DFVF_XYZB3 = 0x00a
    D3DFVF_XYZB4 = 0x00c
    D3DFVF_XYZB5 = 0x00e

    D3DFVF_NORMAL = 0x010
    D3DFVF_RESERVED1 = 0x020
    D3DFVF_DIFFUSE = 0x040
    D3DFVF_SPECULAR = 0x080

    D3DFVF_TEXCOUNT_MASK = 0xf00
    D3DFVF_TEX0 = 0x000
    D3DFVF_TEX1 = 0x100
    D3DFVF_TEX2 = 0x200
    D3DFVF_TEX3 = 0x300
    D3DFVF_TEX4 = 0x400
    D3DFVF_TEX5 = 0x500
    D3DFVF_TEX6 = 0x600
    D3DFVF_TEX7 = 0x700
    D3DFVF_TEX8 = 0x800
    
    SUPPORTED_TYPES = [
        0x02, 0x12, 0x102, 0x112, 0x142, 
        0x152, 0x212, 0x252, 0x412, 0x512        
    ]
    
    CUBE_VERTICES = [
        (1, -1, -1),
        (1, 1, -1),
        (-1, 1, -1),
        (-1, -1, -1),
        (1, -1, 1),
        (1, 1, 1),
        (-1, -1, 1),
        (-1, 1, 1)
    ]
