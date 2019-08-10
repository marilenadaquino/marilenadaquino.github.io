#!/usr/bin/env python
# -*- coding: utf-8 -*-
import uuid , os , re
from script.ocdm.graphlib import GraphEntity
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters
from lxml import etree as ET

# ABBREVIATIONS 
# elem 	= XML element
# be 	= bibliographic entry
# br 	= bibliographic resource
# itr 	= in-text reference pointer

# VARIABLES
# sentence/text chunk tokenizer 
abbreviations_list_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Abbreviations.txt'))
separator = ']'.encode('utf-8')
prepositions = [','.encode('utf-8'), '\u2013'.encode('utf-8')] # first lists separator, second sequences separator
elem_text = './/xref[@ref-type="bibr"] | .//xref[@ref-type="bibr"]/following-sibling::text()[1]'

citing_doi = './/article-id[@pub-id-type="doi"]'

# XML elements handled by the OC model
section_tag = 'sec'
caption_tag = 'caption'
title_tag = 'title'
table_tag = 'table'
footnote_tag = 'fn'
paragraph_tag = 'p'

# mapping XML tags to graphlib bibliographic entities
elem_mapping = [(paragraph_tag,GraphEntity.paragraph),\
				(caption_tag,GraphEntity.caption),\
				(table_tag,GraphEntity.table),\
				(footnote_tag,GraphEntity.footnote),\
				(title_tag,GraphEntity.section_title),\
				(section_tag,GraphEntity.section)]
	

# methods for bibliographic entities
def find_citing_doi(root):
	"""
	params: root -- the root element of the XML document
	return: DOI or uuid of the citing entity
	"""
	if root.find(citing_doi) is not None:
		article_doi = root.find(citing_doi).text
	else:
		article_doi = uuid.uuid4()
	return article_doi


def get_be_id(elem):
	"""
	params: elem -- the XML element including the itr
	return: ID of the XML element including the be denoted by the itr
	"""
	return elem.get('rid')


def find_cited_doi(elem,root): 
	"""
	params: elem -- the XML element OR the text value of the XML element including the itr 
	params: root -- the root element of the XML document
	return: DOI, PMID, or uuid of the be denoted by the itr
	"""
	if isinstance(elem, str) == False: 
		doi = './/ref[@id="'+get_be_id(elem)+'"]//pub-id[@pub-id-type="doi"]'
		pmid = './/ref[@id="'+get_be_id(elem)+'"]//pub-id[@pub-id-type="pmid"]'
	else:
		if root.find('.//ref[label="'+elem+'"]') is not None:
			doi = './/ref[label="'+elem+'"]//pub-id[@pub-id-type="doi"]'
			pmid = './/ref[label="'+elem+'"]//pub-id[@pub-id-type="pmid"]'
		else:
			doi,pmid = None
			be_id = 'not found'
	if root.find(doi) is not None:
		be_id = root.find(doi).text 
	elif root.find(doi) is None and root.find(pmid) is not None:
		be_id = root.find(pmid).text
	else:
		be_id = uuid.uuid4()
	return be_id


# methods for XML/text parsing
def clean(string):
	"""return: encoded stripped string"""
	return string.encode('utf-8').strip()


def get_text_before(elem):
	""" extract text before an xml element till the start tag of the parent element"""
	for item in elem.xpath("preceding-sibling::*/text()|preceding-sibling::text()"):
		item = item
		if item:
			yield item


def get_text_after(elem):
	""" extract text after an xml element till the end tag of the parent element"""
	for item in elem.xpath("following-sibling::*/text()|following-sibling::text()"):
		item = item
		if item:
			yield item


