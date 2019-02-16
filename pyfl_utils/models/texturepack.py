import logging
import struct

from collections import defaultdict
from io import BytesIO
from PIL import Image

from .mesh import Texture
from .crc import crc

_logger = logging.getLogger(__name__)


class TexturePack(object):
    def __init__(self, material_ids, txms):
        self.material_ids = material_ids
        self.txms = txms

        self.parsed_textures = {}
        self.parsed_additions = defaultdict(dict)
        self.parsed_meta = {}
        self._load_images()

    def get_textures(self):
        return self.parsed_textures

    def get_additions(self):
        return self.parsed_additions

    def get_meta(self):
        return self.parsed_meta

    def get_texture_by_material_id(self, material_id):
        return self.parsed_textures[material_id]

    def _load_images(self):
        for txm in self.txms:
            mat_lib = txm.find_nodes_with_name_in_path('\\material library')

            matches = self._search_for_items(mat_lib)

            for match in matches:
                if match['base']:
                    self._load_image(txm, match)
                else:
                    self._load_null_texture(match['crc'])
                if match['light']:
                    self._load_image(txm, match, 'light')
                if match['bump']:
                    self._load_image(txm, match, 'bump')

                self._load_meta(match)

    def _load_meta(self, match):
        if not any(match['meta'].values()):
            return

        self.parsed_meta[match['crc']] = match['meta']

    def _load_null_texture(self, crc):
        texture = Texture()

        texture.ix = 1
        texture.iy = 1
        texture.rgb_matrix = struct.pack('BBBB', 0, 0, 0, 0)
        texture.inversion = False

        self.parsed_textures[crc] = texture

    def _load_image(self, txm, tex_obj, tex_type='base'):
        data = txm.get_node_data('{}\\{}'.format(tex_obj[tex_type], 'MIPS'))
        inversion = True
        if data is None:
            data = txm.get_node_data('{}\\{}'.format(tex_obj[tex_type], 'MIP0'))
            inversion = False

        if data is None or len(data['data']) == 0:
            _logger.error(f'loading of {tex_obj["crc"]} NOK (no data)')
            return

        buffer = BytesIO(data['data'])

        try:
            with Image.open(buffer) as im:
                texture = Texture()

                texture.ix = im.size[0]
                texture.iy = im.size[1]

                try:
                    texture.rgb_matrix = im.tobytes("raw", "RGBA", 0, -1)
                except ValueError:
                    im.putalpha(255)
                    texture.rgb_matrix = im.tobytes("raw", "RGBA", 0, -1)

                texture.inversion = inversion

                if tex_type == 'base':
                    self.parsed_textures[tex_obj['crc']] = texture
                else:
                    self.parsed_additions[tex_obj['crc']][tex_type] = texture
        except Exception as ex:
            _logger.error((
                f'unable to load {tex_type} texture {tex_obj[tex_type]} in "{txm._file}".'
                ' probably an unsupported DDS format. sorry'
            ))
            raise

    def _search_for_items(self, mat_lib):
        matches = []

        for mat_node in mat_lib:
            mat_crc = crc(mat_node['name'])
            if mat_crc in self.material_ids:
                base_texture = mat_node.get_node_data('Dt_name')
                emissive_texture = mat_node.get_node_data('Et_name')
                bump_texture = mat_node.get_node_data('Bt_name')

                diffuse_color = mat_node.get_node_data('Dc')
                opacity = mat_node.get_node_data('Oc')

                matches.append({
                    'crc': mat_crc,
                    'base': self._unpack_name(base_texture['data']) if base_texture else None,
                    'light': self._unpack_name(emissive_texture['data']) if emissive_texture else None,
                    'bump': self._unpack_name(bump_texture['data']) if bump_texture else None,
                    'meta': {
                        'diffuse_color': self._unpack_float_array(diffuse_color['data']) if diffuse_color else None,
                        'opacity': self._unpack_float_array(opacity['data']) if opacity else None,
                    },
                })

        return matches

    @staticmethod
    def _unpack_float_array(data):
        return struct.unpack('f' * int((len(data) / 4)), data)

    @staticmethod
    def _unpack_name(data):
        data = data.decode('utf-8')
        str = ''
        for char in data:
            if char == '\x00':
                break
            str += char
        return str
