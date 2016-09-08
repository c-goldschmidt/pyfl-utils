from .mesh import MeshReader

class VMeshRef(object):
    def __init__(self, raw_data):
        self.raw_data = raw_data
        self._parse()
            
    def _parse(self):
        reader = MeshReader(self.raw_data)
                
        self.header_size = reader.get_dword()
        self.lib_id = reader.get_dword()
        self.start_vertex = reader.get_word()
        self.end_vertex = reader.get_word()
        self.num_verices = reader.get_word()
        self.start_index = reader.get_word()
        self.start_mesh = reader.get_word()
        self.num_meshes = reader.get_word()
        self.bound_max_x = reader.get_float()
        self.bound_min_x = reader.get_float()
        self.bound_max_y = reader.get_float()
        self.bound_min_y = reader.get_float()
        self.bound_max_z = reader.get_float()
        self.bound_min_z = reader.get_float()
        self.center_x = reader.get_float()
        self.center_y = reader.get_float()
        self.center_z = reader.get_float()
        self.radius = reader.get_float()
        