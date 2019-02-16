import asyncio
import logging
import struct

from ..timer import Timer
from .component import Component
from ..utf import UTFFile

_logger = logging.getLogger(__name__)


class Part(object):

    def __init__(self, file_name, index, object_name, mesh_ref):
        self.file_name = file_name
        self.index = index
        self.object_name = object_name
        self.mesh_ref = mesh_ref


class CMPWriter(object):
    def __init__(self):
        self.parts = []
        self.libs = []
        self.hardpoints = []
        self.components = Component()
        self.num_components = 0

    @staticmethod
    async def _async_add_node(utf, lib):
        _logger.info(f'save lib => {lib.mesh_name} ({lib.crc})')
        timer = Timer(_logger.debug)
        utf.add_node(f'\\VMeshLibrary\\{lib.mesh_name}\\VMeshData', data=lib.to_raw_data())
        timer.step('save lib done')

    def add_part(self, file_name, index, object_name, mesh_ref):
        self.parts.append(Part(file_name, index, object_name, mesh_ref))
        self.num_components += 1

    def add_lib(self, data):
        self.libs.append(data)

    def save(self):
        utf = UTFFile()

        tasks = []
        for lib in self.libs:
            _logger.debug('add task')
            tasks.append(asyncio.ensure_future(self._async_add_node(utf, lib)))

        _logger.debug('start tasks')
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))

        timer = Timer(_logger.debug)
        self.components.write_component_data(utf)
        timer.step('save libs done')

        timer = Timer(_logger.debug)
        for part in self.parts:
            _logger.debug(f'save part {part.object_name} (using lib {part.mesh_ref.lib_id})')

            utf.add_node(f'\\Cmpnd\\{part.object_name}\\File name', data=part.file_name.encode('UTF-8') + b'\x00')
            utf.add_node(f'\\Cmpnd\\{part.object_name}\\Object name', data=part.object_name.encode('UTF-8') + b'\x00')
            utf.add_node(f'\\Cmpnd\\{part.object_name}\\Index', data=struct.pack('ii', part.index, 0))

            ref_name = f'\\{part.file_name}\\MultiLevel\\Level0\\VMeshPart\\VMeshRef'

            utf.add_node(ref_name, data=part.mesh_ref.to_raw_data())
            timer.step('save part done')

        for hardpoint in self.hardpoints:
            hardpoint.save(utf)

        return utf
