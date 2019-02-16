import os
import struct
import logging

_logger = logging.getLogger(__name__)


class UTFFile(object):
    def __init__(self, utf_file=None):
        self._file = os.path.abspath(utf_file) if utf_file else None
        
        if utf_file and os.path.isfile(self._file):
            self._load_file()
        else:
            self._root = UTFTreeRoot()
                
    def _load_raw(self):
        fi = open(self._file, 'rb')
        raw_data = fi.read()
        fi.close()
                
        if raw_data[0:4] != b'UTF ':
            raise Exception('not a valid utf file!')
            
        return raw_data
        
    def _load_file(self):
        raw_data = self._load_raw()
        self._root = UTFTreeRoot(raw_data)
        
    def print_tree(self):
        self._root.print_tree()
        
    def save_data_to_file(self, node_name, filename='', multiple=False):
        found = self._root.save_data_to_file(node_name, filename, multiple)
        
        if not found and not multiple:
            _logger.warning(f'node "{node_name}" not found')
            
    def get_node_data(self, node_name, multiple=False):
        found = self._root.get_node_data(node_name, multiple)
        
        if not found and not multiple:
            _logger.warning(f'node "{node_name}" not found')
        else:
            return found
            
    def update_node_data(self, node_name, filename, create=False):
        found = self._root.update_node_data(node_name, filename)
        
        if not found and create:
            self.add_node(node_name, filename)
            
    def rename_node(self, old_name, new_name):
        old_name_parts = old_name.split('\\')[1:]
        new_name_parts = new_name.split('\\')[1:]
        root_node = self._root._get_root_node()
        
        return self._rename_node(old_name_parts, new_name_parts, root_node)
        
    def _rename_node(self, old_name_parts, new_name_parts, node):
        assert len(old_name_parts) == len(new_name_parts)
        
        current_search = old_name_parts[0]
        current_replace = new_name_parts[0]
                
        ret = False
        for child in node.get_children():
            if child['name'] == current_search:
                child['name'] = current_replace
                
                if len(old_name_parts) > 1:
                    ret = self._rename_node(old_name_parts[1:], new_name_parts[1:], child)
                else: ret = True
                break
        return ret
        
    def delete_node(self, node_name):
        return self._root.delete_node(node_name)
            
    def save(self, filename=False):
        if not filename:
            filename = self._file

        self._root._write_to_file(filename)

    def add_node(self, node_path, file_path=None, data=None):
        path_parts = node_path.split('\\')[1:]
        root_node = self._root._get_root_node()
        first_parent, remaining_path = self._find_node_matching_path(path_parts, root_node)

        if file_path:
            with open(file_path, 'rb') as file:
                data = file.read()

        self._create_nodes(remaining_path, first_parent, data)
        
        # self.print_tree()
        
    def _find_node_matching_path(self, path_parts, node):
        current_search = path_parts[0]
        ret = (node, path_parts)
        for child in node.get_children():
            if child['name'] == current_search:
                ret = self._find_node_matching_path(path_parts[1:], child)
                break
        return ret
        
    def find_nodes_with_name_in_path(self, search_path, node=None, ret=None):
        if ret is None:
            ret = []
        if not node:
            node = self._root._get_root_node()
                
        for child in node.get_children():
            #print child['path']
            if search_path in child['path']:
                ret += child.get_children()
            else:
                self.find_nodes_with_name_in_path(search_path, child, ret)
                
        return ret
        
    def _create_nodes(self, node_names, node_append, data):
        for i, name in enumerate(node_names):
            _logger.debug('creating node {} as child of {}'.format(name, node_append['name']))
            node = UTFTreeNode(
                empty=True,
            )
            
            node['name'] = name
            
            if i == len(node_names) - 1:
                node['node_type'] = 'leaf'
                node['data'] = data
            else:
                node['node_type'] = 'intermediate'
                
            node_append.add_child(node)
            node_append = node      

                
