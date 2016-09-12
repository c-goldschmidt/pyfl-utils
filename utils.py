import freelancer

def getSectionByKeyValuePair(sections, key, value=None, multiple=False):
    result_set = []
    
    for section in sections:
        selected = section.get(key) == value if value else section.get(key)
        if selected:
            if multiple:
                result_set.append(section)
            else:
                return section
    
    if multiple:
        return result_set

def getSectionsByExistingKey(sections, key):
    return [section for section in sections if section.get(key)]

def removeSectionByKeyValuePair(sections, key, value=None, multiple=False):
    selected = getSectionByKeyValuePair(sections, key, value, multiple)
    
    if multiple:
        for section in selected:
            sections.remove(section)
    else:
        sections.remove(selected)
		
def initFLModule(freelancer):
    freelancer.init()

    freelancer.loadUniverse()
    freelancer.loadData(r'missions\news.ini')

    # freelancer.outputStats()
    # freelancer.func.performMatchQueue()
    # freelancer.writeSummaries()

def updateNewsBases(newsINI, newsID='all'):
	allBases = freelancer.universe.getAllBases()
	
	if newsID == 'all':
		newsSections = getSectionByKeyValuePair(newsINI, 'newsid', multiple=True)
		for section in newsSections:
			updateNewsBasesInSection(section, allBases)
	else:
		try:
			newsSection = getSectionByKeyValuePair(newsINI, 'newsid', newsID)
			updateNewsBasesInSection(section, allBases)
		except:
			print('"{}" not found!'.format(newsID))
		
	newsINI.write()
	
def updateNewsBasesInSection(section, bases=None):
	if not bases:
		bases = freelancer.universe.getAllBases()
	
	section.set('base', bases)
	