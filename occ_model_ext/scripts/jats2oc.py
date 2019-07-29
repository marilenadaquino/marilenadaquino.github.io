#!/usr/bin/env python
# -*- coding: utf-8 -*-
from lxml import etree as ET
import pprint , uuid, itertools

def find_bibRef(xref, root):
	if isinstance(xref, str) == False: # input xref element
		bibRefID = xref.get('rid')
		patternDOI = './/ref[@id="'+bibRefID+'"]//pub-id[@pub-id-type="doi"]'
		patternPMID = './/ref[@id="'+bibRefID+'"]//pub-id[@pub-id-type="pmid"]'
		if root.find(patternDOI) is not None:
			bibRefUID = root.find(patternDOI).text
		elif root.find(patternDOI) is None and root.find(patternPMID) is not None:
			bibRefUID = root.find(patternPMID).text
		else:
			bibRefUID = uuid.uuid4()
	else: # input label, intermediate refs that do not have a xref in the full text
		if root.find('.//ref[label="'+xref+'"]') is not None:
			patternDOIlabel = './/ref[label="'+xref+'"]//pub-id[@pub-id-type="doi"]'
			patternPMIDlabel = './/ref[label="'+xref+'"]//pub-id[@pub-id-type="pmid"]'
			if root.find(patternDOIlabel) is not None:
				bibRefUID = root.find(patternDOIlabel).text
			elif root.find(patternDOIlabel) is None and root.find(patternPMIDlabel) is not None:
				bibRefUID = root.find(patternPMIDlabel).text
			else:
				bibRefUID = uuid.uuid4()
		else:
			bibRefUID = 'not found'
	return bibRefUID


def extract_intext_ref(filePMC):
	""" preprocess a nxml file and stores a number of context components in a JSON file, namely:
	0. articleDOI : DOI of the citing article
	1. inTextRef : single in-text reference pointers, lists, and sequences of in-text reference pointers
	2. xPointer : xPointer of sentence/text chunk including in-text reference pointers
	3. discourseElement : paragraph/table/footnote and section including the in-text reference pointers
	4. bibRefPMID/DOI : PMC-IDs or DOIs of bibliographic references denoted by in-text reference pointers
	"""
	xmlp = ET.XMLParser(encoding="utf-8")
	tree = ET.parse(filePMC, xmlp)
	root = tree.getroot()
	et = ET.ElementTree(root)
	pp = pprint.PrettyPrinter(indent=1)

	separator = ']'.encode('utf-8')
	prepositions = {','.encode('utf-8'), '\u2013'.encode('utf-8')}
	
	# list of elems and separators ']'
	inTextRefElemsAndSeparator = [item[0].encode('utf-8').strip() if isinstance(item, str) else item for item in root.xpath('.//xref[@ref-type="bibr"] | .//xref[@ref-type="bibr"]/following-sibling::text()[1]') ]
	
	# group elements separated by ] and remove separator ']'
	groups = [list(x[1]) for x in itertools.groupby(inTextRefElemsAndSeparator, lambda x: x==separator) if not x[0]]
	
	# store whether the group of xrefs is a sequence, a singleton, or a list
	for group in groups:		
		if ','.encode('utf-8') in group:
			group.append('list')
		elif '\u2013'.encode('utf-8') in group:
			group.append('sequence')
		else:
			group.append('singleton')
	print('groups',groups)
	
	# remove separators ',' and '\u2013'
	groupsClean = [list(i for i in j if i not in prepositions) for j in groups]
	print('groupsClean',groupsClean)

	fullMetadata = [[{'xrefElemXPath':'./'+et.getpath(xref), 'xrefValue':xref.text, 'xrefParentElem':xref.getparent().tag, 'xrefParentElemXPath':'./'+et.getpath(xref.getparent()), 'bibRefUID':find_bibRef(xref,root)} if isinstance(xref, str) == False else xref for xref in xrefGroup] for xrefGroup in groupsClean]

	# extend sequences
	for groups in fullMetadata: # lists in list
		if 'sequence' in groups:
			rangeValues = []
			for group in groups: # dicts in list
				if isinstance(group, str) == False: # do not consider the string 'sequence'	
					rangeValues.append(group['xrefValue'])
			rangeValues.sort()
			for intermediate in range(int(rangeValues[0])+1,int(rangeValues[1])):
				groups.append({'xrefElemXPath': 'none', 'xrefValue':str(intermediate), 'xrefParentElem':groups[0]['xrefParentElem'], 'xrefParentElemXPath': groups[0]['xrefParentElemXPath'], 'bibRefUID':find_bibRef(str(intermediate),root) })
		
	pp.pprint(fullMetadata)
	

filePMC = 'xml_PMC_sample/PMC5906705.nxml'
extract_intext_ref(filePMC)