class UTFTreeNode(object):
    
    def __init__(self, parent=None, offset=0, root_node=None, path='', empty=False):
        self._offset = offset
        self._type = type
        self._is_leaf = True
        self._data = {}
        self._children = []
        self._parent = parent
        self._root = root_node
        self._path = path
        
        if empty:
            self._init_empty()
        else:
            self._load()
            
    def _init_empty(self):
        self['peer_offset'] = 0
        self['name_offset'] = 0
        self['flags'] = 0
        self['_null_'] = 0
        self['data_block_offset'] = 0
        self['allocated_size'] = 0
        self['size'] = 0
        self['size2'] = 0
        self['timestamp_0'] = 0
        self['timestamp_1'] = 0
        self['timestamp_2'] = 0
        
        if self._path == '__ROOT__':
            self['name'] = '\\'
            self['path'] = ''
            self['node_type'] = 'intermediate'
        else:
            self['name'] = ''
            self['path'] = self._path
                    
    def _load(self):
        pos = self._offset
        
        self['peer_offset'], pos = self._get_int(pos)  # next (sibling) node
        self['name_offset'], pos = self._get_int(pos)
        self['flags'], pos = self._get_int(pos)
        
        self['_null_'], pos = self._get_int(pos)  # unknown, ask schmacki
        
        self['data_block_offset'], pos = self._get_int(pos)  # OR child node offset 
        self['allocated_size'], pos = self._get_int(pos)     # leaf only
        self['size'], pos = self._get_int(pos)               # leaf only
        self['size2'], pos = self._get_int(pos)              # leaf only
        
        # more unknowns
        self['timestamp_0'], pos = self._get_int(pos)
        self['timestamp_1'], pos = self._get_int(pos)
        self['timestamp_2'], pos = self._get_int(pos)
        
        self['name'] = self._root._load_name(self['name_offset'])
        self['path'] = self._concat_path()
        
        if self._parent:
            self._parent.add_child(self)
            
        if self['peer_offset'] > 0:
            UTFTreeNode(
                self._parent,
                self._root['node_block_offset'] + self['peer_offset'],
                self._root,
                self._path
            )
            
        if self['flags'] == 16 and self['data_block_offset'] > 0:
            self['node_type'] = 'intermediate'
            UTFTreeNode(
                self, 
                self._root['node_block_offset'] + self['data_block_offset'], 
                self._root,
                self['path']
            )            
        else:  # if self['flags'] == 128:
            self['node_type'] = 'leaf'
            if self['size'] != self['size2']:
                _logger.warning('This might be compressed !?')
                
            self['data'] = self._root._load_data(
                self['data_block_offset'], 
                self['size'],
            )
        # elif self['flags'] not in [16, 128]:
        #    print('unexpected node flag: {}'.format(self['flags']))
            
    def _get_int(self, read_position):
        return self._root._get_int(read_position)
            
    def save_data_to_file(self, node_name, filename='', multiple_path=False):
        if self['path'].endswith(node_name):
            # print self['path']
            if 'data' in self._data:                
                if multiple_path:
                    filename = multiple_path + self['path'].replace('\\', '_') + filename           
                
                fi = open(filename, 'wb')
                fi.write(self['data'])
                fi.close()
                
                return not multiple_path
            else:
                _logger.error('node does not contain data')
                return True
        else:
            found = False
            for child in self._children:
                found = child.save_data_to_file(node_name, filename, multiple_path)
                if found:
                    break
            return found
            
    def get_node_data(self, node_name, multiple=False):    
        if self['path'].endswith(node_name):
            if 'data' in self._data: 
                if multiple:
                    return [self]
                else:
                    return self
            else:
                _logger.error('node does not contain data')
                return False
        else:
            found = None
            ret = [] if multiple else None
            for child in self._children:
                found = child.get_node_data(node_name, multiple)
                if found:
                    if multiple:
                        ret += found
                    else:
                        ret = found
                        break;
                        
            return ret
            
    def update_node_data(self, node_name, filename=None, data=None):
        if not filename and not data:
            raise Exception('either filename or binary data is needed')

        if self['path'].endswith(node_name):
            if self['flags'] == 128:
                if filename:
                    with open(filename, 'rb') as file:
                        data = file.read()

                if not isinstance(data, bytes):
                    _logger.error('data has to be in binary format!')

                self['data'] = data
            else:
                _logger.error('node is not a leaf!')
                
            return True
        else:
            found = False
            for child in self._children:
                found = child.update_node_data(node_name, filename)
                if found:
                    break
            return found
            
    def delete_node(self, node_name):
        if self['path'].endswith(node_name):
            _logger.debug('found node "{}".'.format(node_name))
            return self
        else:
            found = False
            for child in self._children:
                found = child.delete_node(node_name)
                if found:
                    break
            
            if isinstance(found, UTFTreeNode):
                self._children.remove(found)
                found = True
            
            return found
                        
    def print_tree(self, depth=0):
        print('{}{} ({})'.format(
            ('-' * depth),
            self['name'],
            self._concat_path(),
        ))
        for child in self._children:
            child.print_tree(depth + 1)
                    
    def add_child(self, node):
        self._children.append(node)
        
    def _concat_path(self):
        if self._path != '' and self._path != '\\':
            return self._path + '\\' + self['name']
        return self._path + self['name']
                
    def get_children(self):
        return self._children
    
    # iterator & access
    def __delitem__(self, key):
        del self._data[key]

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        if key == 'node_type':
            self['flags'] = 128 if value == 'leaf' else 16
        self._data[key] = value

    def __iter__(self):
        return self._data.__iter__()


