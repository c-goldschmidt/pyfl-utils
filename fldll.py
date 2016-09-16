import logging
import math
import os
import struct

from .constants import *
from .inifile import INIFile
from .stringutils import try_decode

_logger = logging.getLogger(__name__)

class FLDll(object):
    def __init__(self, dll_file, ini_file=None, base_index=None):
        self._pages = {}
        self._infocards = {}
        self._update_infocards = []
        self._max_table = 0
        
        self.dll_file = os.path.abspath(dll_file)
        self._load_dll()
        
        self._dll_base_index = None        
        if ini_file:
            ini_file = INIFile(ini_file)
            
            base = os.path.basename(self.dll_file)
            section = ini_file.get('resources')
            
            if section:
                dlls = section.get('DLL')
                self._dll_base_index = dlls.index(base) + 1
        elif base_index:
            self._dll_base_index = base_index

    @staticmethod
    def _load_string(module, id):
        resource = PWCHAR()
        lp_buffer = ctypes.cast(ctypes.byref(resource), wintypes.LPWSTR)
        nchar = user32.LoadStringW(module, id, lp_buffer, 0)
        return resource[:nchar].encode('utf-8')
        
    def _load_infocard(self, module, id):
        res_handle = FindResource(module, id, 23)
        
        size = SizeofResource(module, res_handle)
        data_handle = LoadResource(module, res_handle)
        
        data = ''
        try:
            ptr = LockResource(data_handle)
            try:
                data = ctypes.string_at(ptr, size)
            except:
                pass
        finally:
            FreeResource(data_handle)
                
        return self._unpack_infocard(data)
        
    def _unpack_infocard(self, data):     
        data_length = (len(data) - 7) / 2       
        try:
            actual_data = data[2:-5].decode('utf-16').encode('utf-8')
        except:
            # for some reason, there's no padding and zero byte on some items
            try:
                actual_data = data[2:].decode('utf-16').encode('utf-8')
            except:                
                _logger.error('can\'t unpack infocard! in {}'.format(self.dll_file))
                actual_data = ''
                
        return actual_data
        
    @staticmethod
    def _serialize_infocard(infocard):  
        s = try_decode(infocard)
        s = s.encode('utf-16')
        s += '\x20\x20\x00'.encode('utf-16')[2:-1]
        
        return s
        
    @staticmethod
    def index_to_id(index, page):
        return index + 16 * (page - 1)
        
    @staticmethod
    def id_to_index(id):
        i = int(math.floor(id/float(16)))
        return i + 1, id % 16
        
    @staticmethod
    def get_dll_id_from_ini_id(ids) :
        if ids is None :
            return None, None
        mx = 65536
        ids = int(ids)
        i = int(math.floor(ids/float(mx)))
        return i, ids % mx
            
    def get_ini_id(self, id):
        if not self._dll_base_index:
            raise Exception('Not initialized with freelancer.ini!')
        else:
            return int(self._dll_base_index * 65536 + id)
                
    def get_by_id(self, ini_id):
        dll_id = int(ini_id) % 65536
                
        if dll_id in self._infocards:
            return self._infocards[dll_id]
        else:
            page, id = self.id_to_index(dll_id)
            
            if page in self._pages:
                return self._pages[page].get_slot(id)
            else:
                return None
            
    def add_string(self, string):
        str_id = self.find_string(string)
        
        if not str_id:
            for page in self._pages.values():
                first_free = page.get_first_free_index()
                if first_free:
                    page.add_string(first_free, string)
                    page.set_update()
                    return self.index_to_id(first_free, page.get_id())
            
            self._max_table += 1
            new_page = StringTable(self._max_table)
            new_page.add_string(0, string)
            page.set_update()
            self._pages[self._max_table] = new_page
            
            return self.index_to_id(0, self._max_table)
        else:
            return str_id
            
    def update_string(self, string, dll_id):
        page, id = self.id_to_index(dll_id)
        try:
            self._pages[page].update_slot(id, string)
        except KeyError:
            _logger.warning('unable to update slot {} of page {}'.format(id, page))
            pass
            
    def delete_string(self, dll_id):
        page, id = self.id_to_index(dll_id)
        try:
            self._pages[page].delete_slot(id)
            return True
        except KeyError:
            _logger.warning('unable to update slot {} of page {}'.format(id, page))
            return False
            
    def find_infocard(self, infocard):
        try:
            infocard_values = list(self._infocards.values())
            ret = self._infocards.keys()[infocard_values.index(infocard)]
        except ValueError:
            ret = False
            
        return ret
            
    def add_infocard(self, infocard):
        new_id = self.find_infocard(infocard)
        update = new_id is not False
                
        if infocard.startswith('<?xml version="1.0" encoding="UTF-16"?>'):
            data = infocard
            update = False
        else:
            data = '<?xml version="1.0" encoding="UTF-16"?><RDL><PUSH/><TEXT>'
            data += infocard
            data += '</TEXT><PARA/><POP/></RDL>'
            
        if not update:
            new_id = self.find_infocard(infocard)
        
        if not new_id:
            update = True
            new_id = self._get_lockable_id()
            
        self._infocards[new_id] = data
        
        if update:
            self._update_infocards.append(new_id)
            
        return new_id
        
    def update_infocard(self, infocard, index):
        if infocard.startswith('<?xml version="1.0" encoding="UTF-16"?>'):
            data = infocard
        else:
            data = '<?xml version="1.0" encoding="UTF-16"?><RDL><PUSH/><TEXT>'
            data += infocard
            data += '</TEXT><PARA/><POP/></RDL>'
    
        self._infocards[index] = data
        self._update_infocards.append(index)
        
    def delete_infocard(self, index):
        self._infocards[index] = ''
        self._update_infocards.append(index)
    
    def _get_lockable_id(self):
        for page in self._pages.values():
            first_free = page.get_first_free_index()
            if first_free:
                page.lock_slot(first_free)
                return self.index_to_id(first_free, page.get_id())
                    
        self._max_table += 1
        new_page = StringTable(self._max_table)
        new_page.lock_slot(0)
        self._pages[self._max_table] = new_page
        return self.index_to_id(0, self._max_table)
                
    def _load_dll(self):
        def callback_string(module_handle, type, table_index, param):
            self._max_table = table_index
            table = StringTable(table_index)
            
            for i in range(0, 16):
                idx =  self.index_to_id(i, table_index)
                try:
                    str = self._load_string(module_handle, idx)
                    table.add_string(i, str)
                except Exception:
                    pass
                    
            self._pages[table_index] = table
                    
            return True

        def callback_infocard(module_handle, type, table_index, param):
            page, index = self.id_to_index(table_index)
            
            if page not in self._pages:
                self._pages[page] = StringTable(page)
                self._max_table = page
            
            self._pages[page].lock_slot(index)
            self._infocards[table_index] = self._load_infocard(module_handle, table_index)
            return True
            
        module = LoadLibrary(
            self.dll_file, 0, 
            LOAD_WITH_ALTERED_SEARCH_PATH | LOAD_LIBRARY_AS_DATAFILE_EXCLUSIVE | LOAD_LIBRARY_AS_IMAGE_RESOURCE,
        )
                        
        if module == 0:
            raise Exception("Can't read resources from file {} (code: {})".format(
                self.dll_file, 
                GetLastError())
            )
                        
        EnumResourceNames(module, 6, EnumResourceNameCallback(callback_string), None)
        EnumResourceNames(module, 23, EnumResourceNameCallback(callback_infocard), None)
        
        FreeLibrary(module)
    
    def find_string(self, string):
        for page in self._pages.values():
            idx = page.contains_string(string)
            if idx:
                return self.index_to_id(idx, page.get_id())
        return False
    
    def print_all(self):
        print('========= strings =========')
        self.print_strings()
        
        print('========= infocards =========')
        self.print_infocards()      
            
    def print_strings(self):
        for page in self._pages.values():
            page.print_table()
    
    def print_infocards(self):
        for id in self._infocards:
            print(id)
            print(self._infocards[id])
                    
    def save(self):
        update_handle = BeginUpdateResource(self.dll_file.encode('utf-8'), True)
        
        if update_handle == 0:
            _logger.error('error getting handle: {}'.format(GetLastError()))
            return
        
        # update fileinfo section
        version_info = VS_VERSION_INFO()
        print(version_info)
        UpdateResource(update_handle, 16, 1, 0, version_info, len(version_info))
            
        for page in self._pages.values():
            #if page.needs_update():
            _logger.debug('update page {}'.format(page.get_id()))
            data = page.serialize().encode('utf-16')[2:]
            UpdateResource(update_handle, 6, page.get_id(), 1033, data, len(data))
            
        for id in self._infocards:
            if self._infocards[id] == '':
                continue
            _logger.debug('update infocard {}'.format(id))
            data = self._serialize_infocard(self._infocards[id])
            UpdateResource(update_handle, 23, id, 1033, data, len(data))
            
        EndUpdateResource(update_handle, False)
            
