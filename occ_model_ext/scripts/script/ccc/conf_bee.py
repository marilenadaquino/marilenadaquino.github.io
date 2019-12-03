#!/usr/bin/env python
# -*- coding: utf-8 -*-
import uuid , os , re ,rdflib
from collections import defaultdict, Counter
from rdflib.namespace import XSD, RDF, RDFS, Namespace
from rdflib.term import Literal
from script.ocdm.graphlib import GraphEntity
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters
from lxml import etree as ET
from itertools import zip_longest

# ABBREVIATIONS
# elem 	= XML element
# be 	= bibliographic entry (URI)
# br 	= bibliographic resource (URI)
# rp 	= in-text reference pointer
# pl 	= list of pointers

# VARIABLES
abbreviations_list_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Abbreviations.txt'))

list_separators = [('[', ']'), ('[',']') , ('(', ')')]
rp_separators_in_list = [','.encode('utf-8'), '\u2013'.encode('utf-8'), '\u002D'.encode('utf-8'), ';'.encode('utf-8')] # first lists separator, second sequences separator

# XPATH
rp_path = './/xref[@rid = //ref/@id]'
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

# methods used by jats2oc
def sublist(groups):
	result_list = []
	sublist = []
	previous_number = None

	for current_number,path,val in groups:
		if previous_number is None or current_number > previous_number:
			sublist.append((current_number,path,val)) # still ascending, add to the current sublist
		else:
			result_list.append(sublist) # no longer ascending, add the current sublist
			sublist = [(current_number,path,val)] # start a new sublist
		previous_number = current_number
	if sublist: # add the last sublist, if there's anything there
		result_list.append(sublist)
	return result_list


def num(s):
    try:
        return int(s)
    except:
        return None


# methods for XML bibliographic entities
def get_be_id(elem):
	"""
	params: elem -- the XML element including the rp
	return: ID of the XML element including the be denoted by the rp
	"""
	if 'rid' in elem.attrib:
		return elem.get('rid')
	else:
		return elem.getparent().get('rid')


def find_xmlid(elem,root):
	"""
	params: elem -- the XML element OR the text value of the XML element including the rp
	params: root -- the root element of the XML document
	return: xmlid of the rp, i.e. of the bibentry denoted by the rp
	"""

	if isinstance(elem, str) == False:
		xmlid = get_be_id(elem)
	else:
		for ref in root.xpath('.//ref-list/ref'):
			label = ref.find('./label')
			if label:
				cleaned = ''.join(e for e in label.text if e.isalnum())
			else:
				cleaned = ''
			if elem == cleaned:
				xmlid = ref.get('id')
			else:
				xmlid = ''

	return xmlid


# methods for XML parsing
def get_text_before(elem):
	""" extract text before an xml element till the start tag of the parent element"""
	for item in elem.xpath("preceding-sibling::*//text()|preceding-sibling::text()"):
		item = item
		if item:
			yield item


def get_text_after(elem):
	""" extract text after an xml element till the end tag of the parent element"""
	for item in elem.xpath("following-sibling::*//text()|following-sibling::text()"):
		item = item
		if item:
			yield item


def xpath_sentence(elem, root, abb_list_path, parent=None):
	"""
	params: elem -- the rp
	params: root -- the root element of the XML document
	params: abb_list_path -- a txt file including the list of abbreviations for splitting sentences
	return: XPath of the sentence including the rp
	"""
	if parent:
		elem = elem.getparent()

	elem_value = ET.tostring(elem, method="text", encoding='unicode', with_tail=False)
	with open(abb_list_path, 'r') as f:
		abbreviations_list = [line.strip() for line in f.readlines() if not len(line) == 0]

	punkt_param = PunktParameters()
	punkt_param.abbrev_types = set(abbreviations_list)
	sentence_splitter = PunktSentenceTokenizer(punkt_param)

	string_before = "".join(get_text_before(elem))
	string_after = "".join(get_text_after(elem))
	# offset of sentence in the stringified parent element that include the rp
	# (0-based index transformed in 1-based index -- +1 -- to comply with XPath)
	if len(string_before) == 0:
		str_before = ''
		start_sent = 1
	elif len(string_before) != 0 and string_before.isspace():
		str_before = string_before
		start_sent = int([start for start, end in sentence_splitter.span_tokenize( string_before+first_el )][-1])+1
	else:
		str_before = sentence_splitter.tokenize( string_before+elem_value )[-1]
		start_sent = int([start for start, end in sentence_splitter.span_tokenize( string_before+elem_value )][-1] )+1
	if len(string_after) == 0 or string_after.isspace():
		str_after = ''
	else:
		str_after = sentence_splitter.tokenize( string_after )[0]
	len_sent = len(str_before+str_after)
	sent_xpath_function = 'substring(string('+ET.ElementTree(root).getpath(elem.getparent())+'),'+str(start_sent)+','+str(len_sent)+')'
	return sent_xpath_function


