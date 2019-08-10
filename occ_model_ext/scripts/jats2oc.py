#!/usr/bin/env python
# -*- coding: utf-8 -*-
import conf
import uuid , itertools , os 
from lxml import etree as ET
from script.ocdm.graphlib import *
from rdflib import Graph, URIRef
from script.ocdm.conf import context_path as context_path
from itertools import groupby
from collections import defaultdict


class Jats2OC(object):
	
	def __init__(self, xml_doc):
		self.xml_doc = xml_doc
		self.xmlp = ET.XMLParser(encoding="utf-8")
		self.tree = ET.parse(xml_doc, self.xmlp)
		self.root = self.tree.getroot()
		self.et = ET.ElementTree(self.root)

		
	def extract_intext_refs(self):
		""" parse the input xml_doc and return a dictionary including: 
		article_doi, cited be_id, itr groupings, itr_closest_parent, itr_last_ancestor, xpath
		"""	
		context = self.root.xpath(conf.elem_text)

		# list of itr and separator ']' -- assuming ']' is always the separator of itr
		itr_separator = [conf.clean(elem[0]) if isinstance(elem, str) else elem for elem in context]
		
		# group itr by ']'
		itr_groups = [list(x[1]) for x in groupby(itr_separator, lambda x: x==conf.separator) if not x[0]]
		
		# store whether the group of xrefs is a sequence, a singleton, or a list
		for group in itr_groups:		
			if conf.prepositions[0] in group:
				group.append('list')
			elif conf.prepositions[1] in group:
				group.append('sequence')
			else:
				group.append('singleton')
		
		# remove separators from list
		groups = [list(i for i in j if i not in conf.prepositions) for j in itr_groups]

		# dict of all the metadata related to itr
		self.fullMetadata = [[{\
		'article_doi' : conf.find_citing_doi(self.root),\
		'be_id' : conf.find_cited_doi(xref, self.root), \
		'elem_xpath' : './'+self.et.getpath(xref), \
		'elem_sentence_xpath': conf.xpath_substring(xref, self.root, conf.abbreviations_list_path), \
		'elem_closest_parent_tag': xref.getparent().tag, \
		'elem_closest_parent_xpath': './'+self.et.getpath(xref.getparent()), \
		'elem_closest_parent_normalised_xpath': './'+conf.find_closest_parent(xref,self.root), \
		'elem_last_ancestor_xpath': './'+conf.find_container_xpath(xref, conf.section_tag, self.root), \
		'elem_last_ancestor_title': conf.find_container_title(xref, conf.section_tag, self.root), \
		'elem_value': xref.text} \
		if isinstance(xref, str) == False else xref for xref in xrefGroup] \
		for xrefGroup in groups]

		# extend sequences
		for groups in self.fullMetadata: # lists in list
			if 'sequence' in groups:
				rangeValues = []
				for group in groups: # dicts in list
					if isinstance(group, str) == False: # do not consider the string 'sequence'	
						rangeValues.append(group['elem_value'])
				rangeValues.sort()
				for intermediate in range(int(rangeValues[0])+1,int(rangeValues[1])):
					groups.append({\
						'article_doi':conf.find_citing_doi(self.root),\
						'be_id':conf.find_cited_doi(str(intermediate),self.root), \
						'elem_xpath': 'none', \
						'elem_sentence_xpath':groups[0]['elem_sentence_xpath'], \
						'elem_closest_parent_tag':groups[0]['elem_closest_parent_tag'], \
						'elem_closest_parent_xpath': groups[0]['elem_closest_parent_xpath'], \
						'elem_closest_parent_normalised_xpath': groups[0]['elem_closest_parent_normalised_xpath'], \
						'elem_last_ancestor_xpath': groups[0]['elem_last_ancestor_xpath'], \
						'elem_last_ancestor_title': groups[0]['elem_last_ancestor_title'],\
						'elem_value':str(intermediate) })
		
		# remove the type of xrefGroup
		self.newData = [[xref for xref in xrefGroup if isinstance(xref, str) == False] for xrefGroup in self.fullMetadata]
		
		# group by section container
		section = {}
		for xrefGroup in self.newData:				
			groups = groupby(xrefGroup, key=lambda x:x['elem_last_ancestor_xpath'])
			for x,y in groups:
				section.setdefault(x,[]).append(list(y))
		
		# group by normalised closest parent
		self.referencesTree = {}
		for sec, listOfLists in section.items():
			sect = {}
			for lis in listOfLists:
				parentGroups = groupby(lis, key=lambda x:x['elem_closest_parent_normalised_xpath'])
				for w,z in parentGroups:
					sect.setdefault(w,[]).append(list(z))
			self.referencesTree[sec] = sect

		return self.referencesTree


	def to_rdf(self, graph):
		""" process a JSON file to create a graph according to the OCC extended model"""
		self.data = self.extract_intext_refs()
		self.graph = graph

		self.IDgraph = Graph()
		self.DEgraph = Graph() 
		self.BRgraph = Graph()

		citing_doi = [y[0][0]['article_doi'] for k,v in self.data.items() for x,y in v.items()][0]
		
		# TODO check whether the br is already in the OCC
		# br
		self.br_graph = self.graph.add_br("md", source_agent=None, source=None, res=None) 

		# id 	
		citing_doi_graph = self.graph.add_id("md", source_agent=None, source=None, res=None)
		citing_doi_graph.create_doi(citing_doi)
		self.br_graph.has_id(citing_doi_graph)
		self.IDgraph += citing_doi_graph.g

		# de
		
		# section
		for section_element, parent in self.data.items():
			section_graph = self.graph.add_de("md", source_agent=None, source=None, res=None)
			section_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
			section_graph.create_discourse_element(conf.elem_to_type(section_element)) 
			# DOES NOT WORK with caption and tables!!!!
			section_graph.has_id(section_id)		
			self.br_graph.contains_discourse_element(section_graph) # sentences
			
			# DOES NOT WORK - does not catch all the de
			# ADD xpath to everything
			# parent element
			for parent_element, groups in parent.items():
				parent_graph = self.graph.add_de("md", source_agent=None, source=None, res=None)
				parent_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
				if conf.elem_to_type(parent_element) is not None:
					parent_graph.create_discourse_element(conf.elem_to_type(parent_element))	
				parent_graph.has_id(parent_id)
				section_graph.contains_discourse_element(parent_graph)
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
			# de_xpath.create_xpath(inTextRef['elem_sentence_xpath']) 
			# discourse_element.create_sentence()
			# discourse_element.has_id(de_xpath)		
			self.DEgraph += section_graph.g
			self.DEgraph += parent_graph.g
			self.IDgraph += section_id.g
			self.IDgraph += parent_id.g
		
		self.BRgraph += self.br_graph.g
		
		# storer to upload




# TODO 

# extract_intext_refs
# check whether titles are correctly extracted

# to_rdf
# remove the graphs and the serialisation
# does not find the context file
# how to put everything in the br graph? 
# does a br include par, secs, sentences etc. at the same level frbr:part? or only nested frbr:part
# change the path of context.json 