class StringTable(object):  
    def __init__(self, id):
        self._slots = {}
        self._free_slots = 15   
        self._id = id
        self._locked_slots = []
        self._needs_update = False
        
        for i in range(0, 16):
            self._slots[i] = ''
            
    def get_id(self):
        return self._id
        
    def get_slot(self, id):
        return self._slots[id]
        
    def update_slot(self, id, string):
        if not self._slots[id]:
            self._free_slots -= 1
            
        self._slots[id] = string
        self.set_update()
        
    def delete_slot(self, index):
        self._slots[index] = ''
        self._free_slots += 1
        self.set_update()
        
    def needs_update(self):
        return self._needs_update
        
    def set_update(self):
        self._needs_update = True
        
    def lock_slot(self, id):
        self._locked_slots.append(id)
        self._free_slots -= 1
        
    def add_string(self, index, string):
        self._slots[index] = string
        self._free_slots -= 1
                
    def get_first_free_index(self):
        if self._free_slots <= 0:
            return
            
        for i in range(0, 16):
            if self._slots[i] == '' and i not in self._locked_slots:
                return i
        
    def contains_string(self, string):
        for key in self._slots:
            if string == self._slots[key]:
                return key
        
    def print_table(self):
        print('--- Page {} ---'.format(self._id))
        for i in self._slots:
            str = self._slots[i]
            if i in self._locked_slots:
                str = '###LOCKED###'
            print('{}: {}'.format(
                FLDll.index_to_id(i, self._id), 
                str,
            ))
        
    def _pack_string(self, string):
        if string == '':
            return '\x00'
        else:
            s = try_decode(string)
            s = s.encode('utf-16')[2:]
            formatted = struct.pack('h', int(len(s) / 2))
            formatted = (formatted + s).decode('utf-16')
            return formatted
    
    def serialize(self):
        return ''.join([self._pack_string(self._slots[slot]) for slot in self._slots])
