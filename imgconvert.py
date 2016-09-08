import logging
import math
import os
from PIL import Image
from tempfile import NamedTemporaryFile

_logger = logging.getLogger(__name__)

def to_tga(filename):
	im = Image.open(filename)
	im_name = '.'.join(filename.split('.')[:-1])
	im.save(im_name + '.tga')
	
def tga_from_string(string):
	out_size = (256, 256)
	max_h = (out_size[0] * 3) / 4
	max_w = out_size[1]
	
	return_file = NamedTemporaryFile(delete=False, suffix='.tga')
	tmp_file = NamedTemporaryFile(delete=False)
	
	with open(tmp_file.name, 'wb') as file:
		file.write(string)
		
	with Image.open(tmp_file.name) as img:
		new_size = _rescale_size(max_w, max_h, *img.size)
			
		img = img.resize(new_size, Image.LANCZOS)
		img = img.convert('RGBA')
		copy = Image.new('RGBA', out_size, (0, 0, 0, 0))
		
		offset_x = int(math.floor((out_size[0] - img.size[0]) / 2.0))
		offset_y = int(math.floor((out_size[1] - img.size[1]) / 2.0))
		
		_logger.debug('pasting {}x{} image on {}x{} canvas, x: {}, y:{}'.format(
			img.size[0], img.size[1],
			copy.size[0], copy.size[1],
			offset_x, offset_y,
		))
		
		copy.paste(img, (offset_x, offset_y), img)
		copy.save(return_file.name)
		copy.close()
	
	try:
		os.remove(tmp_file.name)
	except:
		print 'can\'t remove tempfile!'
	
	return return_file
	
def _rescale_size(max_w, max_h, img_w, img_h):
	_logger.debug('h: {}, w: {} (max {}x{})'.format(img_h, img_w, max_w, max_h))
	factor = max_w / float(max([img_h, img_w]))
	img_h *= factor
	img_w *= factor
	
	_logger.debug('h: {}, w: {} (factor {})'.format(img_h, img_w, factor))
	
	out = [img_w, img_h]
	
	if out[0] > max_w:
		out[1] = (max_w / out[0]) * out[1]
		out[0] = max_w
		
	if out[1] > max_h:
		out[0] = (max_h / out[1]) * out[0]
		out[1] = max_h
		
	out[0] = int(math.floor(out[0]))
	out[1] = int(math.floor(out[1]))
		
	_logger.debug('{} * {} => {} * {}'.format(img_h, img_w, *out))
	
	return tuple(out)
		
	