def xpath_substring(elem, root, abb_list_path):
	""" 
	params: elem -- the XML element including the itr
	params: root -- the root element of the XML document
	params: abb_list_path -- a txt file including the list of abbreviations for splitting sentences
	return: XPath of the sentence including the
	"""
	elem_value = ET.tostring(elem, method="text", encoding='unicode', with_tail=False)
	
	abbreviations_list = []
	with open(abb_list_path, 'r') as f:
		for line in f.readlines():
			if not len(line) == 0:
				abbreviations_list.append(line.strip())

	punkt_param = PunktParameters()
	punkt_param.abbrev_types = set(abbreviations_list)
	sentence_splitter = PunktSentenceTokenizer(punkt_param)

	string_before = "".join(get_text_before(elem)).strip() 
	string_after = "".join(get_text_after(elem)).strip() 

	# start offset of the last sentence in the stringified parent element that include the itr (0-based index transformed in 1-based index to comply with XPath)
	startSent = int([start for start, end in sentence_splitter.span_tokenize( string_before )][-1])+1  
	# get the length of the string
	strin = sentence_splitter.tokenize( string_before )[-1]+elem_value+sentence_splitter.tokenize( string_after )[0]
	lenSent = len(strin)

	# create the XPath
	sentXPathFunction = 'substring(string(./'+ET.ElementTree(root).getpath(elem.getparent())+'),'+str(startSent)+','+str(lenSent)+')'
	return sentXPathFunction


def find_container_xpath(elem, container_tag, root):
	"""
	params: elem -- an XML element
	params: container_tag -- the tag of the seeked ancestor
	params: root -- the root element of the XML document
	return: XPath of the first selected ancestor of the element
	"""
	et = ET.ElementTree(root)
	section = elem.xpath('ancestor-or-self::'+container_tag+'[1]')
	return et.getpath(section[0])


def find_container_title(elem, container_tag, root):
	"""
	params: elem -- an XML element
	params: container_tag -- the tag of the container element including the title
	return: title -- the tag of the element containing the title of the container
	"""
	et = ET.ElementTree(root)
	title = elem.xpath('ancestor-or-self::'+container_tag+'[1]//'+title_tag)
	if len(elem.xpath('ancestor-or-self::'+container_tag+'[1]//'+title_tag)) != 0:
		title = ET.tostring( elem.xpath('ancestor-or-self::'+container_tag+'[1]//'+title_tag)[0], method="text", encoding='unicode', with_tail=False).strip()
	else:
		title = ''
	return title


def find_closest_parent(elem, root):
	"""
	params: elem -- an XML element
	params: root -- the root element of the XML document
	return: XPath of the closest parent element that is handled by the OC model
	"""
	et = ET.ElementTree(root)
	if len(elem.xpath('ancestor-or-self::'+caption_tag)) != 0:
		parent = elem.xpath('./ancestor::'+caption_tag)
	elif len(elem.xpath('ancestor-or-self::'+title_tag)) != 0:
		parent = elem.xpath('./ancestor::'+title_tag)
	elif len(elem.xpath('ancestor-or-self::'+table_tag)) != 0:
		parent = elem.xpath('./ancestor::'+table_tag)
	elif len(elem.xpath('ancestor-or-self::'+footnote_tag)) != 0:
		parent = elem.xpath('./ancestor::'+footnote_tag)
	else:
		if len(elem.xpath('ancestor-or-self::'+paragraph_tag)) != 0:
			parent = elem.xpath('./ancestor::'+paragraph_tag)
		else:
			parent = elem.xpath('./ancestor::'+section_tag)
	return et.getpath(parent[0])


# methods for serialising RDF 
def elem_to_type(xpath):
	"""
	params: xpath -- XPath of an element to be mapped to RDF
	return: DOCO/DEO class
	"""
	elem = re.sub(r"\[.*\]" ,'', xpath.rsplit('/', 1)[-1])
	for el in elem_mapping:
		if elem == el[0]:
			return el[1]


def file_in_folder(e_type):
	"""create folder for each type of entity"""
	if not os.path.exists("ccc/br/"):
		os.makedirs("ccc/br/")
	if not os.path.exists("ccc/id/"):
		os.makedirs("ccc/id/")
	if not os.path.exists("ccc/de/"):
		os.makedirs("ccc/de/")
	return e_type

