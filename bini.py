import logging
import struct
from collections import namedtuple, defaultdict

_logger = logging.getLogger(__name__)


class BINI(object):
    HEADER = namedtuple('BiniHeader', ['format', 'version', 'string_table_offset'])
    SECTION = namedtuple('BiniSection', ['stp', 'num_entries'])
    ENTRY = namedtuple('BiniEntry', ['stp', 'num_values'])
    VALUE = namedtuple('BiniValue', ['value_type', 'value'])
        
    def __init__(self, content):
        # try:
        #    content = content.encode('cp1252')
        # except:
        #   pass

        self._raw = content
                
        self._string_table = defaultdict(str)
        self._read_offset = 0
        
        self._sections = []  
        
        self._decode()
    
    def _decode(self):
        self._decode_header()
        self._decode_string_table()
        
        self._decode_sections()        
    
    def _decode_header(self):
        self.header = self.HEADER(
            self._raw[0:4],
            struct.unpack('i', self._raw[4:8])[0],
            struct.unpack('i', self._raw[8:12])[0],
        )
        self._read_offset = 12
        
    def _decode_sections(self):
        while self._read_offset < self.header.string_table_offset:
            section_header = self._decode_section_header()
            
            section_dict = {
                'name': self._string_table[section_header.stp],
                'entries': [],
            }
                        
            for i in range(section_header.num_entries):
                entry_dict = self._decode_entry()
                section_dict['entries'].append(entry_dict)
            
            self._sections.append(section_dict)
            
    def _decode_entry(self):
        section_entry = self._decode_entry_header()
        
        entry_dict = {
            'name': self._string_table[section_entry.stp],
            'values': []
        }
        
        for i in range(section_entry.num_values):
            entry_value = self._decode_value()
            entry_dict['values'].append(entry_value)
                
        return entry_dict
        
    def _decode_section_header(self):
        ro = self._read_offset
    
        section_header = self.SECTION(
            struct.unpack('h', self._raw[ro:ro + 2])[0],
            struct.unpack('h', self._raw[ro + 2:ro + 4])[0],
        )
        
        self._read_offset = ro + 4
        return section_header
        
    def _decode_entry_header(self):
        ro = self._read_offset
        
        entry = self.ENTRY(
            struct.unpack('h', self._raw[ro:ro + 2])[0],
            struct.unpack('b', self._raw[ro + 2: ro + 3])[0],
        )
        
        self._read_offset = ro + 3
        return entry
        
    def _decode_value(self):
        ro = self._read_offset
        self._read_offset = ro + 5
        
        val_type = struct.unpack('b', self._raw[ro:ro + 1])[0]
        
        if val_type == 0x01:
            val_content = struct.unpack('i', self._raw[ro + 1:ro + 5])[0]
        elif val_type == 0x02:
            val_content = struct.unpack('f', self._raw[ro + 1:ro + 5])[0]
        elif val_type == 0x03:
            val_content = struct.unpack('i', self._raw[ro + 1:ro + 5])[0]
            val_content = self._string_table[val_content]            
        else:
            _logger.error('invalid value type {}'.format(val_type))
            return self.VALUE(
                val_type,
                None
            )
        
        val = self.VALUE(
            val_type,
            val_content,
        )
        
        return val
    
    def _decode_string_table(self):
        if not self.header.string_table_offset:
            _logger.error('no string table offset!')
            return
            
        pos = self.header.string_table_offset
        st_offseet = self.header.string_table_offset
        
        current_string = ''
        str_offset = 0
        while pos < len(self._raw):
            if self._raw[pos] == 0:
                # logger.debug('string table offset {}: "{}"'.format(str_offset, current_string))
                self._string_table[str_offset] = current_string
                current_string = ''
                str_offset = (pos - st_offseet) + 1
            else:
                current_string += chr(self._raw[pos])
                
            pos += 1
    
    def get_sections(self):
        return self._sections