class UTFTreeRoot(UTFTreeNode):
    def __init__(self, raw_data=None):
        self._raw_len = 0

        if raw_data:
            self._raw = bytes(raw_data)
            self._raw_len = len(self._raw)
            super(UTFTreeRoot, self).__init__(empty=False)
        else:
            super(UTFTreeRoot, self).__init__(empty=True)
            self._actual_root_node = UTFTreeNode(
                self, 
                56,
                self,
                '__ROOT__',
                True
            )
            self.add_child(self._actual_root_node)
        
        self['name'] = 'root'
        self['path'] = ''

    def _load(self):
        pos = self._offset
        
        self['signature'], pos = self._get_int(pos)
        self['version'], pos = self._get_int(pos)
        
        # node chunk
        self['node_block_offset'], pos = self._get_int(pos)
        self['node_size'], pos = self._get_int(pos)
                
        self['unknown'], pos = self._get_int(pos)  # unknown, ask schmacki
        
        # header
        self['header_size'], pos = self._get_int(pos)
        
        # string block
        self['string_block_offset'], pos = self._get_int(pos)
        self['string_block_alloc'], pos = self._get_int(pos)  # unknown, ask schmacki
        self['string_block_size'], pos = self._get_int(pos)     
        
        # data block
        self['data_block_offset'], pos = self._get_int(pos)
        
        # unknown, ask schmacki
        self['unknown2'], pos = self._get_int(pos)            
        
        # whatever date information might be in there...
        self['timestamp_0'], pos = self._get_int(pos)
        self['timestamp_1'], pos = self._get_int(pos)
        self['timestamp_2'], pos = self._get_int(pos)       
        
        self['path'] = ''
        
        self._actual_root_node = UTFTreeNode(
            self, 
            self['node_block_offset'],
            self,
        )       
         
    def _load_data(self, data_offset, data_size):
        start = data_offset + self['data_block_offset']
        end = start + data_size
        return self._raw[start:end]
    
    def _get_int(self, read_position):
        data = struct.unpack('I', self._raw[read_position:read_position+4])
        return data[0], read_position + 4
    
    def _load_name(self, name_offset):
        offset = self['string_block_offset'] + name_offset
        
        char = 'x'
        string = ''                
        while char is not None and offset < self._raw_len:
            char = chr(self._raw[offset])
            if char != '\x00':
                offset += 1
                string += char
            else:
                char = None
                
        return string
        
    def _get_root_node(self):
        return self._actual_root_node
        
    def _write_to_file(self, filename):
        writer = UTFWriter(self, filename)
        writer.save()


