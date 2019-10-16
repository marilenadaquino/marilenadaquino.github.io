#!/usr/bin/env python
# -*- coding: utf-8 -*-
import script.ccc.conf as conf
import uuid , itertools , os , pprint
from lxml import etree as ET
from script.ocdm.graphlib import *
from rdflib import Graph, URIRef
from rdflib.namespace import XSD, RDF, RDFS, Namespace
from script.ocdm.conf import context_path as context_path
from itertools import groupby
from collections import defaultdict, Counter

pp = pprint.PrettyPrinter(indent=1)
class Jats2OC(object):

	def __init__(self, xml_doc):
		#self.xml_doc = xml_doc
		self.root = xml_doc
		self.xmlp = ET.XMLParser(encoding="utf-8")
		#self.tree = ET.parse(xml_doc, self.xmlp) # comm for run.py
		#self.root = self.tree.getroot() # comm for run.py
		self.et = ET.ElementTree(self.root)


	def check_inline_citation_style(self):
		"""return parents, childen and lists separators"""
		rp = conf.find_rp(self.root)
		
		# most common parent element
		rp_closest_parent = Counter([x.tag \
			for x in self.root.xpath('//'+rp+conf.rp_closest_parent) 
			if x.tag not in conf.parent_elements_names]).most_common(1)

		# most common end separator
		rp_end_separator = []
		for x in self.root.xpath('//'+rp+'/following-sibling::text()'):
			if len(x) != 0 and '\n' in x:
				y = x.replace("\n","")
				if len(y) != 0:
					rp_end_separator.append(y[:1])
			elif len(x) != 0 and '\n' not in x:
				rp_end_separator.append(x[:1])
					
		rp_end_separator = Counter(rp_end_separator).most_common(1)
		
		# most common child
		rp_children = Counter(x.tag for x in self.root.xpath('.//'+rp+conf.rp_child) ).most_common(1)
		return rp_closest_parent, rp_end_separator, rp_children


	def extract_intext_refs(self):
		""" parse the input xml_doc and return a list of lists (rp_groups)"""
		rp = conf.find_rp(self.root) # xpath of xref: either with @ref-type or without
		rp_closest_parent = self.check_inline_citation_style()[0]
		rp_end_separator = self.check_inline_citation_style()[1]
		rp_children = self.check_inline_citation_style()[2]
		
		# CASE 1 e.g. 30899012 sup/xref
		if len(rp_closest_parent) != 0 and len(rp_children) == 0: 
			rp_groups = [] 
			for group in self.root.xpath('.//'+rp_closest_parent[0][0]+'['+rp+']'):
				group_list = [x for x in group.xpath('./'+rp+' | ./'+rp+conf.rp_tail)]
				context = []
				for x in group_list:
					if isinstance(x, str) == True and len(x) != 0 and '\n' in x:
						y = x.replace("\n","")
						if len(y) != 0:
							context.append(y[0])
					elif isinstance(x, str) == True and '\n' not in x:
						context.append(x[0])
					else:
						context.append(x)	
				rp_groups.append(context)
			end_separator = rp_closest_parent[0][0]
		
		# CASE 2 e.g. xref/sup, random separators -- ATM we consider them ALL singleton, do not consider separators
		elif len(rp_closest_parent) == 0 and len(rp_children) != 0: 
			rp_groups = [[x] for x in self.root.xpath('.//'+rp+'/'+rp_children[0][0])]
			# TODO end_separator  
		
		# TODO
		# 2.1. xref/sup + element (sup) separators for lists
		# 2.2. e.g. 31537132 xref/sup, separators for sequences in text, but only one @rid in xref 
		# pl_string/xpath methods

		# CASE 3 e.g. 31531096 xref, separated by [],()
		elif len(rp_closest_parent) == 0 and len(rp_end_separator) != 0 and len(rp_children) == 0:
			cont = self.root.xpath('//'+rp+' | //'+rp+conf.rp_tail)
			context = []
			for x in cont:
				if isinstance(x, str) == True and len(x) != 0 and '\n' in x:
					y = x.replace("\n","")
					if len(y) != 0:
						context.append(y[0])
				elif isinstance(x, str) == True and '\n' not in x:
					context.append(x[0])
				else:
					context.append(x)		
			rp_and_separator = [conf.clean(elem).strip().decode('utf-8') if isinstance(elem, str) else elem for elem in context] # list of rp and separator
			rp_groups = [list(x[1]) for x in groupby(rp_and_separator, lambda x: x==rp_end_separator[0][0]) if not x[0]] # group rp by separator		
			end_separator = rp_end_separator[0][0]
		
		# CASE 4
		# TODO improve -- ATM we consider them ALL singleton, do not consider separators
		elif len(rp_closest_parent) == 0 and len(rp_end_separator) == 0 and len(rp_children) == 0:
			rp_groups = [[x] for x in self.root.xpath('.//'+rp)]
			
		# CASE 5 e.g. 31532339 [('attrib', 3)] [(')', 59)] [('italic', 32)] and sometimes no separator/parent
		# TODO improve -- ATM we consider them ALL singleton, do not consider separators
		elif len(rp_closest_parent) != 0 and len(rp_end_separator) != 0 and len(rp_children) != 0:
			rp_groups = [[x] for x in self.root.xpath('.//'+rp)]
		
		else:
			print('', rp_closest_parent, rp_end_separator, rp_children)
			
		
		# add group type rp/pl		
		for group in rp_groups:
			if conf.rp_separators_in_list[0].decode('utf-8') in group:
				group.append('list')
			elif conf.rp_separators_in_list[1].decode('utf-8') in group:
				group.append('sequence')
			else:
				group.append('singleton')
		
		# remove separators 
		groups = [list(i for i in j if i not in conf.rp_separators_in_list) for j in rp_groups]
		
		self.metadata = []
		for rp_group in groups:
			group = []
			if 'list' in rp_group: 
				for rp in rp_group:
					if (isinstance(rp, str) == False):
						rp_dict = {}
						rp_dict["xref"] = conf.find_xmlid(rp, self.root)
						rp_dict["rp_string"] =  ET.tostring(rp, method="text", encoding='unicode', with_tail=False)
						rp_dict["rp_xpath"] = self.et.getpath(rp)
						rp_dict["pl_string"] = conf.xpath_list(rp, self.root, end_separator)[0]
						rp_dict["pl_xpath"] = conf.xpath_list(rp, self.root, end_separator)[1]
						rp_dict["context_xpath"] = conf.xpath_sentence(rp, self.root, conf.abbreviations_list_path, end_separator)
						rp_dict["containers_title"] = conf.find_container_title(rp, conf.section_tag, self.root)
						group.append(rp_dict)
			if 'sequence' in rp_group:
				for rp in rp_group:
					if (isinstance(rp, str) == False):
						rp_dict = {}
						rp_dict["xref"] = conf.find_xmlid(rp, self.root)
						rp_dict["rp_string"] =  ET.tostring(rp, method="text", encoding='unicode', with_tail=False)
						rp_dict["rp_xpath"] = self.et.getpath(rp)
						rp_dict["pl_string"] = conf.xpath_list(rp, self.root, end_separator)[0]
						rp_dict["pl_xpath"] = conf.xpath_list(rp, self.root, end_separator)[1]
						rp_dict["context_xpath"] = conf.xpath_sentence(rp, self.root, conf.abbreviations_list_path, end_separator)
						rp_dict["containers_title"] = conf.find_container_title(rp, conf.section_tag, self.root)
						group.append(rp_dict)
						group.append("sequence")
			if 'singleton' in rp_group:
				for rp in rp_group:
					if isinstance(rp, str) == False:
						rp_dict = {}
						rp_dict["xref"] = conf.find_xmlid(rp, self.root)
						rp_dict["rp_string"] =  ET.tostring(rp, method="text", encoding='unicode', with_tail=False)
						rp_dict["rp_xpath"] = self.et.getpath(rp)
						rp_dict["context_xpath"] = conf.xpath_sentence(rp, self.root, conf.abbreviations_list_path)
						rp_dict["containers_title"] = conf.find_container_title(rp, conf.section_tag, self.root)
						group.append(rp_dict)
			self.metadata.append(group)
		
		# extend sequences
		for groups in self.metadata: # lists in list
			if 'sequence' in groups:
				range_values = [int(group['rp_string']) for group in groups if isinstance(group, str) == False]
				range_values.sort()
				for intermediate in range(int(range_values[0])+1,int(range_values[1])):
					rp_dict = {}
					rp_dict["xref"] = conf.find_xmlid(str(intermediate),self.root)
					rp_dict["pl_string"] = groups[0]['pl_string']
					rp_dict["pl_xpath"] = groups[0]['pl_xpath']
					rp_dict["context_xpath"] = groups[0]['context_xpath']
					rp_dict["containers_title"] = groups[0]['containers_title']
					groups.append(rp_dict)
				groups.remove("sequence")
		# remove the type of group
		self.metadata = [[rp for rp in rp_group if isinstance(rp, str) == False] for rp_group in self.metadata]
		return self.metadata


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
		# remove the graphset in parameter
		# TODO : disambiguation of citing br on OC -- crea tutto comunque
		# EXTEND https://github.com/opencitations/script/blob/master/spacin/resfinder.py, l. 153 onwards
		# if not in OC
		# crea il JSON come quello di Bee (reinventa la ruota -- e.g. http://opencitations.net/corpus)
		# dai tutto in pasto a https://github.com/opencitations/script/blob/master/spacin/crossrefproc.py
		# crp = CrossrefProcessor(base_iri, context_path, full_info_dir, json_object,
                            #                         ResourceFinder(ts_url=triplestore_url, default_dir=default_dir),
                            #                         ORCIDFinder(orcid_conf_path), items_per_file, supplier_prefix)
                            # result = crp.process()
        # ritorna un graphset da integrare
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
		
		# https://github.com/opencitations/script/blob/master/bee/epmcproc.py, l.170 linearizza la stringa della ref per la full-text search
		set_be = { (rp['be_id'],rp['xref']) for rp_group in self.data for rp in rp_group }
		for be_id,xref in set_be:	
			be_graph = self.graph.add_be("md", source_agent=None, source=None, res=None)
			be_graph.create_content(xref)
			self.BEgraph += be_graph.g
			
		# de
		# section
		# TODO 
		# add next -- make a new method in graphlib!

		set_sections_xpath = { (rp['section_xpath'],rp['containers_title']) for rp_group in self.data for rp in rp_group}
		for section_element, containers_title in set_sections_xpath:
			section_graph = self.graph.add_de("md", source_agent=None, source=None, res=None)
			section_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
			section_id.create_xpath(section_element)
			section_graph.create_discourse_element(conf.elem_to_type(section_element))
			section_graph.has_id(section_id) 
			if len(containers_title) != 0:
				section_graph.create_title(containers_title)
			citing_br_graph.contains_discourse_element(section_graph)
			self.DEgraph += section_graph.g
			self.IDgraph += section_id.g
			self.BRgraph += citing_br_graph.g

		# parent element
		# TODO 
		# add next
		set_parent_xpath = { (rp['rp_oc_parent_xpath'],rp['section_xpath']) for rp_group in self.data for rp in rp_group}
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
		set_sentences_xpath = { (rp['context_xpath'],rp['rp_oc_parent_xpath']) for rp_group in self.data for rp in rp_group}		
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
		set_chunk_xpath = { rp['pl_xpath'] for rp_group in self.data for rp in rp_group}
		for pl_xpath in set_chunk_xpath:
			rp_id_chunk = self.graph.add_id("md", source_agent=None, source=None, res=None)
			rp_id_chunk.create_xpath(pl_xpath)
			self.IDgraph += rp_id_chunk.g

		# rp
		# TODO 
		# add next? only when in list?
		# add denotes be
		set_rp_xpath = { ((	rp['rp_xpath'],rp['pl_xpath'],\
							rp['pl_string'],rp['context_xpath'],\
							rp['xref'], len(rp_group))) for rp_group in self.data for rp in rp_group}		
		for rp_xpath,pl_xpath,rp_string,context_xpath,xref,len_rp in set_rp_xpath:
			rp_graph = self.graph.add_rp("md", source_agent=None, source=None, res=None)	
			if rp_xpath != 'none': # intermediate rps in sequences do not have elem xpath, only chunk xpath
				rp_id = self.graph.add_id("md", source_agent=None, source=None, res=None)
				rp_id.create_xpath(rp_xpath) 
				self.IDgraph += rp_id.g
				rp_graph.has_id(rp_id)
			rp_chunk_id_uri = conf.find_id(pl_xpath,self.IDgraph)  # link rp to chunk_xpath
			rp_graph.has_id(rp_chunk_id_uri)
			rp_graph.create_content(rp_string)
			if len_rp == 1 :
				rp_sentence_id_uri = conf.find_id(context_xpath,self.IDgraph)
				rp_sentence = conf.find_de(rp_sentence_id_uri, sent_and_id_graph)
				rp_graph.has_context(rp_sentence[0])
				self.DEgraph += rp_graph.g
			be_uri = conf.find_be(xref,self.BEgraph)
			rp_graph.denotes(be_uri)
			self.DEgraph += rp_graph.g
			rp_and_id_graph += rp_graph.g

		# pl
		for rp_group in self.data:
			if len(rp_group) > 1 :
				pl_graph = self.graph.add_pl("md", source_agent=None, source=None, res=None)
				# lists have the same id of its elements (i.e. the xpath of the text chunk)
				pl_chunk_xpath = [rp['pl_xpath'] for rp in rp_group][0]
				rp_chunk_id_uri = conf.find_id(pl_chunk_xpath,self.IDgraph)		
				rp_uris = conf.find_de(rp_chunk_id_uri,rp_and_id_graph)
				for rp in rp_uris:
					pl_graph.contains_element(rp)			
				pl_graph.has_id(rp_chunk_id_uri) # associate the id to the list			
				pl_context_xpath = [rp['context_xpath'] for rp in rp_group][0]
				pl_sentence_id_uri = conf.find_id(pl_context_xpath,self.IDgraph)
				pl_sentences = conf.find_de(pl_sentence_id_uri, sent_and_id_graph)
				for pl_sentence in pl_sentences:
					pl_graph.has_context(pl_sentence)
				pl_value = [rp['pl_string'] for rp in rp_group][0]
				pl_graph.create_content(pl_value)
				self.DEgraph += pl_graph.g
		
		# citation for each rp
		# citation annotation

		# prepare a graphset?
		# provenance
		# storer to upload
