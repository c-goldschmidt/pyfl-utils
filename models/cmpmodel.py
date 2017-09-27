import numpy as np
from collections import defaultdict

from ..utf import UTFFile
from .vmeshref import VMeshRef
from .vmeshdata import VMeshData
from .component import Component
from .texturepack import TexturePack


class CMPModel(object):
    
    def __init__(self, utf, parent, textures=None):
        if not isinstance(utf, UTFFile):
            raise ValueError('utf must be UTFFile!')
            
        self.utf = utf
        
        self._parent = parent
        self.refs = defaultdict(list)
        self.data = {}
        self.lod_levels = {}
        self.components = Component(utf)
        self.material_ids = []
                
        self.prepared_vertices = defaultdict(list)
        self.prepared_normals = defaultdict(list)
        self.materials_per_mesh = defaultdict(list)
        self.prepared_uvs = defaultdict(list)
        
        self._parse_components()
        self._prepare_values()
        
        # remove multiples
        self.material_ids = list(set(self.material_ids))
        self.textures = None
        if textures:
            self.textures = TexturePack(self.material_ids, textures, self._parent)
        
    def get_lod_levels(self):
        return sorted(list(set(self.lod_levels.values())))
        
    def get_vertices(self, lod_level):
        return self.prepared_vertices[lod_level]
            
    def get_normals(self, lod_level):
        return self.prepared_normals[lod_level]    
        
    def get_uvs(self, lod_level):
        return self.prepared_uvs[lod_level]
    
    def get_materials(self, lod_level):
        return self.materials_per_mesh[lod_level]
        
    def get_textures(self):
        if self.textures:
            return self.textures.get_textures()
        return {}
        
    def update_textures(self, new_textures):
        if len(new_textures) == 0:
            self.textures = None
        else:
            self.textures = TexturePack(self.material_ids, new_textures, self._parent)
        
    def _prepare_values(self):
        self.mesh_index = defaultdict(list)
        for ref_name in self.refs:
            center, has_data = self.components.get_offset(ref_name)
            rota = self.components.get_rotation(ref_name)
            
            for mesh_ref in self.refs[ref_name]:
                
                mesh_center = self._get_mesh_center(
                    center, 
                    mesh_ref,
                    has_data
                )
                
                start = mesh_ref.start_mesh
                end = start + mesh_ref.num_meshes
                offset = mesh_ref.start_vertex            
                crc = mesh_ref.lib_id
                
                if crc not in self.data:
                    self._parent.status('critical: mesh crc {} not found'.format(crc))
                    return
                
                self._load_mesh_values(crc, start, end, mesh_center, rota, offset)

    @staticmethod
    def _get_mesh_center(base_center, mesh_ref, has_data):
        if has_data:
            return {
                'x': base_center['x'],
                'y': base_center['y'],
                'z': base_center['z'],
            }
        else:
            return {
                'x': mesh_ref.center_x,
                'y': mesh_ref.center_y,
                'z': mesh_ref.center_z,
            }
        
    def _load_mesh_values(self, crc, mesh_start, mesh_end, center, rota, vertex_offset): 
        meshes = self.data[crc].meshes
        triangles = self.data[crc].triangles
        vertices = self.data[crc].vertices
        lod_level = self.lod_levels[crc]
        
        if lod_level not in self.mesh_index:
            self.mesh_index[lod_level] = 0
            
        for mesh_idx in range(mesh_start, mesh_end):
            mesh = meshes[mesh_idx]
                        
            start = mesh.triangle_start
            end = mesh.triangle_start + int(mesh.num_ref_vertices / 3)            
            offset = mesh.start_vertex + vertex_offset

            self.prepared_vertices[lod_level].append([])
            self.prepared_normals[lod_level].append([])
            self.prepared_uvs[lod_level].append([])
            self.materials_per_mesh[lod_level].append(mesh.material_id) 
            
            for idx in range(start, end):
                triangle = triangles[idx]
                
                try: 
                    self._load_triangle_data(lod_level, vertices, triangle, center, rota, offset)
                except:
                    self._parent.status('error loading model...')
                    raise
            
            self.mesh_index[lod_level] += 1
            
    @staticmethod
    def _chk_append(idx, arr):
        if len(arr) < idx:
            arr.append([])
    
    def _load_triangle_data(self, lod_level, vertices, triangle, center, rota, offset):
        vertex_1 = vertices[triangle.vertex_1 + offset]                
        vertex_2 = vertices[triangle.vertex_2 + offset]                
        vertex_3 = vertices[triangle.vertex_3 + offset]
        
        mesh_idx = self.mesh_index[lod_level]
        
        self.prepared_vertices[lod_level][mesh_idx] += self._vertices_to_array(
            vertex_1, 
            vertex_2,
            vertex_3,
            center, 
            rota
        )        
        self.prepared_normals[lod_level][mesh_idx] += self._normals_to_array(
            vertex_1, 
            vertex_2,
            vertex_3,
            rota
        )
        self.prepared_uvs[lod_level][mesh_idx] += self._uvs_to_array(
            vertex_1, 
            vertex_2,
            vertex_3,
        )

    def _vertices_to_array(self, vertex_1, vertex_2, vertex_3, center, rota):
        vec = np.matrix([
            [vertex_1.x, vertex_1.y, vertex_1.z],
            [vertex_2.x, vertex_2.y, vertex_2.z],
            [vertex_3.x, vertex_3.y, vertex_3.z],
        ])
        
        out = np.matmul(vec, rota).tolist()  
        out = self._apply_offset_to_matrix(out, center)
        
        return out

    def _parse_components(self):
        mesh_data = self.utf.find_nodes_with_name_in_path('\\VMeshLibrary')        
        for mesh in mesh_data:            
            data = mesh.get_node_data('VMeshData')['data']
            new_node = VMeshData(data, mesh['name'])   
            
            self.material_ids += new_node.material_ids
            self.data[new_node.crc] = new_node
            
        mesh_refs = self.utf.get_node_data('VMeshRef', True)        
        for ref in mesh_refs:
            ref_path = ref['path'].split('\\')  
            
            new_ref = VMeshRef(ref['data'])
            
            self.refs[ref_path[1]].append(new_ref)
            self.lod_levels[new_ref.lib_id] = ref_path[-3]

    @staticmethod
    def _print_obj(obj):
        print('=============')
        print('\n'.join("%s: %s" % item for item in vars(obj).items()))

    @staticmethod
    def _apply_offset_to_matrix(out, center):
        out[0][0] += center['x']
        out[0][1] += center['y']
        out[0][2] += center['z']

        out[1][0] += center['x']
        out[1][1] += center['y']
        out[1][2] += center['z']

        out[2][0] += center['x']
        out[2][1] += center['y']
        out[2][2] += center['z']

        return out[0] + out[1] + out[2]

    @staticmethod
    def _normals_to_array(vertex_1, vertex_2, vertex_3, rota):
        vec = np.matrix([
            [vertex_1.normal_x, vertex_1.normal_y, vertex_1.normal_z],
            [vertex_2.normal_x, vertex_2.normal_y, vertex_2.normal_z],
            [vertex_3.normal_x, vertex_3.normal_y, vertex_3.normal_z],
        ])

        out = np.matmul(vec, rota).tolist()
        return out

    @staticmethod
    def _uvs_to_array(vertex_1, vertex_2, vertex_3):
        return [
            vertex_1.s, vertex_1.t,
            vertex_2.s, vertex_2.t,
            vertex_3.s, vertex_3.t,
        ]