def xpath_list(elem, root, end_sep):
	"""
	params: elem -- the rp
	params: root -- the root element of the XML document
	params: strat_sep, end_sep -- separators of the substring representing a list
	return: XPath of the list including the rp
	"""
	et = ET.ElementTree(root)
	start_seps = [tup[0] for tup in list_separators if end_sep == tup[1]]
	if len(start_seps) != 0:
		start_sep = start_seps[0]
		elem_value = ET.tostring(elem, method="text", encoding='unicode', with_tail=False)
		string_before = "".join(get_text_before(elem)).strip()
		string_after = "".join(get_text_after(elem)).strip()

		if string_before.rfind(start_sep) != -1:
			start_sep_index = string_before.rfind(start_sep)+1
		else:
			start_sep_index = 1
		if string_after.find(end_sep) != -1:
			end_sep_index = string_after.find(end_sep)+1 # include the character
		else:
			end_sep_index = len(string_after)

		py_strin = (string_before[start_sep_index-1:]+elem_value+string_after[:end_sep_index]).strip().replace("\n","")
		len_list = len( string_before[start_sep_index:]+elem_value+string_after[:end_sep_index+1] )
		list_xpath_function = 'substring(string('+ET.ElementTree(root).getpath(elem.getparent())+'),'+str(start_sep_index)+','+str(len_list)+')'
	else: # parent element
		py_strin = (ET.tostring(elem.getparent(), method="text", encoding='unicode', with_tail=False)).strip().replace("\n","")
		list_xpath_function = et.getpath(elem.getparent())

	return [py_strin,list_xpath_function]


def xpath_list_between_elements(first_el, last_el, root):
	"""
	params: first_el -- first rp
	params: last_el -- last rp
	params: root -- the root element of the XML document
	return: xpath of the string including the pl that has no separators, nor parent element
	"""
	last_value = ET.tostring(last_el, method="text", encoding='unicode', with_tail=False)
	string_before = "".join(get_text_before(first_el))
	string_before_last = "".join(get_text_before(last_el))
	start_pl = int( len(string_before) )
	len_pl = int( len(string_before_last+last_value) ) - start_pl
	pl_xpath_function = 'substring(string('+ET.ElementTree(root).getpath(first_el.getparent())+'),'+str(start_pl)+','+str(len_pl)+')'
	return pl_xpath_function


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
	title_list = [ET.tostring( x, method="text", encoding='unicode', with_tail=False).strip() for x in elem.xpath('./ancestor::node()/'+title_tag)]
	if len(title_list) == 0:
		title_list = ''
	return title_list


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

# methods for XML/text cleaning
def clean(string):
	"""return: encoded stripped string"""
	return string.encode('utf-8').strip()


def clean_list(l):
	"""given a list of strings/elements returns a new list with stripped strings and elements"""
	# only strings
	new_l = []
	type_l = list({type(item) for item in l})
	if len(type_l) == 1 and type_l[0] == str:
		string_list = True
	else:
		string_list = False

	if string_list == True:
		for x in l:
			if len(x) != 0 and '\n' in x:
				y = x.replace("\n","")
				if len(y) != 0:
					new_l.append(y[:1])
			elif len(x) != 0 and '\n' not in x:
				new_l.append(x[:1])
	else:
		for x in l: # strings and elems
			if isinstance(x, str) == True and len(x) != 0 and '\n' in x:
				y = x.replace("\n","")
				if len(y) != 0:
					new_l.append(y[0])
			elif isinstance(x, str) == True and len(x) != 0 and '\n' not in x:
				new_l.append(x[0])
			else:
				new_l.append(x)
	return new_l


# methods for pl JSON
def rp_end_separator(rp_path_list):
	"""given a list of separators (in sentence) retrieve the most common separator"""
	rp_end_separator = clean_list(rp_path_list)
	rp_end_separator = [rp for rp in rp_end_separator if rp.encode('utf-8') not in rp_separators_in_list]
	rp_end_separator = Counter(rp_end_separator).most_common(1)
	return rp_end_separator


# methods for rp JSON
def rp_dict(xref , n_rp , xref_id , rp_string , rp_xpath , pl_string , pl_xpath, context_xpath, containers_title):
	""" create a dictionary w/ all the info on a rp to be refined and injected in a final JSON"""
	rp_dict = {}
	if xref is not None:
		rp_dict["xml_element"] = xref
	rp_dict["n_rp"] = n_rp
	rp_dict["xref_id"] = xref_id
	if rp_string is not None:
		rp_dict["rp_string"] = rp_string
	if pl_string is not None:
		rp_dict["pl_string"] = pl_string
	if rp_xpath is not None:
		rp_dict["rp_xpath"] = rp_xpath
	if pl_xpath is not None:
		rp_dict["pl_xpath"] = pl_xpath
	rp_dict["context_xpath"] = context_xpath
	rp_dict["containers_title"] = containers_title
	return rp_dict


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
