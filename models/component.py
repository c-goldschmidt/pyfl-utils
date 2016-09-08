import numpy as np

from .mesh import (
    MeshReader,
    FixNode,
    RevNode,
    SphNode,
    PrisNode,
)


class Component(object):
    
    def __init__(self, cmp):        
        self.fix_data = {}
        self.rev_data = {} 
        self.pris_data = {} 
        self.sph_data = {}          
        self.offsets_by_part_name = {}
        self.rotations_by_part_name = {}
        self.part_names_by_db_name = {}
        
        self._parse_comp_data_nodes(cmp)      

        if 'Cons' not in self._component_data:
            self.has_data = False
            return        
            
        self.has_data = True
        
        self._parse_fix()
        self._parse_revolute()
        self._parse_sphere()
        self._parse_pris()
        self._build_offsets()
    
    def get_offset(self, db_name):
        offsets = {'x':0, 'y': 0, 'z': 0}
        
        try:
            db_name = db_name.decode('utf-8')
        except:
            pass
                                
        if db_name not in self.part_names_by_db_name:
            return offsets, False
            
        part_name = self.part_names_by_db_name[db_name]
                
        if part_name not in self.offsets_by_part_name:
            return offsets, False
                
        return self.offsets_by_part_name[part_name], True
        
    def get_rotation(self, db_name):
        rotation = np.matrix([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ])
        
        try:
            db_name = db_name.decode('utf-8')
        except:
            pass
                                
        if db_name not in self.part_names_by_db_name:
            return rotation
        
        part_name = self.part_names_by_db_name[db_name]
        
        if part_name not in self.rotations_by_part_name:
            return rotation
                
        return self.rotations_by_part_name[part_name]      
    
    def _parse_comp_data_nodes(self, cmp):
        self.comp_data = cmp.find_nodes_with_name_in_path('\\Cmpnd')
                
        self._component_data = {}
        for node in self.comp_data:
            self._component_data[node['name']] = node
    
    def _build_offsets(self):
        for part in self._component_data:
            if part not in ['Cons']:
                object_name = self._component_data[part].get_node_data('Object name')
                file_name = self._component_data[part].get_node_data('File name')
                                
                # remove zero-terminator
                object_name = self._unpack_name(object_name['data'])
                file_name = self._unpack_name(file_name['data'])
                
                offsets = self._build_offset_to_root(object_name)
                rotations = self._build_rotation_to_root(object_name)
                
                self.offsets_by_part_name[object_name] = offsets     
                self.rotations_by_part_name[object_name] = rotations                 
                self.part_names_by_db_name[file_name] = object_name
                
    def _build_offset_to_root(self, part, offsets=None):
        if not offsets:
            offsets = {'x':0, 'y': 0, 'z': 0}
        try:
            part = part.decode('utf-8')
        except:
            pass
        
        node = self._get_node_by_part_name(part)
        if not node:
            return offsets
                                
        offsets['x'] += node.origin_x
        offsets['y'] += node.origin_y
        offsets['z'] += node.origin_z
            
        if node.parent_name != 'Root':
            offsets = self._build_offset_to_root(node.parent_name, offsets)
            
        return offsets
        
    def _build_rotation_to_root(self, part, rotations=None):
        if rotations is None:
            rotations = np.matrix([
                [1, 0, 0],
                [0, 1, 0],
                [0, 0, 1],
            ])      
        try:
            part = part.decode('utf-8')
        except:
            pass
            
        node = self._get_node_by_part_name(part)
        if not node:
            return rotations
            
        new_rotations = np.matrix([
            [node.rot_mat_xx, node.rot_mat_xy, node.rot_mat_xz],
            [node.rot_mat_yx, node.rot_mat_yy, node.rot_mat_yz],
            [node.rot_mat_zx, node.rot_mat_zy, node.rot_mat_zz],
        ])
            
        rotations = np.matmul(rotations, new_rotations)
                
        if node.parent_name != 'Root':
            rotations = self._build_rotation_to_root(node.parent_name, rotations)
            
        return rotations        
    
    def _get_node_by_part_name(self, part):
        node = None
        
        if part in self.fix_data:
            node = self.fix_data[part]
        elif part in self.rev_data:
            node = self.rev_data[part]
        elif part in self.sph_data:
            node = self.sph_data[part]
        elif part in self.pris_data:
            node = self.pris_data[part]
            
        return node
        
    def _parse_fix(self):
        node = self._component_data['Cons'].get_node_data('Fix')
        
        if not node:
            return
            
        count = int(len(node['data']) / 176)
        reader = MeshReader(node['data'])
                
        for _ in range(count):
            part = FixNode()
            part.parent_name = reader.get_string(64)
            part.child_name = reader.get_string(64)
            
            self._read_origin(part, reader)
            self._read_rotation_matrix(part, reader)
            
            self.fix_data[part.child_name] = part
    
    def _parse_revolute(self):
        node = self._component_data['Cons'].get_node_data('Rev')
        
        if not node:
            return
            
        count = int(len(node['data']) / 208)
        reader = MeshReader(node['data'])
                
        for _ in range(count):
            part = RevNode()
            
            part.parent_name = reader.get_string(64)
            part.child_name = reader.get_string(64)
            
            self._read_origin(part, reader)
            self._read_offset(part, reader)
            self._read_rotation_matrix(part, reader)
            
            part.axis_rot_x = reader.get_float()
            part.axis_rot_y = reader.get_float()
            part.axis_rot_z = reader.get_float()
            part.min = reader.get_float()
            part.max = reader.get_float()
            
            self.rev_data[part.child_name] = part
        
    def _parse_sphere(self):
        node = self._component_data['Cons'].get_node_data('Sphere')
        
        if not node:
            return
            
        count = int(len(node['data']) / 212)
        reader = MeshReader(node['data'])
        
        for _ in range(count):
            part = SphNode()
            
            part.parent_name = reader.get_string(64)
            part.child_name = reader.get_string(64)
            
            self._read_origin(part, reader)
            self._read_offset(part, reader)
            self._read_rotation_matrix(part, reader)
            
            part.min_x = reader.get_float()
            part.max_x = reader.get_float()
            part.min_y = reader.get_float()
            part.max_y = reader.get_float()
            part.min_z = reader.get_float()
            part.max_z = reader.get_float()
            
            self.sph_data[part.child_name] = part
            
    def _parse_pris(self):
        node = self._component_data['Cons'].get_node_data('Pris')
        
        if not node:
            return
            
        count = int(len(node['data']) / 208)
        reader = MeshReader(node['data'])
                
        for _ in range(count):
            part = RevNode()
            
            part.parent_name = reader.get_string(64)
            part.child_name = reader.get_string(64)
            
            self._read_origin(part, reader)
            self._read_offset(part, reader)
            self._read_rotation_matrix(part, reader)
            
            part.axis_rot_x = reader.get_float()
            part.axis_rot_y = reader.get_float()
            part.axis_rot_z = reader.get_float()
            part.min = reader.get_float()
            part.max = reader.get_float()
            
            self.pris_data[part.child_name] = part
            
    def _read_origin(self, part, reader):
        part.origin_x = reader.get_float()
        part.origin_y = reader.get_float()
        part.origin_z = reader.get_float()
        
    def _read_offset(self, part, reader):
        part.offset_x = reader.get_float()
        part.offset_y = reader.get_float()
        part.offset_z = reader.get_float()
    
    def _read_rotation_matrix(self, part, reader):        
        part.rot_mat_xx = reader.get_float()
        part.rot_mat_xy = reader.get_float()
        part.rot_mat_xz = reader.get_float()
        
        part.rot_mat_yx = reader.get_float()
        part.rot_mat_yy = reader.get_float()
        part.rot_mat_yz = reader.get_float()
        
        part.rot_mat_zx = reader.get_float()
        part.rot_mat_zy = reader.get_float()
        part.rot_mat_zz = reader.get_float()
        
    @staticmethod
    def _unpack_name(data):
        data = data.decode('utf-8')
        str = ''
        for char in data:
            if char == '\x00':
                break
            str += char
        return str