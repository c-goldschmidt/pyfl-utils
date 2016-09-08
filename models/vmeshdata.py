from .mesh import (
    MeshReader,
    MeshHeader, 
    MeshTriangle, 
    MeshVertex, 
    MeshConstants, 
)
from .crc import crc

class VMeshData(MeshConstants):

    def __init__(self, raw_data, mesh_name):
        self.raw_data = raw_data
        self.mesh_name = mesh_name
        self.crc = crc(mesh_name)
                
        self.meshes = []
        self.triangles = []
        self.vertices = []
        self.material_ids = []
        
        self._parse()
        
    def _parse(self):
        self._mesh = MeshReader(self.raw_data)
                
        self._parse_info()
        self._parse_mesh_headers()
        self._parse_triangles()
        self._parse_vertices()
            
    def _parse_info(self):        
        self.mesh_type = self._mesh.get_dword()
        self.surface_type = self._mesh.get_dword()
        self.num_meshes = self._mesh.get_word()
        self.num_ref_vertices = self._mesh.get_word()
        self.vertex_format = self._mesh.get_word()
        self.num_vertices = self._mesh.get_word()
        
        if self.vertex_format not in self.SUPPORTED_TYPES:
            raise ValueError('invalid vertex format!')
        
    def _parse_mesh_headers(self):    
        start_offset = 0
        for _ in range(self.num_meshes):
            item = MeshHeader()
            
            item.material_id = self._mesh.get_dword()
            item.start_vertex = self._mesh.get_word()
            item.end_vertex = self._mesh.get_word()
            item.num_ref_vertices = self._mesh.get_word()
            item.padding = self._mesh.get_word()
            
            item.triangle_start = start_offset
            start_offset += int(item.num_ref_vertices / 3)
            
            self.material_ids.append(item.material_id)
            self.meshes.append(item)
            
    def _parse_triangles(self):
        num_triangles = int(self.num_ref_vertices / 3)  # 3 vertices per triangle
                
        for _ in range(num_triangles):
            item = MeshTriangle()
            
            item.vertex_1 = self._mesh.get_word()
            item.vertex_2 = self._mesh.get_word()
            item.vertex_3 = self._mesh.get_word()
            
            self.triangles.append(item)
            
    def _parse_vertices(self):
        
        for _ in range(self.num_vertices):
            item = MeshVertex()
            
            item.vertex_format = self.vertex_format
            item.x = self._mesh.get_float()
            item.y = self._mesh.get_float()
            item.z = self._mesh.get_float()
            
            self._parse_normals(item)
            self._parse_diffuse(item)
            self._parse_tex_1(item)
            self._parse_tex_2(item)
            self._parse_tex_4(item)
            self._parse_tex_5(item)
            
            self.vertices.append(item)            
            
    def _parse_normals(self, item):
        if item.vertex_format & self.D3DFVF_NORMAL == self.D3DFVF_NORMAL:
            item.normal_x = self._mesh.get_float()
            item.normal_y = self._mesh.get_float()
            item.normal_z = self._mesh.get_float()
            
    def _parse_diffuse(self, item):
        if item.vertex_format & self.D3DFVF_DIFFUSE == self.D3DFVF_DIFFUSE:
            item.diffuse = self._mesh.get_dword()
            
    def _parse_tex_1(self, item):
        if item.vertex_format & self.D3DFVF_TEX1 == self.D3DFVF_TEX1:
            item.s = self._mesh.get_float()
            item.t = self._mesh.get_float()
            
            #print('TEX1 s: {}, t: {}'.format(item.s, item.t))
        
    def _parse_tex_2(self, item):
        if item.vertex_format & self.D3DFVF_TEX2 == self.D3DFVF_TEX2:
            item.s = self._mesh.get_float()
            item.t = self._mesh.get_float()
            item.u = self._mesh.get_float()
            item.v = self._mesh.get_float()
            
            #print('TEX2 s: {}, t: {}'.format(item.s, item.t))
                        
    def _parse_tex_4(self, item):
        if item.vertex_format & self.D3DFVF_TEX4 == self.D3DFVF_TEX4:
            item.s = self._get_float()
            item.t = self._get_float()
            item.tangent_x = self._mesh.get_float()
            item.tangent_y = self._mesh.get_float()
            item.tangent_z = self._mesh.get_float()
            item.binormal_x = self._mesh.get_float()
            item.binormal_y = self._mesh.get_float()
            item.binormal_z = self._mesh.get_float()
            
            #print('TEX4 s: {}, t: {}'.format(item.s, item.t))
            
    def _parse_tex_5(self, item):
        if item.vertex_format & self.D3DFVF_TEX5 == self.D3DFVF_TEX5:
            item.s = self._mesh.get_float()
            item.t = self._mesh.get_float()
            item.u = self._mesh.get_float()
            item.v = self._mesh.get_float()
            item.tangent_x = self._mesh.get_float()
            item.tangent_y = self._mesh.get_float()
            item.tangent_z = self._mesh.get_float()
            item.binormal_x = self._mesh.get_float()
            item.binormal_y = self._mesh.get_float()
            item.binormal_z = self._mesh.get_float()
            
            #print('TEX5 s: {}, t: {}'.format(item.s, item.t))
            