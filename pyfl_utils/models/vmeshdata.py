import logging

from ..timer import Timer
from .mesh import (
    MeshReader,
    MeshHeader,
    MeshTriangle,
    MeshVertex,
    MeshConstants,
    MeshWriter,
)
from .crc import crc

_logger = logging.getLogger(__name__)


class VMeshLimitError(ValueError):
    pass


class VMeshData(MeshConstants):

    def __init__(self, raw_data=None, mesh_name=None):
        self.raw_data = None
        self.crc = None
        self._mesh_name = None

        self.meshes = []
        self.triangles = []
        self.vertices = []
        self.material_ids = []

        self.mesh_type = 0x001
        self.surface_type = 0x004
        self.vertex_format = None
        self.num_meshes = 0
        self.num_vertices = 0
        self.num_ref_vertices = 0

        if mesh_name:
            self.mesh_name = mesh_name

        if raw_data:
            self.raw_data = raw_data
            self._parse()

    @property
    def mesh_name(self):
        return self._mesh_name

    @mesh_name.setter
    def mesh_name(self, name):
        self._mesh_name = name
        self.crc = crc(name)

    def to_raw_data(self):
        writer = MeshWriter()
        _logger.debug(f'num_vertices: {self.num_vertices}')

        timer = Timer(_logger.debug)
        self._write_info(writer)
        timer.step('_write_info')
        self._write_mesh_headers(writer)
        timer.step('_write_mesh_headers')
        self._write_triangles(writer)
        timer.step('_write_triangles')
        self._write_vertices(writer)
        timer.step('_write_vertices')

        return writer.raw_data

    def merge(self, other):

        if self.num_ref_vertices + len(other.triangles * 3) > 0xffff:
            raise VMeshLimitError

        for vertex in other.vertices:
            self.add_vertex(vertex)

        for triangle in other.triangles:
            self.add_triangle(triangle)

        for mesh in other.meshes:
            self.add_mesh_header(mesh)

    def add_mesh_header(self, mesh_header):
        self.meshes.append(mesh_header)
        self.num_meshes += 1

    def add_triangle(self, triangle):
        if self.num_ref_vertices + 3 > 0xffff:
            raise VMeshLimitError('Too many triangles in this node!')

        self.triangles.append(triangle)
        self.num_ref_vertices += 3     # 3 vertices per triangle

    def add_vertex(self, vertex):
        if vertex.vertex_format not in self.SUPPORTED_TYPES:
            raise ValueError(f'invalid vertex format: {vertex.vertex_format}! (supported: {self.SUPPORTED_TYPES})')

        if not self.vertex_format:
            self.vertex_format = vertex.vertex_format
        elif self.vertex_format != vertex.vertex_format:
            raise ValueError(f'invalid vertex format {vertex.vertex_format} for this library {self.vertex_format}')

        self.vertices.append(vertex)
        self.num_vertices += 1

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

        _logger.debug(f'num_vertices: {self.num_vertices}')

        if self.vertex_format not in self.SUPPORTED_TYPES:
            raise ValueError('invalid vertex format!')

    def _write_info(self, writer):
        _logger.debug(f'ref vertices: {self.num_ref_vertices}')

        writer.set_dword(self.mesh_type)
        writer.set_dword(self.surface_type)
        writer.set_word(self.num_meshes)
        writer.set_word(self.num_ref_vertices)
        writer.set_word(self.vertex_format)
        writer.set_word(self.num_vertices)

    def _parse_mesh_headers(self):    
        start_offset = 0
        for _ in range(self.num_meshes):
            item = MeshHeader()
            
            item.material_id = self._mesh.get_dword()
            item.start_vertex = self._mesh.get_word()
            item.end_vertex = self._mesh.get_word()
            item.num_ref_vertices = self._mesh.get_word()
            item.padding = self._mesh.get_word()

            _logger.debug(f'padding: {item.padding}')
            
            item.triangle_start = start_offset
            start_offset += int(item.num_ref_vertices / 3)
            
            self.material_ids.append(item.material_id)
            self.meshes.append(item)

    def _write_mesh_headers(self, writer):

        for item in self.meshes:
            writer.set_dword(item.material_id)
            writer.set_word(item.start_vertex)
            writer.set_word(item.end_vertex)
            writer.set_word(item.num_ref_vertices)
            writer.set_word(item.padding)

    def _parse_triangles(self):
        num_triangles = int(self.num_ref_vertices / 3)  # 3 vertices per triangle
                
        for _ in range(num_triangles):
            item = MeshTriangle()
            
            item.vertex_1 = self._mesh.get_word()
            item.vertex_2 = self._mesh.get_word()
            item.vertex_3 = self._mesh.get_word()
            
            self.triangles.append(item)

    def _write_triangles(self, writer):

        for item in self.triangles:
            writer.set_word(item.vertex_1)
            writer.set_word(item.vertex_2)
            writer.set_word(item.vertex_3)

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

    def _write_vertices(self, writer):
        for item in self.vertices:

            writer.set_float(item.x)
            writer.set_float(item.y)
            writer.set_float(item.z)

            self._write_normals(item, writer)
            self._write_diffuse(item, writer)
            self._write_tex_1(item, writer)
            self._write_tex_2(item, writer)
            self._write_tex_4(item, writer)
            self._write_tex_5(item, writer)

    def _parse_normals(self, item):
        if item.vertex_format & self.D3DFVF_NORMAL == self.D3DFVF_NORMAL:
            item.normal_x = self._mesh.get_float()
            item.normal_y = self._mesh.get_float()
            item.normal_z = self._mesh.get_float()

    def _write_normals(self, item, writer):
        if item.vertex_format & self.D3DFVF_NORMAL == self.D3DFVF_NORMAL:
            writer.set_float(item.normal_x)
            writer.set_float(item.normal_y)
            writer.set_float(item.normal_z)

    def _parse_diffuse(self, item):
        if item.vertex_format & self.D3DFVF_DIFFUSE == self.D3DFVF_DIFFUSE:
            item.diffuse = self._mesh.get_dword()

    def _write_diffuse(self, item, writer):
        if item.vertex_format & self.D3DFVF_DIFFUSE == self.D3DFVF_DIFFUSE:
            writer.set_dword(item.diffuse)

    def _parse_tex_1(self, item):
        if item.vertex_format & self.D3DFVF_TEX1 == self.D3DFVF_TEX1:
            item.s = self._mesh.get_float()
            item.t = self._mesh.get_float()

    def _write_tex_1(self, item, writer):
        if item.vertex_format & self.D3DFVF_TEX1 == self.D3DFVF_TEX1:
            writer.set_float(item.s)
            writer.set_float(item.t)

    def _parse_tex_2(self, item):
        if item.vertex_format & self.D3DFVF_TEX2 == self.D3DFVF_TEX2:
            item.s = self._mesh.get_float()
            item.t = self._mesh.get_float()
            item.u = self._mesh.get_float()
            item.v = self._mesh.get_float()

    def _write_tex_2(self, item, writer):
        if item.vertex_format & self.D3DFVF_TEX2 == self.D3DFVF_TEX2:
            writer.set_float(item.s)
            writer.set_float(item.t)
            writer.set_float(item.u)
            writer.set_float(item.v)

    def _parse_tex_4(self, item):
        if item.vertex_format & self.D3DFVF_TEX4 == self.D3DFVF_TEX4:
            item.s = self._mesh.get_float()
            item.t = self._mesh.get_float()
            item.tangent_x = self._mesh.get_float()
            item.tangent_y = self._mesh.get_float()
            item.tangent_z = self._mesh.get_float()
            item.binormal_x = self._mesh.get_float()
            item.binormal_y = self._mesh.get_float()
            item.binormal_z = self._mesh.get_float()

    def _write_tex_4(self, item, writer):
        if item.vertex_format & self.D3DFVF_TEX4 == self.D3DFVF_TEX4:
            writer.set_float(item.s)
            writer.set_float(item.t)
            writer.set_float(item.tangent_x)
            writer.set_float(item.tangent_y)
            writer.set_float(item.tangent_z)
            writer.set_float(item.binormal_x)
            writer.set_float(item.binormal_y)
            writer.set_float(item.binormal_z)

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

    def _write_tex_5(self, item, writer):
        if item.vertex_format & self.D3DFVF_TEX5 == self.D3DFVF_TEX5:
            writer.set_float(item.s)
            writer.set_float(item.t)
            writer.set_float(item.u)
            writer.set_float(item.v)
            writer.set_float(item.tangent_x)
            writer.set_float(item.tangent_y)
            writer.set_float(item.tangent_z)
            writer.set_float(item.binormal_x)
            writer.set_float(item.binormal_y)
            writer.set_float(item.binormal_z)
