from ctypes import *

from .mesh import MeshReader, MeshWriter


class VMeshRefStruct(Structure):
    _fields_ = [
        ('header_size', c_ulong),
        ('lib_id', c_ulong),
        ('start_vertex', c_ushort),
        ('end_vertex', c_ushort),
        ('num_vertices', c_ushort),
        ('start_index', c_ushort),
        ('start_mesh', c_ushort),
        ('num_meshes', c_ushort),
        ('bound_max_x', c_float),
        ('bound_min_x', c_float),
        ('bound_max_y', c_float),
        ('bound_min_y', c_float),
        ('bound_max_z', c_float),
        ('bound_min_z', c_float),
        ('center_x', c_float),
        ('center_y', c_float),
        ('center_z', c_float),
        ('radius', c_float),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header_size = sizeof(VMeshRefStruct)

    def to_raw_data(self):
        buffer = create_string_buffer(sizeof(self))
        memmove(buffer, addressof(self), sizeof(self))
        return buffer.raw

    def parse(self, data):
        memmove(addressof(self), data, sizeof(self))


class VMeshRef(VMeshRefStruct):
    def __init__(self, raw_data=None):
        super().__init__()

        if raw_data:
            self.parse(raw_data)
