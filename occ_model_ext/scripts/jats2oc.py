#!/usr/bin/env python
# -*- coding: utf-8 -*-
import conf
import uuid , itertools , os , pprint
from lxml import etree as ET
from script.ocdm.graphlib import *
from rdflib import Graph, URIRef
from rdflib.namespace import XSD, RDF, RDFS, Namespace
from script.ocdm.conf import context_path as context_path
from itertools import groupby
from collections import defaultdict

pp = pprint.PrettyPrinter(indent=1)
class Jats2OC(object):

	def __init__(self, xml_doc):
		self.xml_doc = xml_doc
		self.xmlp = ET.XMLParser(encoding="utf-8")
		self.tree = ET.parse(xml_doc, self.xmlp)
		self.root = self.tree.getroot()
		self.et = ET.ElementTree(self.root)


	def extract_intext_refs(self):
		""" parse the input xml_doc and return a list of lists (itr_groups) including:
		article_doi, cited be_id, itr groupings, itr_closest_parent, itr_last_ancestor, xpath
		"""
		context = self.root.xpath(conf.elem_text)

		# list of itr and separator
		itr_separator = [conf.clean(elem[0]) if isinstance(elem, str) else elem for elem in context]

		# group itr by separator -- assuming the separator is always the same
		itr_groups = [list(x[1]) for x in groupby(itr_separator, lambda x: x==conf.separator) if not x[0]]

		for group in itr_groups:
			if conf.itr_separators[0] in group:
				group.append('list')
			elif conf.itr_separators[1] in group:
				group.append('sequence')
			else:
				group.append('singleton')

		# remove separators 
		groups = [list(i for i in j if i not in conf.itr_separators) for j in itr_groups]

		# metadata related to itr
		self.full_metadata = [[{\
			'article_doi' : conf.find_citing_doi(self.root),\
			'be_id' : conf.find_cited_doi(xref, self.root), \
			'elem_xpath' : './'+self.et.getpath(xref), \
			'elem_chunk_xpath': conf.xpath_list(xref, self.root, conf.start_sep, conf.end_sep) ,\
			'elem_sentence_xpath': conf.xpath_sentence(xref, self.root, conf.abbreviations_list_path), \
			'elem_closest_parent_xpath': './'+self.et.getpath(xref.getparent()), \
			'elem_closest_parent_normalised_xpath': './'+conf.find_closest_parent(xref,self.root), \
			'elem_last_ancestor_xpath': './'+conf.find_container_xpath(xref, conf.section_tag, self.root), \
			'elem_last_ancestor_title': conf.find_container_title(xref, conf.section_tag, self.root), \
			'elem_value': xref.text} \
			if isinstance(xref, str) == False else xref for xref in xrefGroup] \
			for xrefGroup in groups]

		# extend sequences
		for groups in self.full_metadata: # lists in list
			if 'sequence' in groups:
				range_values = [group['elem_value'] for group in groups if isinstance(group, str) == False]
				range_values.sort()
				for intermediate in range(int(range_values[0])+1,int(range_values[1])):
					groups.append({\
						'article_doi':conf.find_citing_doi(self.root),\
						'be_id':conf.find_cited_doi(str(intermediate),self.root), \
						'elem_xpath': 'none', \
						'elem_chunk_xpath': groups[0]['elem_chunk_xpath'],\
						'elem_sentence_xpath':groups[0]['elem_sentence_xpath'], \
						'elem_closest_parent_xpath': groups[0]['elem_closest_parent_xpath'], \
						'elem_closest_parent_normalised_xpath': groups[0]['elem_closest_parent_normalised_xpath'], \
						'elem_last_ancestor_xpath': groups[0]['elem_last_ancestor_xpath'], \
						'elem_last_ancestor_title': groups[0]['elem_last_ancestor_title'],\
						'elem_value':str(intermediate) })

		# remove the type of group
		self.full_metadata = [[xref for xref in xrefGroup if isinstance(xref, str) == False] for xrefGroup in self.full_metadata]
		return self.full_metadata


	def to_rdf(self, graph): 
		""" process a JSON file to create a graph according to the OCC extended model"""
		self.data = self.extract_intext_refs()
		self.graph = graph
		self.IDgraph = Graph()
		self.DEgraph = Graph()
		self.BRgraph = Graph()
		sent_and_id_graph = Graph()
		rp_and_id_graph = Graph()
		

		# br
		# TODO : disambiguation on OC
		# if not in OC
		# add id (all of them?), type, title, part of, cites, publication date, embodied as XML, number?, 
		# edition, part (references?), contributor
		# add citations

		citing_doi = [itr['article_doi'] for itr_group in self.data for itr in itr_group][0]
		self.br_graph = self.graph.add_br("md", source_agent=None, source=None, res=None)
		citing_doi_graph = self.graph.add_id("md", source_agent=None, source=None, res=None)
		citing_doi_graph.create_doi(citing_doi)
		self.br_graph.has_id(citing_doi_graph)
		self.IDgraph += citing_doi_graph.g

		# de
		# rp_id_chunk 
		set_chunk_xpath = { itr['elem_chunk_xpath'] for itr_group in self.data for itr in itr_group}
		for elem_chunk_xpath in set_chunk_xpath:
			rp_id_chunk = self.graph.add_id("md", source_agent=None, source=None, res=None)
			rp_id_chunk.create_xpath(elem_chunk_xpath)
			self.IDgraph += rp_id_chunk.g

		# rp
		set_itr_xpath = { ((itr['elem_xpath'],itr['elem_chunk_xpath'])) for itr_group in self.data for itr in itr_group}		
		for elem_xpath,elem_chunk_xpath in set_itr_xpath:
			rp_graph = self.graph.add_rp("md", source_agent=None, source=None, res=None)	
			if elem_xpath != 'none': # intermediate itrs in sequences do not have elem xpath, only chunk xpath
				rp_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
				rp_id.create_xpath(elem_xpath) 
				self.IDgraph += rp_id.g
				rp_graph.has_id(rp_id)
			rp_chunk_id_uri = conf.find_id(elem_chunk_xpath,self.IDgraph)  # link itr to chunk_xpath
			rp_graph.has_id(rp_chunk_id_uri)
			self.DEgraph += rp_graph.g

			# TODO 
			# add value
			# add next?
			# add denotes be
			rp_and_id_graph += rp_graph.g #for reconciling lists

		# pl
		for itr_group in self.data:
			if len(itr_group) > 1 :
				pl_graph = self.graph.add_pl("md", source_agent=None, source=None, res=None)
				# lists have the same id of its elements (i.e. the xpath of the text chunk)
				pl_chunk_xpath = [itr['elem_chunk_xpath'] for itr in itr_group][0]
				rp_chunk_id_uri = conf.find_id(pl_chunk_xpath,self.IDgraph)		
				rp_uris = conf.find_de(rp_chunk_id_uri,rp_and_id_graph)
				for rp in rp_uris:
					pl_graph.contains_element(rp)			
				pl_graph.has_id(rp_chunk_id_uri) # associate the id to the list
				
				self.DEgraph += pl_graph.g
				
				# TODO 
				# add value

		# sentence
		set_sentences_xpath = { itr['elem_sentence_xpath'] for itr_group in self.data for itr in itr_group}		
		for sentence in set_sentences_xpath:
			sentence_graph = self.graph.add_de("md", source_agent=None, source=None, res=None)
			sentence_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
			sentence_id.create_xpath(sentence)
			sentence_graph.create_sentence()
			sentence_graph.has_id(sentence_id)
			sent_and_id_graph += sentence_graph.g + sentence_id.g
			self.DEgraph += sentence_graph.g
			self.IDgraph += sentence_id.g	
			
			# TODO 
			# add next
			# add context of list in sentence
			# add context of itr in sentence

		# parent element
		set_parent_xpath = { itr['elem_closest_parent_normalised_xpath'] for itr_group in self.data for itr in itr_group}
		for parent_element in set_parent_xpath:
			parent_graph = self.graph.add_de("md", source_agent=None, source=None, res=None)
			parent_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
			parent_id.create_xpath(parent_element)
			if conf.elem_to_type(parent_element):
				parent_graph.create_discourse_element(conf.elem_to_type(parent_element))
			parent_graph.has_id(parent_id)
			self.DEgraph += parent_graph.g
			self.IDgraph += parent_id.g	

			# TODO 
			# add part (sentence)
			# add next

		# section
		set_sections_xpath = { itr['elem_last_ancestor_xpath'] for itr_group in self.data for itr in itr_group}
		for section_element in set_sections_xpath:
			section_graph = self.graph.add_de("md", source_agent=None, source=None, res=None)
			section_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
			section_id.create_xpath(section_element)
			section_graph.create_discourse_element(conf.elem_to_type(section_element))
			section_graph.has_id(section_id)
			self.br_graph.contains_discourse_element(section_graph) # sentences
			self.DEgraph += section_graph.g
			self.IDgraph += section_id.g
			self.BRgraph += self.br_graph.g
			
			# TODO 
			# add title
			# add part (parent)
			# add next
		
		# be 
		# TODO : disambiguation on OC
		# add id, text, references br, 
		

		# citation

		# citation annotation

		# prepare a graphset?
		# storer to upload
