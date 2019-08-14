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
		""" parse the input xml_doc and return a list of lists (rp_groups) including:
		article_doi, cited be_id, rp groupings, rp_closest_parent, rp_last_ancestor, xpath
		"""
		context = self.root.xpath(conf.elem_text)

		# list of rp and separator
		rp_separator = [conf.clean(elem[0]) if isinstance(elem, str) else elem for elem in context]

		# group rp by separator -- assuming the separator is always the same
		rp_groups = [list(x[1]) for x in groupby(rp_separator, lambda x: x==conf.separator) if not x[0]]

		for group in rp_groups:
			if conf.rp_separators[0] in group:
				group.append('list')
			elif conf.rp_separators[1] in group:
				group.append('sequence')
			else:
				group.append('singleton')

		# remove separators 
		groups = [list(i for i in j if i not in conf.rp_separators) for j in rp_groups]

		# metadata related to rp
		self.full_metadata = [[{\
			'article_doi' : conf.find_citing_doi(self.root),\
			'be_id' : conf.find_cited_doi(xref, self.root)[0], \
			'be_text' : conf.find_cited_doi(xref, self.root)[1], \
			'elem_xpath' : './'+self.et.getpath(xref), \
			'elem_chunk_value': conf.xpath_list(xref, self.root, conf.start_sep, conf.end_sep)[0] ,\
			'elem_chunk_xpath': conf.xpath_list(xref, self.root, conf.start_sep, conf.end_sep)[1] ,\
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
						'be_id':conf.find_cited_doi(str(intermediate),self.root)[0], \
						'be_text':conf.find_cited_doi(str(intermediate),self.root)[1],\
						'elem_xpath': 'none', \
						'elem_chunk_value': groups[0]['elem_chunk_value'],\
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
		self.BEgraph = Graph()
		sent_and_id_graph = Graph()
		rp_and_id_graph = Graph()
		cited_doi_graph = Graph()

		# br
		# TODO : disambiguation of citing br on OC
		# if not in OC
		# add id (all of them?), type, title, part of, cites, publication date, embodied as XML, number?, 
		# edition, part (references?), contributor
		# add pmid, pmcid?

		citing_doi = [rp['article_doi'] for rp_group in self.data for rp in rp_group][0]
		citing_br_graph = self.graph.add_br("md", source_agent=None, source=None, res=None)
		citing_doi_graph = self.graph.add_id("md", source_agent=None, source=None, res=None)
		citing_doi_graph.create_doi(citing_doi)
		citing_br_graph.has_id(citing_doi_graph)
		self.IDgraph += citing_doi_graph.g

		# be 
		# TODO 
		# disambiguation of be/br on OC
		# add referenced br, id of br -- distiguish doi from pmid. IN WHICH GRAPH?
		set_be = { (rp['be_id'],rp['be_text']) for rp_group in self.data for rp in rp_group }
		for be_id,be_text in set_be:	
			be_graph = self.graph.add_be("md", source_agent=None, source=None, res=None)
			be_graph.create_content(be_text)
			self.BEgraph += be_graph.g
			
		# de
		# section
		# TODO 
		# add next
		set_sections_xpath = { (rp['elem_last_ancestor_xpath'],rp['elem_last_ancestor_title']) for rp_group in self.data for rp in rp_group}
		for section_element, section_title in set_sections_xpath:
			section_graph = self.graph.add_de("md", source_agent=None, source=None, res=None)
			section_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
			section_id.create_xpath(section_element)
			section_graph.create_discourse_element(conf.elem_to_type(section_element))
			section_graph.has_id(section_id) 
			if len(section_title) != 0:
				section_graph.create_title(section_title)
			citing_br_graph.contains_discourse_element(section_graph)
			self.DEgraph += section_graph.g
			self.IDgraph += section_id.g
			self.BRgraph += citing_br_graph.g

		# parent element
		# TODO 
		# add next
		set_parent_xpath = { (rp['elem_closest_parent_normalised_xpath'],rp['elem_last_ancestor_xpath']) for rp_group in self.data for rp in rp_group}
		for parent_element,section_element in set_parent_xpath:
			parent_graph = self.graph.add_de("md", source_agent=None, source=None, res=None)
			parent_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
			parent_id.create_xpath(parent_element)
			if conf.elem_to_type(parent_element):
				parent_graph.create_discourse_element(conf.elem_to_type(parent_element))
			parent_graph.has_id(parent_id)
			section_elem_id = conf.find_id(section_element,self.IDgraph)
			section_elem_uri = conf.find_de(section_elem_id, self.DEgraph)
			parent_graph.contained_in_discourse_element(section_elem_uri[0])
			self.DEgraph += parent_graph.g
			self.IDgraph += parent_id.g	

		# sentence
		# TODO 
		# add next?
		set_sentences_xpath = { (rp['elem_sentence_xpath'],rp['elem_closest_parent_normalised_xpath']) for rp_group in self.data for rp in rp_group}		
		for sentence,parent_elem in set_sentences_xpath:
			sentence_graph = self.graph.add_de("md", source_agent=None, source=None, res=None)
			sentence_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
			sentence_id.create_xpath(sentence)
			if conf.table_tag in sentence: # the only case where we have a text chunk rather than a sentence
				sentence_graph.create_text_chunk()
			else:
				sentence_graph.create_sentence()
			sentence_graph.has_id(sentence_id)
			sent_and_id_graph += sentence_graph.g + sentence_id.g
			parent_elem_id = conf.find_id(parent_elem,self.IDgraph)
			parent_elem_uri = conf.find_de(parent_elem_id, self.DEgraph)
			sentence_graph.contained_in_discourse_element(parent_elem_uri[0])
			self.DEgraph += sentence_graph.g
			self.IDgraph += sentence_id.g	

		# rp_id_chunk 
		set_chunk_xpath = { rp['elem_chunk_xpath'] for rp_group in self.data for rp in rp_group}
		for elem_chunk_xpath in set_chunk_xpath:
			rp_id_chunk = self.graph.add_id("md", source_agent=None, source=None, res=None)
			rp_id_chunk.create_xpath(elem_chunk_xpath)
			self.IDgraph += rp_id_chunk.g

		# rp
		# TODO 
		# add next? only when in list?
		# add denotes be
		set_rp_xpath = { ((	rp['elem_xpath'],rp['elem_chunk_xpath'],\
							rp['elem_chunk_value'],rp['elem_sentence_xpath'],\
							rp['be_text'], len(rp_group))) for rp_group in self.data for rp in rp_group}		
		for elem_xpath,elem_chunk_xpath,elem_value,elem_sentence_xpath,be_text,len_rp in set_rp_xpath:
			rp_graph = self.graph.add_rp("md", source_agent=None, source=None, res=None)	
			if elem_xpath != 'none': # intermediate rps in sequences do not have elem xpath, only chunk xpath
				rp_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
				rp_id.create_xpath(elem_xpath) 
				self.IDgraph += rp_id.g
				rp_graph.has_id(rp_id)
			rp_chunk_id_uri = conf.find_id(elem_chunk_xpath,self.IDgraph)  # link rp to chunk_xpath
			rp_graph.has_id(rp_chunk_id_uri)
			rp_graph.create_content(elem_value)
			if len_rp == 1 :
				rp_sentence_id_uri = conf.find_id(elem_sentence_xpath,self.IDgraph)
				rp_sentence = conf.find_de(rp_sentence_id_uri, sent_and_id_graph)
				rp_graph.has_context(rp_sentence[0])
				self.DEgraph += rp_graph.g
			be_uri = conf.find_be(be_text,self.BEgraph)
			rp_graph.denotes(be_uri)
			self.DEgraph += rp_graph.g
			rp_and_id_graph += rp_graph.g

		# pl
		for rp_group in self.data:
			if len(rp_group) > 1 :
				pl_graph = self.graph.add_pl("md", source_agent=None, source=None, res=None)
				# lists have the same id of its elements (i.e. the xpath of the text chunk)
				pl_chunk_xpath = [rp['elem_chunk_xpath'] for rp in rp_group][0]
				rp_chunk_id_uri = conf.find_id(pl_chunk_xpath,self.IDgraph)		
				rp_uris = conf.find_de(rp_chunk_id_uri,rp_and_id_graph)
				for rp in rp_uris:
					pl_graph.contains_element(rp)			
				pl_graph.has_id(rp_chunk_id_uri) # associate the id to the list			
				pl_sentence_xpath = [rp['elem_sentence_xpath'] for rp in rp_group][0]
				pl_sentence_id_uri = conf.find_id(pl_sentence_xpath,self.IDgraph)
				pl_sentences = conf.find_de(pl_sentence_id_uri, sent_and_id_graph)
				for pl_sentence in pl_sentences:
					pl_graph.has_context(pl_sentence)
				pl_value = [rp['elem_chunk_value'] for rp in rp_group][0]
				pl_graph.create_content(pl_value)
				self.DEgraph += pl_graph.g
		
		# citation for each rp
		# citation annotation

		# prepare a graphset?
		# provenance
		# storer to upload
