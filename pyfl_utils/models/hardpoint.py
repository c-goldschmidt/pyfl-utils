import struct


class Hardpoint(object):
    def __init__(self, file_name):
        self.type = None
        self.name = None
        self.axis = None
        self.orientation = None
        self.min = None
        self.max = None
        self.position = None
        self.file_name = file_name

    @staticmethod
    def fixed(file_name, name, position, orientation):
        hp = Hardpoint(file_name)

        hp.type = 'Fixed'
        hp.name = name
        hp.position = position
        hp.orientation = orientation

        return hp

    def save(self, utf):
        base_name = f'\\{self.file_name}\\Hardpoints\\{self.type}\\{self.name}'

        if self.orientation:
            utf.add_node(f'{base_name}\\Orientation', data=struct.pack('f' * 9, *self.orientation))

        if self.position:
            utf.add_node(f'{base_name}\\Position', data=struct.pack('f' * 3, *self.position))

        if self.axis:
            utf.add_node(f'{base_name}\\Axis', data=struct.pack('f' * 3, *self.axis))

        if self.min:
            utf.add_node(f'{base_name}\\Min', data=struct.pack('f' * 3, *[self.min, 0]))

        if self.max:
            utf.add_node(f'{base_name}\\Max', data=struct.pack('f' * 3, *[self.max, 0]))
