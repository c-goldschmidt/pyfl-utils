import codecs
import logging
import os
from .multidict import MultiDict
from .bini import BINI

_logger = logging.getLogger(__name__)


class INIFile(object):
    def __init__(self, filename):
        self._sections = MultiDict()
        self._filename = filename
        
        with open(filename, 'rb') as file:
            try:
                self._raw = file.read()
            except:
                _logger.error('cannot read INI file')
                return

        is_bini = self._parse_bini()        
        if not is_bini:
            self._parse_raw()

        _logger.debug(filename)
        
    def get_path(self):
        return os.path.dirname(self._filename)

    def _is_bini(self):
        encoded = self._raw.decode('UTF-8', errors='replace')
        return encoded.startswith('BINI')

    def _parse_bini(self):
        if self._is_bini():
            bini = BINI(self._raw)
            
            for section in bini.get_sections():
                ini_section = IniSection(section['name'])
                
                for entry in section['entries']:
                    vals = []
                    for value in entry['values']:         
                        vals.append(str(value.value))
                        
                    ini_section.add(entry['name'], ', '.join(vals))
                
                self.add(ini_section)            
            return True
        return False
    
    def _parse_raw(self):
        self._raw = self._raw.decode('UTF-8', errors='replace')
        current_section = None
        for line in self._raw.split('\n'):
            line = line.replace('\n', '')
            line = line.replace('\r', '')
            line = line.strip('\r\n \t')
            
            if line == '' or line.startswith(';'):
                continue
                
            if line.startswith('BINI'):
                _logger.error('this is a bini file!!')
                return
                            
            if line.startswith('['):
                line = line.strip('[]')
                current_section = IniSection(line)
                self._sections[line.lower()] = current_section
            elif not current_section:
                raise Exception('error parsing ini: floating config!')
            else:
                current_section._add_raw(line)
    
    def print_raw(self):
        for section in self.to_list():
            section.print_raw()
            
    def get(self, section_name):
        try:
            return self._sections[section_name.lower()]
        except KeyError:
            return None
        
    def get_by_key(self, key, multiple=True, section_name=None):
        if section_name:
            sections = list(self._sections[section_name.lower()])
        else:
            sections = self.to_list()
            
        ret_list = []
        for section in sections:
            if section._has_key(key):
                if multiple:
                    ret_list.append(section)
                else:
                    return section
        
        if multiple:
            return ret_list
        else:
            return None
                    
    def get_by_kv(self, key, value, multiple=True, section_name=None, case_sensitive=False):
        if section_name:
            sections = list(self._sections[section_name.lower()])
        else:
            sections = self.to_list()
            
        if not case_sensitive:
            value = value.lower()
            
        ret_list = []
        for section in sections:
            sec_value = section.get(key)
            
            if not sec_value:
                continue
            
            if not case_sensitive:
                sec_value = sec_value.lower()
                            
            if sec_value == value:
                if multiple:
                    ret_list.append(section)
                else:
                    return section            
        
        if multiple:
            return ret_list
        else:
            return None
        
    def set(self, section):
        self._sections.set(section.name.lower(), section)
        
    def add(self, section):
        self._sections[section.name.lower()] = section
        
    def rem(self, section):
        if isinstance(section, IniSection):
            # remove by instance
            current = self._sections[section.name.lower()]
            if isinstance(current, list):
                current.remove(section)
            else:
                del self._sections[section.name.lower()]
        else:
            # remove by name
            del self._sections[section.lower()]
    
    def rem_by_kv(self, key, value, case_sensitive=False):
        section = self.get_by_kv(key, value, multiple=False, case_sensitive=case_sensitive)
        
        if section:
            self.rem(section)
    
    def save(self):
        raw = ''
        for section in self.to_list():
            raw += section.to_raw()

        with codecs.open(self._filename, 'w', 'cp1252') as file:
            file.write(raw)
            
    def to_list(self):
        ret_list = []
        
        for key in self._sections:
            value = self._sections[key]
            if isinstance(value, list):
                for section in value:
                    ret_list.append(section)
            else:
                ret_list.append(value)
            
        return ret_list

        
class IniSection(object):
    @staticmethod
    def _strip_comments(string):
        return string.split(';')[0].strip()
        
    def __init__(self, section_name):
        self.name = section_name
        self._options = MultiDict()
        
    def _add_raw(self, line):
        if not line.startswith(';'):
            split = line.split('=')
            
            if len(split) == 1:
                split.append('')
                
            if split[0] != '':
                self._options[split[0].strip()] = self._strip_comments(split[1])
    
    def get(self, key):
        if key in self._options:
            return self._options[key]
        return None
        
    def set(self, key, value):
        self._options.set(key, value)
    
    def add(self, key, value):
        self._options[key] = value
        
    def to_raw(self):
        raw = '[{}]\r\n'.format(self.name)
        
        for key in self._options:
            value = self._options[key]
            if isinstance(value, list):
                for val in value:
                    raw += self._kv_to_raw(key, val)
            else:
                raw += self._kv_to_raw(key, value)
                
        return raw + '\r\n'
        
    def _kv_to_raw(self, key, value, allow_empty=True):
        if value == '' and not allow_empty:
            return '{}\r\n'.format(key)
        else:
            value = str(value).strip()
            if value != '':
                value = ' ' + value
            return '{} ={}\r\n'.format(key, value)
            
    def _has_key(self, key):
        return key in self._options
        
    def print_raw(self):
        print(self.to_raw())
            
    