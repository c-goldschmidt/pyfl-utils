import logging
import os
from .fldll import FLDll
from .utf import UTFFile
from .inifile import INIFile, IniSection
from .imgconvert import tga_from_string
from PIL import Image
from .settings import settings

_logger = logging.getLogger(__name__)


class Newsvendor(object):
	
	def __init__(self, settings=settings):
		self._news_ini = INIFile(settings.news)
		self._dll = FLDll(settings.dll, settings.fl)
		self._tex = UTFFile(settings.tex)

	def handle_get(self, params):
		params = params[2:]
		
		if len(params) == 0:
			return self._ini_to_json(self._news_ini.get_by_key('newsid'))
		else:
			return self._obj_to_json(self._news_ini.get_by_kv('newsid', params[0]))
			
	def handle_post(self, params, data):	
		params = params[2:]
		entry = None
		
		if 'new_newsid' in data:
			newsid = data['new_newsid'][0]
		elif len(params) > 0:
			newsid = params[0]
			
		if len(params) == 0:
			self._create_news(newsid, data=data)
		else:
			self._update_news(params[0], newsid, data)
		
		self._news_ini.save()
		self._dll.save()
		self._tex.save()
					
		return {'status': 'OK', 'newsid': newsid}
		
	def handle_delete(self, params):
		params = params[2:]
		
		if len(params) > 0:
			try:
				entry = self._news_ini.get_by_kv('newsid', params[0], multiple=False)
			except KeyError:
				_logger.warning('newsid {} does not exist, but shall be updated!'.format(params[0]))
				return False
		
			self._delete_string_from_dll(entry.get('headline'))
			self._delete_infocard_from_dll(entry.get('text'))
			self._delete_image_from_texture(params[0])
			self._delete_news(params[0])
			
			self._news_ini.save()
			self._dll.save()
			self._tex.save()
			
			return True
			
		return False
		
	def _data_to_news_object(self, newsid, data, old_object=None):
		if 'new_logo' in data:
			if old_object:
				self._update_image_in_texture(old_object.get('newsid'), newsid, data['new_logo'][0])
			else:
				self._add_image_to_texture(newsid, data['new_logo'][0])
		elif old_object:
			self._rename_image_in_texture(old_object.get('newsid'), newsid)
	
		if 'new_logo' in data:
			logo = 'newsid_{}'.format(newsid)
		else:
			logo = data['logo'][0]
			
		if old_object:
			_logger.debug(old_object)
			headline = self._update_string_in_dll(data['headline'][0], old_object.get('headline'))
			text = self._update_infocard_in_dll(data['text'][0], old_object.get('text'))
		else:
			headline = self._add_string_to_dll(data['headline'][0])
			text = self._add_infocard_to_dll(data['text'][0])
			
		return {
			'headline': headline,
			'category': headline,
			'text': text,
			'icon': data['icon'][0],
			'logo': logo,
		}
		
	def _add_string_to_dll(self, string):
		_logger.debug('adding string')
		dll_id = self._dll.add_string(string)
		return self._dll.get_ini_id(dll_id)
		
	def _update_string_in_dll(self, string, ini_id):
		_logger.debug('updating string {}'.format(ini_id))
		_, id = self._dll.get_dll_id_from_ini_id(ini_id)
		self._dll.update_string(string, id)
		return ini_id
		
	def _delete_string_from_dll(self, ini_id):
		_logger.debug('deleting string {}'.format(ini_id))
		_, id = self._dll.get_dll_id_from_ini_id(ini_id)
		return self._dll.delete_string(id)
		
	def _add_infocard_to_dll(self, string):
		_logger.debug('adding infocard')
		dll_id = self._dll.add_infocard(string)
		return self._dll.get_ini_id(dll_id)
		
	def _update_infocard_in_dll(self, string, ini_id):
		_logger.debug('updating infocard {}'.format(ini_id))
		_, id = self._dll.get_dll_id_from_ini_id(ini_id)
		self._dll.update_infocard(string, id)
		return ini_id
		
	def _delete_infocard_from_dll(self, ini_id):
		_logger.debug('deleting string {}'.format(ini_id))
		_, id = self._dll.get_dll_id_from_ini_id(ini_id)
		return self._dll.delete_infocard(id)
				
	def _delete_news(self, news_id):
		try:
			self._news_ini.rem_by_kv('newsid', news_id)
			return True
		except KeyError:
			_logger.warning('newsid {} dows not exist, but shall be deleted!'.format(news_id))
			return False
		
	def _update_news(self, old_newsid, new_newsid, data):
		try:
			entry = self._news_ini.get_by_kv('newsid', old_newsid, multiple=False)
		except KeyError:
			_logger.warning('newsid {} dows not exist, but shall be updated!'.format(old_newsid))
			pass
										
		news_object = self._data_to_news_object(new_newsid, data, entry)
	
		self._delete_news(old_newsid)
		self._create_news(new_newsid, news_object=news_object)
			
	def _create_news(self, new_newsid, news_object=None, data=None):
		if not news_object:				
			news_object = self._data_to_news_object(new_newsid, data)
	
		if self._news_ini.get_by_kv('newsid', new_newsid):
			raise Exception('"{}" is already existing!'.format(new_newsid))
		
		section = IniSection('NewsItem')
		
		section.set('rank', 'base_0_rank, mission_end')
		section.set('newsid', new_newsid)
		
		for key in news_object:
			section.set(key, str(news_object[key]))
			
		self._update_bases(section)		
		self._news_ini.add(section)
			
	def export_images(self):
		basepath = './html/img/newsimages/'
		
		# del old
		for root, dirs, files in os.walk(basepath):
			for name in files:
				os.remove(os.path.join(root, name))		
				
		self._tex.save_data_to_file('MIP0', '.tga', basepath)
		
		for root, dirs, files in os.walk(basepath):
			for in_name in files:
				in_name = os.path.join(root, in_name)
				out_name = in_name.replace('_Texture library_', '')
				out_name = out_name.replace('_MIP0.tga', '.png')
				
				im = Image.open(in_name)
				im.save(out_name)		
				os.remove(in_name)
				
	def export_image(self, image_name):
		basepath = './html/img/newsimages/'
		in_name = os.path.join(basepath, '_Texture library_' + image_name + '_MIP0.tga')
		out_name = os.path.join(basepath, image_name + '.png') 
		
		if os.path.isfile(out_name):
			os.remove(out_name)
		
		self._tex.save_data_to_file('\\Texture library\\' + image_name + '\\MIP0', in_name)
		
		if os.path.isfile(in_name):
			im = Image.open(in_name)
			im.save(out_name)
			os.remove(in_name)
			return True		
		else:
			_logger.warning('can\'t export "{}"'.format(image_name))
			return False		
	
	def _obj_to_json(self, obj):	
		new_obj = {
			'headline': {'id': obj.get('headline'), 'text': self._dll.get_by_id(obj.get('headline'))},
			'category': {'id': obj.get('category'), 'text': self._dll.get_by_id(obj.get('category'))},
			'text': {'id': obj.get('text'), 'text': self._dll.get_by_id(obj.get('text'))},
			'icon': obj.get('icon'),
			'logo': obj.get('logo'),
			'newsid': obj.get('newsid'),
		}
		return new_obj
	
	def _ini_to_json(self, arr):
		return [self._obj_to_json(obj) for obj in arr]
		
	def _add_image_to_texture(self, newsid, imagestring):
		tempfile = tga_from_string(imagestring)
		node_name = '\\Texture library\\newsid_{}\\MIP0'.format(newsid)
		self._tex.update_node_data(node_name, tempfile.name, True)
		
		try:
			os.remove(tempfile.name)
		except:
			_logger.warning('could not clean tempfile!')
			pass
			
	def _update_image_in_texture(self, old_newsid, new_newsid, imagestring):
		self._add_image_to_texture(old_newsid, imagestring)
		self._rename_image_in_texture(old_newsid, new_newsid)
			
	def _rename_image_in_texture(self, old_newsid, new_newsid):
		old_node_name = '\\Texture library\\newsid_{}\\MIP0'.format(old_newsid)
		new_node_name = '\\Texture library\\newsid_{}\\MIP0'.format(new_newsid)
		
		if not self._tex.rename_node(old_node_name, new_node_name):
			_logger.warning('error renaming texture node!')
			
	def _delete_image_from_texture(self, newsid):
		node_name = 'Texture library\\newsid_{}'.format(newsid)
		
		if not self._tex.delete_node(node_name):
			_logger.warning('error deleting texture node!')
			
		self._tex.print_tree()
			
	def _update_bases(self, ini_section):
		universe = INIFile(settings.universe)
		
		base_sections = universe.get('base')
		
		bases = []
		for section in base_sections:
			bases.append(section.get('nickname'))
		ini_section.set('base', bases)
