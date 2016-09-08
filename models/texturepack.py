from io import BytesIO
from PIL import Image

from .mesh import Texture
from .crc import crc

class TexturePack(object):
    def __init__(self, material_ids, txms, parent):
        self.material_ids = material_ids
        self.txms = txms
        
        self._parent = parent
        
        self.parsed_textures = {}        
        self._load_images()
    
    def get_textures(self):
        return self.parsed_textures
        
    def get_texture_by_material_id(self, material_id):
        return self.parsed_textures[material_id]
    
    def _load_images(self):
        for txm in self.txms:
            mat_lib = txm.find_nodes_with_name_in_path('\\material library')
            
            matches = self._search_for_items(mat_lib)
            
            for match in matches:
                self._load_image(txm, match)
                
    def _load_image(self, txm, tex_obj):        
        data = txm.get_node_data('{}\\{}'.format(tex_obj['name'], 'MIPS'))
        inversion = True
        if data is None:
            data = txm.get_node_data('{}\\{}'.format(tex_obj['name'], 'MIP0'))
            inversion = False
        
        if data is None:
            print('loading of {} NOK (no data)'.format(tex_obj['crc']))
            return
            
        buffer = BytesIO(data['data'])
        
        try:
            with Image.open(buffer) as im:
                texture = Texture()
                
                texture.ix = im.size[0]
                texture.iy = im.size[1]
                
                try:
                    texture.rgb_matrix = im.tobytes("raw", "RGBA", 0, -1)
                except SystemError:     
                    im.putalpha(255) 
                    texture.rgb_matrix = im.tobytes("raw", "RGBA", 0, -1)
                    
                texture.inversion = inversion
                        
                    
                self.parsed_textures[tex_obj['crc']] = texture
                print('loading of {} OK'.format(tex_obj['crc']))
        except Exception as ex:
             self._parent.status((
                'unable to load texture {}. probably an '
                'unsupported DDS format. sorry'
            ).format(tex_obj['name']))
    
    def _search_for_items(self, mat_lib):
        matches = []
        
        for mat_node in mat_lib:
            mat_crc = crc(mat_node['name'])
            if mat_crc in self.material_ids:
                match_img_name = mat_node.get_node_data('Dt_name')
                                
                if match_img_name:
                    matches.append({
                        'crc': mat_crc, 
                        'name': self._unpack_name(match_img_name['data']),
                    })
                    
        return matches
    
    @staticmethod
    def _unpack_name(data):
        data = data.decode('utf-8')
        str = ''
        for char in data:
            if char == '\x00':
                break
            str += char
        return str