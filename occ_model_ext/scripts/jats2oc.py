#!/usr/bin/env python
# -*- coding: utf-8 -*-
from lxml import etree as ET
import pprint , uuid, itertools , os
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters
# TODO 
# wrapper for iterating over all the xml files
# control whther the citation style is always the same
# new function for sentence tokenization - add sentence xpath in fullMetadata

def get_text_before(element):
    for item in element.xpath("preceding-sibling::*/text()|preceding-sibling::text()"):
        item = item.strip()
        if item:
            yield item


def get_text_after(element):
    for item in element.xpath("following-sibling::*/text()|following-sibling::text()"):
        item = item.strip()
        if item:
            yield item


def find_bibRef(xref, root):
	""" given a xml element xref or the text value of the element xref
	finds in the bibliography the corresponding element ref."""
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


def xpathSubstring(xref,root):
	"""given a xml element and the root element of the xml file, 
	returns the XPath function identifying the sentence wherein it appears
	"""

	xrefValue = ET.tostring(xref, method="text", encoding='unicode', with_tail=False)
	xrefToString = ET.tostring(xref, encoding='unicode', with_tail=False)
	
	# enrich the list of abbreviations with Abbreviations.txt
	ABBREVIATIONS_LIST = ['dr', 'vs', 'mr', 'mrs', 'prof', 'inc', 'al', 'eg', 'fig', 'figs', 'Fig', 'tab', 'eq', 'ref', 'e.g', 'refs', 'i.e', 'cf', 'eqs', 'ca', 'm.f']

	abbpath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Abbreviations.txt'))
	with open(abbpath, 'r') as f:
		for line in f.readlines():
			if not len(line) == 0:
				ABBREVIATIONS_LIST.append(line.strip())

	# Initialize Sentence Splitter
	punkt_param = PunktParameters()
	punkt_param.abbrev_types = set(ABBREVIATIONS_LIST)
	sentence_splitter = PunktSentenceTokenizer(punkt_param)

	string_before = "".join(get_text_before(xref)) 
	string_after = "".join(get_text_after(xref))

	# get start offset of the last sentence in the string before the pointer (0-based index transformed in 1-based index to comply with XPath)
	startSent = int([start for start, end in sentence_splitter.span_tokenize( string_before )][-1])+1  
	print(sentence_splitter.tokenize( string_before )[-1].encode('utf-8'),sentence_splitter.span_tokenize( string_before )[-1])
	# get the length of the string
	strin = sentence_splitter.tokenize( string_before )[-1]+xrefValue+sentence_splitter.tokenize( string_after )[0]
	print(strin.encode('utf-8'))
	lenSent = len(strin)

	# create the XPath
	sentXPathFunction = 'substring(string(./'+ET.ElementTree(root).getpath(xref.getparent())+'),'+str(startSent)+','+str(lenSent)+')'
	return sentXPathFunction

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
	
	# list of elems and separators ']' -- assuming ']' is always the separator of in-text references aand the rest of the text
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
	
	# remove separators ',' and '\u2013'
	groupsClean = [list(i for i in j if i not in prepositions) for j in groups]

	# include all the metadata related to the in-text references
	fullMetadata = [[{'xrefElemXPath':'./'+et.getpath(xref), 'xrefValue':xref.text, 'xrefParentElem':xref.getparent().tag, 'xrefParentElemXPath':'./'+et.getpath(xref.getparent()), 'bibRefUID':find_bibRef(xref,root)} if isinstance(xref, str) == False else xref for xref in xrefGroup] for xrefGroup in groupsClean]

	for xrefGroup in groupsClean:
		for xref in xrefGroup:
			if isinstance(xref, str) == False:
				print(xpathSubstring(xref,root))

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
	

filePMC = 'xml_PMC_sample/PMC5906705.nxml'
extract_intext_ref(filePMC)
