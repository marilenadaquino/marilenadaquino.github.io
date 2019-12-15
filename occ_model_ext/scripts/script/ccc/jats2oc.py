#!/usr/bin/env python
# -*- coding: utf-8 -*-
import script.ccc.conf_bee as conf
import uuid , itertools , os , pprint ,re , string
from lxml import etree as ET
from itertools import groupby
from collections import defaultdict, Counter

from script.spacin.formatproc import FormatProcessor
from script.ocdm.graphlib import *
from script.ocdm.conf import context_path as context_path


pp = pprint.PrettyPrinter(indent=1)
class Jats2OC(object):

	def __init__(self, xml_doc):
		#self.xml_doc = xml_doc
		self.root = xml_doc
		self.xmlp = ET.XMLParser(encoding="utf-8")
		#self.tree = ET.parse(xml_doc, self.xmlp) # comm for run.py
		#self.root = self.tree.getroot() # comm for run.py
		self.et = ET.ElementTree(self.root)


	def extract_intext_refs(self):
		"""process a XML file and return a list of lists of dictionaries"""
		self.metadata = []
		n_rp = 100 # start from 100 to include floating numbers (corresponding to rp extracted from sequences in post process)
		rp_list = []

		# rp
		for xref in self.root.xpath(conf.rp_path):
			n_rp += 100
			xref_id = xref.get('rid')
			xref_text = xref.text
			if xref_text:
				rp_string = xref_text.strip().replace('\n','')
			else:
				xref_text = ET.tostring(xref, method="text", encoding='unicode', with_tail=False)
				rp_string = xref_text.strip().replace('\n','')
			rp_xpath = self.et.getpath(xref)
			parent = None if xref.getparent().tag in conf.parent_elements_names else xref.getparent().tag
			context_xpath = conf.xpath_sentence(xref, self.root, conf.abbreviations_list_path, parent)
			containers_title = conf.find_container_title(xref, conf.section_tag, self.root)
			pl_string , pl_xpath = None , None

			if len(list(xref)) == 0: # no children
				seq = xref_text.encode('utf-8').split('\u2013'.encode('utf-8'))
				if len(seq) == 2 and conf.num(seq[0]) and conf.num(seq[1]): # more digits <xref rid="CIT0001">1-3</xref>
					pl_string , pl_xpath = rp_string , rp_xpath
					rp_dict = conf.rp_dict(xref , n_rp , xref_id , rp_string , rp_xpath , pl_string , pl_xpath, context_xpath, containers_title)
					rp_list.append(rp_dict)
					range_values = [int( val ) for val in seq if val.isdigit() ]
					if len(range_values) == 2:
						range_values.sort()
						for intermediate in range(int(range_values[0])+1,int(range_values[1])+1 ): # 2nd to last included
							n_rp += 100
							xref_id = conf.find_xmlid(str(intermediate),self.root)
							rp_dict_i = conf.rp_dict(xref , n_rp , xref_id , None , None , pl_string , rp_xpath, context_xpath, containers_title)
							rp_list.append(rp_dict_i)
					else: # no digits
						pass
				else: # simple string <xref rid="CIT0001">1</xref>
					rp_dict = conf.rp_dict(xref , n_rp , xref_id , rp_string , rp_xpath , None , None, context_xpath, containers_title)
					rp_list.append(rp_dict)
			else: # children
				if xref[0].tail:
					tail = (xref[0].tail).strip().replace('\n','')
				else:
					tail = ''
				rp_string = ET.tostring(xref, method="text", encoding='unicode', with_tail=False).strip().replace('\n','')

				if len(xref_text.strip().replace('\n','')) != 0 or len(tail) != 0: # Amass <italic>et al.</italic>, 2000
					rp_dict = conf.rp_dict(xref , n_rp , xref_id , rp_string , rp_xpath , None , None, context_xpath, containers_title)
					rp_list.append(rp_dict)

				elif len(xref_text.strip().replace('\n','')) == 0 and len(tail) == 0: # xref/sup
					if xref[0].text:
						seq = ((xref[0].text).strip().replace('\n','')).split('\u2013')
					else:
						seq = ((ET.tostring(xref[0], method="text", encoding='unicode', with_tail=False)).strip().replace('\n','')).split('\u2013')
					if len(seq) == 2 and conf.num(seq[0]) and conf.num(seq[1]): # more digits <xref rid="CIT0001"><sup>1-3</sup></xref>
						pl_string , pl_xpath = rp_string , rp_xpath
						rp_dict = conf.rp_dict(xref , n_rp , xref_id , rp_string , rp_xpath , pl_string , pl_xpath, context_xpath, containers_title)
						rp_list.append(rp_dict)

						range_values = [int( val ) for val in seq if val.isdigit() ]
						if len(range_values) != 0:
							range_values.sort()
							for intermediate in range(int(range_values[0])+1,int(range_values[1])+1 ): # 2nd to last included
								n_rp += 100
								xref_id = conf.find_xmlid(str(intermediate),self.root)
								rp_dict_i = conf.rp_dict(xref , n_rp , xref_id , None , None , pl_string , pl_xpath, context_xpath, containers_title)
								rp_list.append(rp_dict_i)
					else: # simple string
						rp_string = ET.tostring(xref[0], method="text", encoding='unicode', with_tail=False).strip().replace('\n','')
						rp_dict = conf.rp_dict(xref , n_rp , xref_id , rp_string , rp_xpath , pl_string , pl_xpath, context_xpath, containers_title)
						rp_list.append(rp_dict)

		sort_xpaths = [rp["rp_xpath"] if "rp_xpath" in rp.keys() else rp["pl_xpath"] for rp in rp_list ]

		# pl
		# 1. pl in parent element
		parent_pl_set = list({ (rp["xml_element"].getparent(), self.et.getpath(rp["xml_element"].getparent()) ) \
			for rp in rp_list if rp["xml_element"].getparent().tag not in conf.parent_elements_names})

		for parent_el, parent_el_path  in parent_pl_set: # sup w/ comma or dash separated xref [TEST 4]
			pl_string = ET.tostring(parent_el, method="text", encoding='unicode', with_tail=False).strip().replace('\n','')
			pl_xpath = self.et.getpath(parent_el)
			context_xpath = conf.xpath_sentence(parent_el, self.root, conf.abbreviations_list_path, None)
			containers_title = conf.find_container_title(parent_el, conf.section_tag, self.root)
			parent_el_list = []

			for xref_el in parent_el:
				n_rpn = [rp["n_rp"] for rp in rp_list if rp["xml_element"] == xref_el ][0]
				tail = (xref_el.tail)
				if tail and '\u2013' in tail.strip().replace('\n',''):
					end_seq = xref_el.getnext()
					if end_seq.tag == 'xref' and ( (xref_el.text).isdigit() and (end_seq.text).isdigit() ):
						for intermediate in range(int(xref_el.text)+1,int(end_seq.text) ):
							n_rpn += 1
							xref_id = conf.find_xmlid(str(intermediate),self.root)
							rp_dict_i = conf.rp_dict(xref_el , n_rpn , xref_id , None , None , pl_string , pl_xpath, context_xpath, containers_title)
							rp_list.append(rp_dict_i)
				rp_list = sorted(rp_list, key=lambda rp: int(rp["n_rp"]))
				for rp in rp_list:
					if xref_el == rp["xml_element"]:
						rp["pl_string"] = pl_string
						rp["pl_xpath"] = pl_xpath
						parent_el_list.append(rp)
						rp_list.remove(rp)
			self.metadata.append(parent_el_list)

		# 2. pl in xref (already found)
		pl_set = {rp["pl_xpath"] for rp in rp_list if "pl_xpath" in rp.keys()}
		pl_dict = {pl : [rp for rp in rp_list if "pl_xpath" in rp.keys() and rp["pl_xpath"] == pl] for pl in pl_set}
		for pl, pl_list in pl_dict.items():
			self.metadata.append(pl_list)

		# 3. pl in separators
		sentences_set = {rp["context_xpath"] for rp in rp_list}
		sentences_dict = {sent : [rp for rp in rp_list if rp["context_xpath"] == sent] for sent in sentences_set}
		all_groups = []
		for sent, xref_list in sentences_dict.items():
			if len(xref_list) == 1: # rp in sentence (do not care about separator)
				self.metadata.append(xref_list)
				for rp in rp_list:
					if rp == xref_list[0]:
						rp_list.remove(rp)

			if len(xref_list) > 1: # rp and pl in sentence
				xref_in_sent = [rp["rp_xpath"] for rp in xref_list if "rp_xpath" in rp.keys()]
				tails = [self.root.xpath('/'+xref+conf.rp_tail)[0] if self.root.xpath('/'+xref+conf.rp_tail) else '' for xref in xref_in_sent]

				end_separator = conf.rp_end_separator(tails)

				if len(end_separator) != 0 and end_separator[0][0] not in list(string.ascii_letters) and end_separator[0][0] not in list(string.digits): # separators
					context = [conf.clean_list(self.root.xpath('/'+xref+' | /'+xref+conf.rp_tail)) for xref in xref_in_sent]
					context = [y for x in context for y in x]
					rp_and_separator = [conf.clean(elem).strip().decode('utf-8') if isinstance(elem, str) else elem for elem in context] # list of rp and separator
					rp_groups = [list(x[1]) for x in groupby(rp_and_separator, lambda x: x==end_separator[0][0]) if not x[0]] # group rp by separator
					# add group type rp/pl -- TODO when it's both a list and a sequence	e.g. 31243649
					for group in rp_groups:
						if conf.rp_separators_in_list[0].decode('utf-8') in group \
						or conf.rp_separators_in_list[3].decode('utf-8') in group:
							group.append('list')
						elif conf.rp_separators_in_list[1].decode('utf-8') in group \
						or conf.rp_separators_in_list[2].decode('utf-8') in group:
							group.append('sequence')
						else:
							group.append('singleton')

					# remove separators
					groups = [list(i for i in j if i not in conf.rp_separators_in_list) for j in rp_groups]
					for group in groups:
						if 'singleton' in group:
							singleton_path = self.et.getpath(group[0])
							rp_dict = [rp for rp in rp_list if "rp_xpath" in rp.keys() and rp["rp_xpath"] == singleton_path]
							for rp in rp_dict:
								self.metadata.append(rp_dict)
								rp_list.remove(rp)

						if 'list' in group:
							elems_path = [self.et.getpath(elem) for elem in group if isinstance(elem, str) == False]
							rp_dicts = [rp for rp in rp_list for elem in elems_path if "rp_xpath" in rp.keys() and rp["rp_xpath"] == elem]
							for rp in rp_dicts:
								rp["pl_string"] = conf.xpath_list(rp["xml_element"], self.root, end_separator[0][0])[0]
								rp["pl_xpath"] = conf.xpath_list(rp["xml_element"], self.root, end_separator[0][0])[1]
							self.metadata.append(rp_dicts)
							for rp in rp_dicts:
								rp_list.remove(rp)

						if 'sequence' in group:
							elems_path = [self.et.getpath(elem) for elem in group if isinstance(elem, str) == False]
							rp_dicts = [rp for rp in rp_list for elem in elems_path if "rp_xpath" in rp.keys() and rp["rp_xpath"] == elem]
							for rp in rp_dicts:
								rp["pl_string"] = conf.xpath_list(rp["xml_element"], self.root, end_separator[0][0])[0]
								rp["pl_xpath"] = conf.xpath_list(rp["xml_element"], self.root, end_separator[0][0])[1]
							range_values = [int(rp["rp_string"]) for rp in rp_list \
								for elem in elems_path if "rp_xpath" in rp.keys() \
								and rp["rp_xpath"] == elem and rp["rp_string"].isdigit()]
							if len(range_values) != 0:
								range_values.sort()
								n_rpn = rp_dicts[0]["n_rp"]
								for intermediate in range(int(range_values[0])+1,int(range_values[1]) ):
									n_rpn += 1 # TODO change
									xref_id = conf.find_xmlid(str(intermediate),self.root)
									rp = rp_dicts[0]["xml_element"]
									pl_string = conf.xpath_list(rp, self.root, end_separator[0][0])[0]
									pl_xpath = conf.xpath_list(rp, self.root, end_separator[0][0])[1]
									context_xpath = rp_dicts[0]["context_xpath"]
									containers_title = rp_dicts[0]["containers_title"]
									rp_dict_i = conf.rp_dict(None , n_rpn , xref_id , None , None , pl_string , pl_xpath, context_xpath, containers_title)
									rp_dicts.append(rp_dict_i)
									rp_dicts = sorted(rp_dicts, key=lambda rp: int(rp["n_rp"]))

							self.metadata.append(rp_dicts)
							for rp in rp_dicts:
								if rp in rp_list:
									rp_list.remove(rp)

				else: # no separator
					groups , lonely = [],[]
					for xref in xref_in_sent: # exception xref/sup + sup=, + xref/sup
						if len(self.root.xpath('/'+xref+'/following-sibling::*[1][contains(text(), ",")]')) != 0 \
							and len(self.root.xpath('/'+xref+'/preceding-sibling::*[1][contains(text(), ",")]')) == 0:
							if self.root.xpath('/'+xref+'/sup/text()'):
								groups.append(["1",xref, (self.root.xpath('/'+xref+'/sup/text()')[0]) ]) # start
							else:
								groups.append(["1",xref, (self.root.xpath('/'+xref+'/text()')[0]) ])
						elif len(self.root.xpath('/'+xref+'/following-sibling::*[1][contains(text(), ",")]')) == 0 \
							and len(self.root.xpath('/'+xref+'/preceding-sibling::*[1][contains(text(), ",")]')) == 0:
							if self.root.xpath('/'+xref+'/sup/text()'):
								lonely.append(["0",xref, (self.root.xpath('/'+xref+'/sup/text()')[0]) ]) # alone
							else:
								lonely.append(["0",xref, (self.root.xpath('/'+xref+'/text()')[0]) ]) # mistakes in lists with separators (e.g. 31411129, sec[1]/p[1]/xref[3])
						elif len(self.root.xpath('/'+xref+'/following-sibling::*[1][contains(text(), ",")]')) != 0 \
							and len(self.root.xpath('/'+xref+'/preceding-sibling::*[1][text() = ","]')) != 0:
							if self.root.xpath('/'+xref+'/sup/text()'):
								groups.append(["2",xref, (self.root.xpath('/'+xref+'/sup/text()')[0]) ]) # inlist
							else:
								groups.append(["2",xref, (self.root.xpath('/'+xref+'/text()')[0]) ])
						elif len(self.root.xpath('/'+xref+'/following-sibling::*[1][contains(text(), ",")]')) == 0 \
							and len(self.root.xpath('/'+xref+'/preceding-sibling::*[1][contains(text(), ",")]')) != 0:
							if self.root.xpath('/'+xref+'/sup/text()'):
								groups.append(["3",xref, (self.root.xpath('/'+xref+'/sup/text()')[0]) ]) # last
							else:
								groups.append(["3",xref, (self.root.xpath('/'+xref+'/text()')[0]) ]) # last
						else: # only rp
							if len(self.root.xpath('/'+xref+'/following-sibling::*[1][contains(text(), ",")]')) != 0 \
								and len(self.root.xpath('/'+xref+'/preceding-sibling::*[1][contains(text(), ",")]')) != 0:
								groups.append(["1",xref, (self.root.xpath('/'+xref+'/sup/text()')[0]) ])
							else:
								lonely.append([ "0",xref, (self.root.xpath('/'+xref+'/sup/text()')[0]) ])
					if len(groups) != 0:
						all_groups.append(groups)
					if len(lonely) != 0:
						all_groups.append(lonely)

		# no separator, weird internal separators
		sublists = [conf.sublist(group) for group in all_groups]
		rp_dictionaries = []
		for group_in_sent in sublists:
			for group_list in group_in_sent:
				rp_dict = [rp for rp in rp_list for tup in group_list if ("rp_xpath" in rp.keys() and rp["rp_xpath"] == tup[1]) or ("pl_xpath" in rp.keys() and rp["pl_xpath"] == tup[1]) ]
				rp_dictionaries.append(rp_dict)

		# add pl xpath/string
		for rp_d in rp_dictionaries:
			if len(rp_d) > 1:
				first_el = rp_d[0]["xml_element"]
				last_el = rp_d[-1]["xml_element"]
				for rp in rp_d:
					if "pl_xpath" not in rp.keys():
						pl_xpath = conf.xpath_list_between_elements(first_el, last_el, self.root)
						rp["pl_xpath"] = pl_xpath
						rp["pl_string"] = self.root.xpath(pl_xpath)
			self.metadata.append(rp_d)

		# sort rp in incremental order
		self.metadata = sorted(self.metadata, key=lambda rp : rp[0]["n_rp"])
		# start enumerate at 1 not 0
		# tot_rp = [(count, r) for count, r in enumerate([rp for group in self.metadata for rp in group],1)]
		for group in self.metadata:
			for rp in group:
				# for count, r in tot_rp:
				# 	if r == rp:
				# 		rp["n_rp"] = count
				# remove useless key:values
				if "n_rp" in rp.keys():
					del rp["n_rp"]
				if "xml_element" in rp.keys():
					del rp["xml_element"]

		return self.metadata

	@staticmethod
	def process_reference_pointers(citing_entity, cited_entities_xmlid_be, reference_pointer_list, graph, resp_agent=None, source_provider=None, source=None):
		""" process a JSON snippet including reference pointers
		return RDF entities for rp, pl, and de according to OCDM """
		de_resources , be_ids = [] , {}
		for pl_entry in reference_pointer_list:
			if len(pl_entry) > 1:
				cur_pl = Jats2OC.process_pointer_list(pl_entry, citing_entity, graph, de_resources, resp_agent, source_provider, source)
				for rp_dict in pl_entry:
					rp_num = Jats2OC.retrieve_rp_occurrence(be_ids, rp_dict)
					rp_entity = Jats2OC.process_pointer(rp_dict, rp_num, citing_entity, cited_entities_xmlid_be, graph, de_resources, resp_agent, source_provider, source, in_list=True)
					cur_pl.contains_element(rp_entity)
					# TODO create hasNext
			else:
				rp_num = Jats2OC.retrieve_rp_occurrence(be_ids, pl_entry[0])
				rp_entity = Jats2OC.process_pointer(pl_entry[0], rp_num, citing_entity, cited_entities_xmlid_be, graph, de_resources, resp_agent, source_provider, source)


	@staticmethod
	def process_pointer_list(pl_entry, citing_entity, graph, de_resources, resp_agent=None, source_provider=None, source=None):
		""" process a pl list of dict """
		cur_pl = graph.add_pl(resp_agent, source_provider, source)
		containers_title = pl_entry[0]["containers_title"]
		if "pl_string" in pl_entry[0]:
			cur_pl.create_content(pl_entry[0]["pl_string"])
		if "pl_xpath" in pl_entry[0]:
			pl_xpath = Jats2OC.add_xpath(graph, cur_pl, pl_entry[0]["pl_xpath"], resp_agent, source_provider, source)
		if "context_xpath" in pl_entry[0]:
			context = Jats2OC.create_context(graph, citing_entity, cur_pl, pl_entry[0]["context_xpath"], de_resources, containers_title, resp_agent)
		return cur_pl


	@staticmethod
	def process_pointer(dict_pointer, rp_num, citing_entity, cited_entities_xmlid_be, graph, de_resources, resp_agent=None, source_provider=None, source=None, in_list=False):
		""" process a rp_dict, create citation and annotation """
		cur_rp = graph.add_rp(resp_agent, source_provider, source)
		containers_title = dict_pointer["containers_title"]
		if "rp_xpath" in dict_pointer:
			rp_xpath = Jats2OC.add_xpath(graph, cur_rp, dict_pointer["rp_xpath"], resp_agent, source_provider, source)
		if "rp_string" in dict_pointer:
			cur_rp.create_content(dict_pointer["rp_string"])
		if in_list==False:
			if "context_xpath" in dict_pointer:
				context = Jats2OC.create_context(graph, citing_entity, cur_rp, dict_pointer["context_xpath"], de_resources, containers_title, resp_agent, source_provider, source)
		for cited_entity, xmlid, be in cited_entities_xmlid_be:
			if dict_pointer["xref_id"] == xmlid:
				cur_rp.denotes_be(be)
				cur_an = graph.add_an(resp_agent, source_provider, source)
				cur_ci = graph.add_ci(resp_agent, citing_entity, cited_entity, rp_num, source_provider, source)
				cur_ci._create_citation(citing_entity, cited_entity)
				cur_an._create_annotation(be, cur_rp, cur_ci)
		return cur_rp


	@staticmethod
	def add_xpath(graph, cur_res, xpath_string, resp_agent=None, source_provider=None, source=None): # new
		cur_id = graph.add_id(resp_agent, source_provider, source)
		cur_id.create_xpath(xpath_string)
		cur_res.has_id(cur_id)


	@staticmethod
	def create_context(graph, citing_entity, cur_rp_or_pl, xpath_string, de_resources, containers_title, resp_agent=None, source_provider=None, source=None):
		cur_sent = Jats2OC.de_finder(graph, citing_entity, xpath_string, de_resources, containers_title, resp_agent, source_provider, source)
		if cur_sent != None:
			cur_rp_or_pl.has_context(cur_sent)


	@staticmethod
	def de_finder(graph, citing_entity, xpath_string, de_resources, containers_title, resp_agent, source_provider=None, source=None):
		cur_de = [de_uri for de_path, de_uri in de_resources if xpath_string == de_path]
		if len(cur_de) == 0: # new de
			de_res = graph.add_de(resp_agent, source_provider, source)
			de_resources.append((xpath_string, de_res))
			if 'substring(string(' in xpath_string and conf.table_tag in xpath_string: # sentence or text chunk
				de_res.create_text_chunk()
			elif 'substring(string(' in xpath_string and conf.table_tag not in xpath_string:
				de_res.create_sentence()
			else:
				de_res.create_discourse_element(conf.elem_to_type(xpath_string))
			de_xpath = Jats2OC.add_xpath(graph, de_res, xpath_string, resp_agent, source_provider, source)
			if xpath_string+'/title' in containers_title:
				de_res.create_title(containers_title[xpath_string+'/title'])
			# TODO create hasNext
			hierarchy = Jats2OC.create_hierarchy(graph, citing_entity, de_res, conf.get_subxpath_from(xpath_string), de_resources, containers_title, resp_agent, source_provider, source)
		else:
			de_res = cur_de[0]

		return de_res

	@staticmethod
	def create_hierarchy(graph, citing_entity, de_res, xpath_string, de_resources, containers_title, resp_agent=None, source_provider=None, source=None):
		if xpath_string != '/article/body' and xpath_string != '/':
			cur_el = Jats2OC.de_finder(graph, citing_entity, xpath_string, de_resources,containers_title, resp_agent, source_provider, source)
			if cur_el != None:
				de_res.contained_in_discourse_element(cur_el)
				hierarchy = Jats2OC.create_hierarchy(graph, citing_entity, cur_el, conf.get_subxpath_from(xpath_string), de_resources, containers_title, resp_agent, source_provider, source)
				if '/' not in xpath_string.split("/article/body/",1)[1] :
					citing_entity.contains_discourse_element(cur_el)
	# TODO method for has next

	@staticmethod
	def retrieve_rp_occurrence(be_ids, rp_dict):
		if rp_dict["xref_id"] in be_ids:
			be_ids[rp_dict["xref_id"]] = be_ids[rp_dict["xref_id"]]+1
		else:
			be_ids[rp_dict["xref_id"]] = 1

		occurrence = be_ids[rp_dict["xref_id"]]
		return str(occurrence)
