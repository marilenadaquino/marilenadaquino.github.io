#!/usr/bin/env python
# -*- coding: utf-8 -*-
from lxml import etree as ET
import uuid , itertools , os , pprint
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters
from script.ocdm.graphlib import *
from rdflib import Graph, URIRef
from script.ocdm.conf import context_path as context_path
from itertools import groupby
from collections import defaultdict

pp = pprint.PrettyPrinter(indent=1)

class Jats2OC(object):
	
	def __init__(self, filePMC):
		self.filePMC = filePMC
		self.xmlp = ET.XMLParser(encoding="utf-8")
		self.tree = ET.parse(filePMC, self.xmlp)
		self.root = self.tree.getroot()
		self.et = ET.ElementTree(self.root)
	

	def get_text_before(self, element):
		""" extract text before an xml element till the start tag of the parent element"""
		for item in element.xpath("preceding-sibling::*/text()|preceding-sibling::text()"):
			self.item = item
			if self.item:
				yield self.item


	def get_text_after(self, element):
		""" extract text after an xml element till the end tag of the parent element"""
		for item in element.xpath("following-sibling::*/text()|following-sibling::text()"):
			self.item = item
			if self.item:
				yield self.item


	def find_bibRef(self, xref, root):
		""" given a xml element xref or the text value of the element xref
		return the ID (DOI or PMCID) of the corresponding bibliographic entry."""
		if isinstance(xref, str) == False: # input xref element
			self.bibRefID = xref.get('rid')
			self.patternDOI = './/ref[@id="'+self.bibRefID+'"]//pub-id[@pub-id-type="doi"]'
			self.patternPMID = './/ref[@id="'+self.bibRefID+'"]//pub-id[@pub-id-type="pmid"]'
			if self.root.find(self.patternDOI) is not None:
				self.bibRefUID = self.root.find(self.patternDOI).text
			elif self.root.find(self.patternDOI) is None and self.root.find(self.patternPMID) is not None:
				self.bibRefUID = self.root.find(self.patternPMID).text
			else:
				self.bibRefUID = uuid.uuid4()
		else: # input label, intermediate refs that do not have a xref in the full text
			if self.root.find('.//ref[label="'+xref+'"]') is not None:
				self.patternDOIlabel = './/ref[label="'+xref+'"]//pub-id[@pub-id-type="doi"]'
				self.patternPMIDlabel = './/ref[label="'+xref+'"]//pub-id[@pub-id-type="pmid"]'
				if self.root.find(self.patternDOIlabel) is not None:
					self.bibRefUID = self.root.find(self.patternDOIlabel).text
				elif self.root.find(self.patternDOIlabel) is None and root.find(self.patternPMIDlabel) is not None:
					self.bibRefUID = self.root.find(self.patternPMIDlabel).text
				else:
					self.bibRefUID = uuid.uuid4()
			else:
				self.bibRefUID = 'not found'
		return self.bibRefUID


	def xpathSubstring(self, xref, root):
		""" given a xml element and the root element of the xml file, 
		returns the XPath function identifying the sentence wherein it appears
		"""

		self.xrefValue = ET.tostring(xref, method="text", encoding='unicode', with_tail=False)
		self.xrefToString = ET.tostring(xref, encoding='unicode', with_tail=False)
		
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

		string_before = "".join(self.get_text_before(xref)).strip() 
		string_after = "".join(self.get_text_after(xref)).strip() 

		# get start offset of the last sentence in the string before the pointer (0-based index transformed in 1-based index to comply with XPath)
		startSent = int([start for start, end in sentence_splitter.span_tokenize( string_before )][-1])+1  
		# get the length of the string
		strin = sentence_splitter.tokenize( string_before )[-1]+self.xrefValue+sentence_splitter.tokenize( string_after )[0]
		lenSent = len(strin)

		# create the XPath
		self.sentXPathFunction = 'substring(string(./'+ET.ElementTree(root).getpath(xref.getparent())+'),'+str(startSent)+','+str(lenSent)+')'
		return self.sentXPathFunction


	def find_section(self, xref, root):
		"""return the XPath parent section of a xref"""
		section = xref.xpath('ancestor-or-self::sec[1]')
		return self.et.getpath(section[0])


	def find_first_parent(self, xref, root):
		"""return the XPath the first ancestor of a xref if included in a list of elements"""
		if len(xref.xpath('ancestor-or-self::caption')) != 0:
			parent = xref.xpath('./ancestor::caption')
		elif len(xref.xpath('ancestor-or-self::title')) != 0:
			parent = xref.xpath('./ancestor::title')
		elif len(xref.xpath('ancestor-or-self::table')) != 0:
			parent = xref.xpath('./ancestor::table')
		elif len(xref.xpath('ancestor-or-self::fn')) != 0:
			parent = xref.xpath('./ancestor::fn')
		else:
			if len(xref.xpath('ancestor-or-self::p')) != 0:
				parent = xref.xpath('./ancestor::p')
			else:
				parent = xref.xpath('./ancestor::sec')
		return self.et.getpath(parent[0])
		

	def extract_intext_refs(self):
		""" preprocess a nxml file and stores a number of context information 
		related to in-text references in a JSON file, namely:
		0. citing entity : DOI (articleDOI) of the citing article
		1. in-text reference pointers : the value (xrefValue), and the type (singleton, list, or sequence) 
		   of in-text reference pointers
		2. xPaths : xPath of the element (xrefElemXPath), its parent (xrefParentElemXPath), 
		   and the sentence/text chunk (xrefElemSentenceXPath) including in-text reference pointers
		3. discourse elements : the tag of the parent element (xrefParentElem) including the in-text reference pointers
		4. cited entities : PMC-IDs or DOIs (bibRefUID) of cited entities denoted by in-text reference pointers
		"""
		separator = ']'.encode('utf-8')
		prepositions = {','.encode('utf-8'), '\u2013'.encode('utf-8')}
		articleDOI = self.root.find('.//article-id[@pub-id-type="doi"]').text
		
		# list of elems and separators ']'
		# assuming ']' is always the separator of in-text references aand the rest of the text
		xrefOrText = './/xref[@ref-type="bibr"] | .//xref[@ref-type="bibr"]/following-sibling::text()[1]'
		inTextRefElemsAndSeparator = [item[0].encode('utf-8').strip() if isinstance(item, str) \
		else item for item in self.root.xpath(xrefOrText) ]
		
		# group elements by ] and remove separator ']'
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
		self.fullMetadata = [[{\
		'articleDOI':articleDOI,\
		'bibRefUID':self.find_bibRef(xref,self.root), \
		'xrefElemXPath':'./'+self.et.getpath(xref), \
		'xrefElemSentenceXPath':self.xpathSubstring(xref,self.root), \
		'xrefParentElem':xref.getparent().tag, \
		'xrefParentElemXPath':'./'+self.et.getpath(xref.getparent()), \
		'xrefParentElemNormalisedXPath': './'+self.find_first_parent(xref,self.root), \
		'xrefSectionElemXPath': './'+self.find_section(xref,self.root), \
		'xrefValue':xref.text} \
		if isinstance(xref, str) == False else xref for xref in xrefGroup] \
		for xrefGroup in groupsClean]

		# extend sequences
		for groups in self.fullMetadata: # lists in list
			if 'sequence' in groups:
				rangeValues = []
				for group in groups: # dicts in list
					if isinstance(group, str) == False: # do not consider the string 'sequence'	
						rangeValues.append(group['xrefValue'])
				rangeValues.sort()
				for intermediate in range(int(rangeValues[0])+1,int(rangeValues[1])):
					groups.append({\
						'articleDOI':articleDOI,\
						'bibRefUID':self.find_bibRef(str(intermediate),self.root), \
						'xrefElemXPath': 'none', \
						'xrefElemSentenceXPath':groups[0]['xrefElemSentenceXPath'], \
						'xrefParentElem':groups[0]['xrefParentElem'], \
						'xrefParentElemXPath': groups[0]['xrefParentElemXPath'], \
						'xrefParentElemNormalisedXPath': groups[0]['xrefParentElemNormalisedXPath'], \
						'xrefSectionElemXPath': groups[0]['xrefSectionElemXPath'], \
						'xrefValue':str(intermediate) })
		
		# remove the type of xrefGroup
		self.newData = [[xref for xref in xrefGroup if isinstance(xref, str) == False] for xrefGroup in self.fullMetadata]
		
		# group by section
		section = {}
		for xrefGroup in self.newData:				
			groups = groupby(xrefGroup, key=lambda x:x['xrefSectionElemXPath'])
			for x,y in groups:
				section.setdefault(x,[]).append(list(y))
		
		# group by normalised parent
		self.referencesTree = {}
		for sec, listOfLists in section.items():
			sect = {}
			for lis in listOfLists:
				parentGroups = groupby(lis, key=lambda x:x['xrefParentElemNormalisedXPath'])
				for w,z in parentGroups:
					sect.setdefault(w,[]).append(list(z))
			self.referencesTree[sec] = sect

		return self.referencesTree
		

	def fileInFolder(self, types):
		"""create folder for each type of entity"""
		self.type = types
		if not os.path.exists("ccc/br/"):
			os.makedirs("ccc/br/")
		if not os.path.exists("ccc/id/"):
			os.makedirs("ccc/id/")
		if not os.path.exists("ccc/de/"):
			os.makedirs("ccc/de/")
		return self.type


	def parentType(self, xpath):
		"""map the XPath of a element to the corresponding DOCO/DEO class"""
		self.xpath = xpath
		self.elem = re.sub(r"\[.*\]" ,'', self.xpath.rsplit('/', 1)[-1])
		self.elem_mapping = [('p','paragraph'),('caption','caption'),('table','table'),('fn','footnote'),('title','section_title')]
		for el in self.elem_mapping:
			if self.elem == el[0]:
				return el[1]


	def to_rdf(self, graph):
		""" given a JSON file create a graph according to the OCC extended model
		and serialize in JSON-LD files
		"""
		self.data = self.extract_intext_refs()
		self.graph = graph
		# TODO change
		citing_doi = [y[0][0]['articleDOI'] for k,v in self.data.items() for x,y in v.items()][0]

		# br
		br_graph = self.graph.add_br("md", source_agent=None, source=None, res=None)
		
		# id 
		IDgraph = Graph()	
		citing_doi_graph = self.graph.add_id("md", source_agent=None, source=None, res=None)
		citing_doi_graph.create_doi(citing_doi)
		br_graph.has_id(citing_doi_graph) # article DOI
		IDgraph += citing_doi_graph.g

		# de
		DEgraph = Graph() 
		
		# section
		for section_element, parent in self.data.items():
			section_graph = self.graph.add_de("md", source_agent=None, source=None, res=None)
			section_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
			section_graph.create_section()
			section_graph.has_id(section_id)		
			br_graph.contains_in_reference_list(section_graph) # sentences
			# parent element
			for parent_element, groups in parent.items():
				parent_graph = self.graph.add_de("md", source_agent=None, source=None, res=None)
				parent_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
				if self.parentType(parent_element) is not None:
					parent_graph.create_discourse_element(self.parentType(parent_element))	
				parent_graph.has_id(parent_id)
				section_graph.contains_in_reference_list(parent_graph)
				br_graph.contains_in_reference_list(parent_graph)
				# for group in groups:
				# 	if len(group) = 1:
				# 		for key,value in group.items():
				# 			# create the intext ref
				# 	else:
				# 		# create the list
				# 		for xref in group:
				# 			# create the elements of the list
				# 			for key,value in xref.items():
			# sentence
			# discourse_element = self.graph.add_de("md", source_agent=None, source=None, res=None)
			# de_xpath = self.graph.add_id("md", source_agent=None, source=None, res=None)
			# de_xpath.create_xpath(inTextRef['xrefElemSentenceXPath']) 
			# discourse_element.create_sentence()
			# discourse_element.has_id(de_xpath)		
			DEgraph += section_graph.g
			DEgraph += parent_graph.g
			IDgraph += section_id.g
		
		# serialise in files
		BRgraph = br_graph.g
		BRgraph.serialize(destination='ccc/br/'+self.fileInFolder('br')+'.json', format='json-ld', context=context_path_local, auto_compact=True)
		IDgraph.serialize(destination='ccc/id/'+self.fileInFolder('id')+'.json', format='json-ld', context=context_path_local, auto_compact=True)
		DEgraph.serialize(destination='ccc/de/'+self.fileInFolder('de')+'.json', format='json-ld', context=context_path_local, auto_compact=True)


# test
filePMC = 'xml_PMC_sample/PMC5906705.nxml'
jats = Jats2OC(filePMC)
pp.pprint(jats.extract_intext_refs())
context_path_local = 'context.json'
cccgraph= GraphSet("https://w3id.org/oc/corpus/", context_path_local, "ccc/")
jats.to_rdf(cccgraph)


# TODO 

# to_rdf
# check whether br already exists in OC
# does not find the context file
# how to add multiple entities to the same json? 1 json (graph) for each entity (e.g. every ID and DE)?
#	I created graphs for each type of entity
# how to put everything in the br graph? 
# does a br include par, secs, sentences etc. at the same level frbr:part? or only nested frbr:part
# change the path of context.json 
