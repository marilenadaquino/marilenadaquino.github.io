#!/usr/bin/env python
# -*- coding: utf-8 -*-
import uuid , os , re ,rdflib
from rdflib.namespace import XSD, RDF, RDFS, Namespace
from rdflib.term import Literal
from script.ocdm.graphlib import GraphEntity
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters
from lxml import etree as ET

# ABBREVIATIONS
# elem 	= XML element
# be 	= bibliographic entry
# br 	= bibliographic resource
# rp 	= in-text reference pointer

# VARIABLES
abbreviations_list_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Abbreviations.txt'))

# TO REMOVE
pl_start_sep = '['
pl_end_sep = ']'.encode('utf-8')
pl_start_separators = ['[','(']
pl_end_separators = [']',')']
rp_separators_in_list = [','.encode('utf-8'), '\u2013'.encode('utf-8')] # first lists separator, second sequences separator

# XPATH: modify find_rp() to associate the correct xml element to rp
rp_tail = '/following-sibling::text()[1]'
rp_closest_parent = '/ancestor::*[1]'
rp_child = '/child::*[1]'
citing_doi = './/article-id[@pub-id-type="doi"]'

# XML elements mapped to the OC model
section_tag = 'sec'
caption_tag = 'caption'
title_tag = 'title'
table_tag = 'table'
notes_tag = 'notes'
footnote_tag = 'fn'
paragraph_tag = 'p'
be_tag = 'ref'

# other XML elements
front_tag = 'front'
back_tag = 'back'

parent_elements_names = [notes_tag, section_tag, caption_tag, title_tag, table_tag, footnote_tag, paragraph_tag, 'tr','td','th']


# mapping to graphlib bibliographic entities
elem_mapping = [(caption_tag,GraphEntity.caption),\
				(paragraph_tag,GraphEntity.paragraph),\
				(table_tag,GraphEntity.table),\
				(footnote_tag,GraphEntity.footnote),\
				(notes_tag,GraphEntity.footnote),\
				(title_tag,GraphEntity.section_title),\
				(section_tag,GraphEntity.section)]

# Namespaces
C4O = Namespace("http://purl.org/spar/c4o/")
DATACITE = Namespace("http://purl.org/spar/datacite/")
LITERAL = Namespace("http://www.essepuntato.it/2010/06/literalreification/")


# methods for XML bibliographic entities
def find_rp(root):
	"""
	params: root -- the root element of the XML document
	return: the XPATH of rp (e.g. 'xref[@ref-type="bibr"]' or 'xref')
	"""
	et = ET.ElementTree(root)
	if len(root.xpath('.//xref[@ref-type="bibr"]')) != 0:
		rp_path = 'xref[@ref-type="bibr"]'
	else:
		if len(root.xpath('.//xref[@rid = //ref/@id]')) != 0:
			rp_path = 'xref[@rid = //ref/@id]'
	return rp_path


def find_citing_doi(root):
	"""
	params: root -- the root element of the XML document
	return: DOI or uuid of the citing entity
	"""
	if root.find(citing_doi) is not None:
		article_doi = root.find(citing_doi).text
	else:
		article_doi = str(uuid.uuid4())
	return article_doi


def get_be_id(elem):
	"""
	params: elem -- the XML element including the rp
	return: ID of the XML element including the be denoted by the rp
	"""
	if 'rid' in elem.attrib:
		return elem.get('rid')
	else:
		return elem.getparent().get('rid')


def find_cited_doi(elem,root):
	"""
	params: elem -- the XML element OR the text value of the XML element including the rp
	params: root -- the root element of the XML document
	return: DOI, PMID, or uuid of the be denoted by the rp
	"""
	if isinstance(elem, str) == False:
		doi = './/ref[@id="'+get_be_id(elem)+'"]//pub-id[@pub-id-type="doi"]'
		pmid = './/ref[@id="'+get_be_id(elem)+'"]//pub-id[@pub-id-type="pmid"]'
		be_path = './/ref[@id="'+get_be_id(elem)+'"]'
	else:
		if root.find('.//ref[label="'+elem+'"]') is not None:
			doi = './/ref[label="'+elem+'"]//pub-id[@pub-id-type="doi"]'
			pmid = './/ref[label="'+elem+'"]//pub-id[@pub-id-type="pmid"]'
			be_path = './/ref[label="'+elem+'"]'
		else:
			doi,pmid,be_path = None
			be_id = 'not found'
	if root.find(doi) is not None:
		be_id = root.find(doi).text
	elif root.find(doi) is None and root.find(pmid) is not None:
		be_id = root.find(pmid).text
	else:
		be_id = str(uuid.uuid4())
	be_text = ET.tostring(root.find(be_path), method="text", encoding='unicode', with_tail=False).strip() 
	return be_id, be_text


def find_xmlid(elem,root):
	"""
	params: elem -- the XML element OR the text value of the XML element including the rp
	params: root -- the root element of the XML document
	return: xmlid of the rp, i.e. of the bibentry denoted by the rp
	"""
	if isinstance(elem, str) == False:
		xmlid = get_be_id(elem)
	else:
		if root.find('.//ref[label="'+elem+'"]') is not None:
			xmlid = root.find('.//ref[label="'+elem+'"]').get('id')
		else:
			xmlid = None
	return xmlid

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


