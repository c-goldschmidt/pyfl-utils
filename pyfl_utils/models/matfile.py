import os
import struct
import logging
from collections import defaultdict

from ..utf import UTFFile
from ..imgconvert import to_tga

_logger = logging.getLogger(__name__)


def to_fl_filename(filename):
    split = filename.split('.')
    split[-1] = 'tga'

    return '.'.join(split)


class MatLibEntry(object):

    def __init__(self):
        self.name = None

        self.dc = None
        self.oc = None

        self.dt_name = None
        self.dt_flags = None

        self.et_name = None
        self.et_flags = None

        self.bt_name = None
        self.bt_flags = None

    @property
    def type(self):
        mat_type = b'DcDt'

        if self.et_name:
            mat_type += b'Et'

        if self.bt_name:
            mat_type += b'Bt'

        if self.oc and self._is_valid_float_array(self.oc, 2):
            mat_type += b'OcOt'

        return mat_type + b'\x00'

    @staticmethod
    def _is_valid_float_array(arr, num_cmps):
        try:
            assert isinstance(arr, list), 'not an array'
            assert len(arr) == num_cmps, f'expected {num_cmps} components, got {len(arr)}'

            for val in arr:
                assert 0.0 <= val <= 1.0, '{val} not between 0 and 1'

        except AssertionError as e:
            _logger.error(f'float array invalid: {e}')
            return False
        return True

    def add_to_utf(self, utf: UTFFile):
        base_path = f'\\material library\\{self.name}'

        if self.dc and self._is_valid_float_array(self.dc, 4):
            _logger.debug(f'adding {self.name} diffuse color (Dc)')
            utf.add_node(f'{base_path}\\Dc', data=struct.pack('ffff', *self.dc))

        if self.oc and self._is_valid_float_array(self.oc, 2):
            _logger.debug(f'adding {self.name} opacity (Oc)')
            utf.add_node(f'{base_path}\\Oc', data=struct.pack('ff', *self.oc))

        if self.dt_name:
            _logger.debug(f'adding {self.name} diffuse texture (Dt_name / Dt_flags)')
            utf.add_node(f'{base_path}\\Dt_name', data=self.dt_name.encode('UTF-8') + b'\x00')
            utf.add_node(f'{base_path}\\Dt_flags', data=self.dt_flags)

        if self.et_name:
            _logger.debug(f'adding {self.name} emissive texture (Et_name / Et_flags)')
            utf.add_node(f'{base_path}\\Et_name', data=self.et_name.encode('UTF-8') + b'\x00')
            utf.add_node(f'{base_path}\\Et_flags', data=self.et_flags)

        if self.bt_name:
            _logger.debug(f'adding {self.name} bump texture (Bt_name / Bt_flags)')
            utf.add_node(f'{base_path}\\Bt_name', data=self.bt_name.encode('UTF-8') + b'\x00')
            utf.add_node(f'{base_path}\\Bt_flags', data=self.bt_flags)

        _logger.debug(f'adding {self.name} Type as {self.type}')
        utf.add_node(f'{base_path}\\Type', data=self.type)


class TexLibEntry(object):
        def __init__(self, key_name, filename):
            self.key_name = key_name
            self.filename = filename

        def add_to_utf(self, utf: UTFFile):
            ending = os.path.basename(self.filename).split('.')[-1].lower()

            # note: not supporting multiple LODs yet (dds has that builtin)
            node_name = 'MIPS' if ending == 'dds' else 'MIP0'

            if ending not in ['dds', 'tga']:
                to_tga(self.filename)
                self.filename = to_fl_filename(self.filename)

            utf.add_node(f'\\texture library\\{self.key_name}\\{node_name}', file_path=self.filename)


class MATFile(object):

    def __init__(self):
        self._mat_lib = defaultdict(MatLibEntry)
        self._tex_lib = {}

    def save(self, filename):
        file = UTFFile()

        for entry in self._mat_lib.values():
            entry.add_to_utf(file)

        for entry in self._tex_lib.values():
            entry.add_to_utf(file)

        file.save(filename)

    def _set_img(self, key, filename, mat_type):
        base_name = os.path.basename(to_fl_filename(filename))
        key = key or base_name

        self._mat_lib[key].name = key
        setattr(self._mat_lib[key], f'{mat_type}_name', base_name)
        setattr(self._mat_lib[key], f'{mat_type}_flags', struct.pack('ii', 64, 0))

        self._tex_lib[base_name] = TexLibEntry(base_name, filename)
        return key

    def set_base_image(self, filename, key=None):
        return self._set_img(key, filename, 'dt')

    def set_emissive(self, filename, key):
        return self._set_img(key, filename, 'et')

    def set_bump(self, filename, key):
        return self._set_img(key, filename, 'bt')

    def set_additional_info(self, key, diffuse_color=None, opacity=None):
        self._mat_lib[key].name = key
        if diffuse_color:
            self._mat_lib[key].dc = diffuse_color

        if opacity:
            self._mat_lib[key].oc = opacity