class UTFWriter(object):
    def __init__(self, tree, filename):
        self._tree = tree
        self._filename = filename
        
        self._name_offsets = {}
        
        self._node_block = b''
        self._string_block = b''
        self._data_block = b''
        
        self._write_nodes = []
        self._node_block_length = 0     
        
    def save(self): 
        self._prepare_nodes(self._tree)
        
        for node in self._write_nodes:
            self._node_block += self._pack_node(node)
        
        self._tree['signature'] = 541480021     # fixed 
        self._tree['version'] = 257             # fixed 
        self._tree['header_size'] = 44          # fixed 
        self._tree['node_block_offset'] = 56    # fixed
        
        self._tree['timestamp_0'] = 0
        self._tree['timestamp_1'] = 0
        self._tree['timestamp_2'] = 0
        self._tree['unknown'] = 0
        self._tree['unknown2'] = 0
        
        self._tree['node_size'] = len(self._node_block)
        
        self._tree['string_block_offset'] = self._tree['node_block_offset'] + self._tree['node_size']
        self._tree['string_block_size'] = len(self._string_block) + 1
        self._tree['string_block_alloc'] = (self._tree['string_block_size'] + 7) & ~7
        self._tree['data_block_offset'] = self._tree['string_block_offset'] + self._tree['string_block_alloc']

        self._raw = self._pack_header(self._tree)
        self._raw += self._node_block
        self._raw += self._string_block
        self._raw += b'\x00'
        
        for i in range(self._tree['string_block_size'], self._tree['string_block_alloc']):
            self._raw += b'\x00'
        
        self._raw += self._data_block
                        
        with open(self._filename, 'wb') as file:
            file.write(self._raw)
        
    def _add_node(self, node):
        node['name_offset'] = self._pack_string(node['name'])
        
        if node['node_type'] == 'leaf':
            node['data_block_offset'] = len(self._data_block)
                                    
            node['size'] = len(node['data'])
            node['size2'] = node['size']
            node['allocated_size'] = (node['size'] + 3) & ~ 3

            self._data_block += node['data']
            
            for i in range(node['size'], node['allocated_size']):
                self._data_block += b'\x00'
        else:
            node['size'] = 0
            node['size2'] = 0
            node['allocated_size'] = 0
                        
    def _prepare_nodes(self, current_node):
        children = current_node.get_children()
                
        prev_node = None
        for node in children:
            node['peer_offset'] = 0
            node_offset = self._node_block_length
            self._node_block_length += 4 * 11
            self._write_nodes.append(node)
                        
            if prev_node:
                prev_node['peer_offset'] = node_offset
            elif current_node['name'] != 'root':
                # no previous: first child node
                current_node['data_block_offset'] = node_offset
            
            self._add_node(node)    
            prev_node = node    
            
        for node in children:
            if len(node.get_children()) > 0:
                self._prepare_nodes(node)       
            
    def _pack_string(self, string):
        name = (string if isinstance(string, bytes) else string.encode('UTF-8')) + b'\x00'

        if name in self._name_offsets:
            ret = self._name_offsets[name]
        else:
            ret = len(self._string_block)
            self._string_block += name
            self._name_offsets[name] = ret

        return ret
                
    @staticmethod
    def _pack_node(node):
        return struct.pack(
            'I' * 11,
            node['peer_offset'],
            node['name_offset'],
            node['flags'],
            node['_null_'],
            node['data_block_offset'],
            node['allocated_size'],
            node['size'],
            node['size2'],
            node['timestamp_0'],
            node['timestamp_1'],
            node['timestamp_2'],
        )
    
    @staticmethod
    def _pack_header(node):
        return struct.pack(
            'I' * 14,
            node['signature'],
            node['version'],
            node['node_block_offset'],
            node['node_size'],
            node['unknown'],
            node['header_size'],
            node['string_block_offset'],
            node['string_block_alloc'],
            node['string_block_size'],
            node['data_block_offset'],
            node['unknown2'],
            node['timestamp_0'],
            node['timestamp_1'],
            node['timestamp_2']
        )