def xpath_sentence(elem, root, abb_list_path):
	"""
	params: elem -- the rp
	params: root -- the root element of the XML document
	params: abb_list_path -- a txt file including the list of abbreviations for splitting sentences
	return: XPath of the sentence including the rp
	"""
	elem_value = ET.tostring(elem, method="text", encoding='unicode', with_tail=False)
	with open(abb_list_path, 'r') as f:
		abbreviations_list = [line.strip() for line in f.readlines() if not len(line) == 0]

	punkt_param = PunktParameters()
	punkt_param.abbrev_types = set(abbreviations_list)
	sentence_splitter = PunktSentenceTokenizer(punkt_param)

	string_before = "".join(get_text_before(elem)).strip()
	string_after = "".join(get_text_after(elem)).strip()

	# offset of sentence in the stringified parent element that include the rp 
	# (0-based index transformed in 1-based index -- +1 -- to comply with XPath)
	if len(string_before) == 0:
		str_before = ''
		start_sent = 1
	else:
		str_before = sentence_splitter.tokenize( string_before )[-1]
		start_sent = int([start for start, end in sentence_splitter.span_tokenize( string_before )][-1])+1
	if len(string_after) == 0:
		str_after = ''
	else:
		str_after = sentence_splitter.tokenize( string_after )[0]
	len_sent = len(str_before+elem_value+str_after)
	sent_xpath_function = 'substring(string(./'+ET.ElementTree(root).getpath(elem.getparent())+'),'+str(start_sent)+','+str(len_sent)+')'
	return sent_xpath_function


def xpath_list(elem, root, start_sep, end_sep):
	"""
	params: elem -- the rp
	params: root -- the root element of the XML document
	params: strat_sep, end_sep -- separators of the substring representing a list
	return: XPath of the list including the rp
	"""
	elem_value = ET.tostring(elem, method="text", encoding='unicode', with_tail=False)
	string_before = "".join(get_text_before(elem)).strip()
	string_after = "".join(get_text_after(elem)).strip()
	if string_before.rfind(start_sep) != -1:
		start_sep_index = string_before.rfind(start_sep)+1
	else:
		start_sep_index = 1
	if string_after.find(end_sep.decode('utf-8')) != -1:
		end_sep_index = string_after.find(end_sep.decode('utf-8'))+1 # include the character
	else:
		end_sep_index = len(string_after)
	strin = string_before[start_sep_index:]+elem_value+string_after[:end_sep_index+1]
	py_strin = string_before[start_sep_index-1:]+elem_value+string_after[:end_sep_index]
	len_list = len(strin)
	list_xpath_function = 'substring(string(./'+ET.ElementTree(root).getpath(elem.getparent())+'),'+str(start_sep_index)+','+str(len_list)+')'
	return [py_strin,list_xpath_function]


def find_container_xpath(elem, container_tag, root):
	"""
	params: elem -- an XML element
	params: container_tag -- the tag of the seeked ancestor
	params: root -- the root element of the XML document
	return: XPath of the first selected ancestor of the element
	"""
	# TODO improve
	et = ET.ElementTree(root)
	if len(elem.xpath('./ancestor-or-self::'+container_tag+'[1]')) != 0:
		section = elem.xpath('./ancestor-or-self::'+container_tag+'[1]')[0]
	else:
		if len(elem.xpath('./ancestor-or-self::'+notes_tag+'[1]')) != 0:
			section = elem.xpath('./ancestor-or-self::'+notes_tag+'[1]')[0]
		else:
			if len(elem.xpath('./ancestor-or-self::'+front_tag+'[1]')) != 0:
				section = elem.xpath('./ancestor-or-self::'+front_tag+'[1]')[0]
			elif len(elem.xpath('./ancestor-or-self::'+back_tag+'[1]')) != 0:
				section = elem.xpath('./ancestor-or-self::'+back_tag+'[1]')[0]
			else:
				section = root
	return et.getpath(section)


def find_container_title(elem, container_tag, root):
	"""
	params: elem -- an XML element
	params: container_tag -- the tag of the container element including the title
	return: title -- the tag of the element containing the title of the container
	"""
	et = ET.ElementTree(root)
	title = elem.xpath('./ancestor-or-self::'+container_tag+'[1]//'+title_tag)
	if len(elem.xpath('./ancestor-or-self::'+container_tag+'[1]//'+title_tag)) != 0:
		title = ET.tostring( elem.xpath('./ancestor-or-self::'+container_tag+'[1]//'+title_tag)[0], method="text", encoding='unicode', with_tail=False).strip()
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


#def get_rp_or_pl_path(elem, root):


# methods for serialising RDF
def elem_to_type(xpath):
	"""
	params: xpath -- XPath of an XML element to be mapped to RDF
	return: DOCO/DEO class
	"""
	pos = re.search( r"\[.*\]", xpath.rsplit('/', 1)[-1])
	if pos:
		elem = re.sub(r"\[.*\]" ,'', xpath.rsplit('/', 1)[-1])
	else:
		elem = xpath.rsplit('/', 1)[-1]
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


def find_de(de_id, graph):
	""" 
	params: de_id -- URI of the id
	params: graph -- RDF graph where to look in 
	return: list of URIs associated to the same id URI
	"""
	list_de = []
	for de, has_id, _id in graph.triples(( None,DATACITE.hasIdentifier,de_id )):
		list_de.append(de)
	return list_de	
									

def find_id(de_id, graph):
	""" 
	params: de_id -- value of an id
	params: graph -- RDF graph where to look in 
	return: the URI of the id associated to the value
	"""
	for o,has_val,val in graph.triples((None,LITERAL.hasLiteralValue,None)):
		if val.strip() == de_id.strip():
			return o


def find_be(be_text,graph):
	""" 
	params: be_text -- text of a bibliographic reference
	params: graph -- RDF graph where to look in 
	return: the URI of the be
	"""
	for o,has_val,val in graph.triples((None,C4O.hasContent,None)):
		if val.strip() == be_text.strip():
			return o