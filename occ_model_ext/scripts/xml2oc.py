#!/usr/bin/env python
# -*- coding: utf-8 -*-
from lxml import etree as ET
from collections import defaultdict
import pprint , re , uuid , html


def extract_intext_ref(filePMC):
	""" preprocess a nxml file and stores a number of context components in a JSON file, namely:
	0. articleDOI : DOI of the citing article
	1. inTextRef : single in-text reference pointers, lists, and sequences of in-text reference pointers
	2. xPointer : xPointer of sentence/text chunk including in-text reference pointers
	3. discourseElement : paragraph/table/footnote and section including the in-text reference pointers
	4. bibRefPMID : PMC-IDs of bibliographic references denoted by in-text reference pointers
	"""
	pp = pprint.PrettyPrinter(indent=1)
	xmlp = ET.XMLParser(encoding="utf-8")
	tree = ET.parse(filePMC, xmlp)
	root = tree.getroot()
	counting = 0
	parent_map = dict((c, p) for p in root.getiterator() for c in p) # map parents/children

	# store in-text	refs and context in a dictionary
	articleDOI = root.find('.//article-id[@pub-id-type="doi"]').text
	articleInTextRefs = {}
	articleInTextRefs[articleDOI] = {}
	articleInTextRefs[articleDOI]['lists'] = []
	articleInTextRefs[articleDOI]['sequences'] = []
	articleInTextRefs[articleDOI]['singleITR'] = []

	# extract square brackets content
	inTextRefGroups = re.findall(r'\[.*?\]', ET.tostring(root, encoding='utf-8', method="text").decode('utf-8') )
	# 1. plain lists, e.g. 1,3,6
	inTextRefLists = [inTextRefGroup.replace('[', '').replace(']', '').split(',') for inTextRefGroup in inTextRefGroups if ',' in inTextRefGroup]
	# 2. sequences, e.g. 1-5, that are extended in 1,2,3,4,5
	inTextRefSequences = [inTextRefGroup.replace('[', '').replace(']', '').split('\u2013') for inTextRefGroup in inTextRefGroups if '\u2013' in inTextRefGroup]
	inTextRefSequencesExtended = [[str(intRef) for intRef in range(int(inTextRefSequence[0]),int(inTextRefSequence[1])+1 )] for inTextRefSequence in inTextRefSequences]
	# 3. single pointers
	inTextRefSingle = [inTextRefGroup.replace('[', '').replace(']', '') for inTextRefGroup in inTextRefGroups if re.match(r'^[[0-9]+]$', inTextRefGroup)]

	# extract in-text references and context from the nxml file
	for inTextRef in root.findall('.//xref[@ref-type="bibr"]'): 
		counting += 1
		inTextRefValue = inTextRef.text
		bibRefID = inTextRef.get('rid')
		discourseElement = inTextRef.getparent().tag
		
		# cited entities: doi, pmid, or random uuid
		patternDOI = './/ref[@id="'+bibRefID+'"]/element-citation/pub-id[@pub-id-type="doi"]'
		patternPMID = './/ref[@id="'+bibRefID+'"]/element-citation/pub-id[@pub-id-type="pmid"]'
		if root.find(patternDOI) is not None:
			bibRefUID = root.find(patternDOI).text
		elif root.find(patternDOI) is None and root.find(patternPMID) is not None:
			bibRefUID = root.find(patternPMID).text
		else:
			bibRefUID = uuid.uuid4()
		
		for inTextRefList in inTextRefLists:
			for inTextRefVal in inTextRefList:
				if inTextRefVal == inTextRefValue:
					print('list', inTextRefList, inTextRefVal, bibRefUID, discourseElement)
		
		for inTextRefSeq in inTextRefSequencesExtended:
			for inTextRefVal1 in inTextRefSeq:
				if inTextRefVal1 == inTextRefValue:
					print('seq', inTextRefSeq, inTextRefVal1, bibRefUID, discourseElement)
				if inTextRefVal1 != inTextRefValue and root.find('.//ref[label="'+inTextRefVal1+'"]'): # intermediate refs that do not have a xref in the full text
					# TODO doi, pubid, or nothing!!
					patternDOIlabel = './/ref[label="'+inTextRefVal1+'"]/element-citation/pub-id[@pub-id-type="doi"]'
					patternPMIDlabel = './/ref[label="'+inTextRefVal1+'"]/element-citation/pub-id[@pub-id-type="pmid"]'
					if root.find(patternDOIlabel) is not None:
						bibRefUID = root.find(patternDOIlabel).text
					elif root.find(patternDOIlabel) is None and root.find(patternPMIDlabel) is not None:
						bibRefUID = root.find(patternPMIDlabel).text
					else:
						bibRefUID = uuid.uuid4()
					print('seq', inTextRefSeq, inTextRefVal1, bibRefUID, 'TBF discourseElement TBF')
					# TODO discourseElement?
					# add to seq
		for inTextRefVal2 in inTextRefSingle:
			if inTextRefVal2 == inTextRefValue:
				print('single', inTextRefSingle, inTextRefVal2, bibRefUID, discourseElement)
			
		# text of parent: print(ET.tostring(parent_map[inTextRef], encoding='utf-8', method="text"))
		
		
		# 1. plain lists, e.g. 1,3,6
		#if inTextRef.tail == ',': 
			# TODO check how it works for tables and footnotes
			# DOESN'T MATCH THE LAST OF THE LIST
			#articleInTextRefs[articleDOI]['lists'].append( (inTextRefValue, bibRefPMID, discourseElement) )
			# print('list:', ET.tostring(parent_map[inTextRef], encoding='utf-8', method="text"))
			# inTextRef.getnext()
			# print('lis2:', inTextRef.getparent().text.encode('utf-8'))
		
		
		# DOESN'T WORK
		#elif inTextRef.tail == '&#x02013;':  
			#print('sequence:', ET.tostring(parent_map[inTextRef], encoding='utf-8', method="text"))
		
		
		# MATCHES ALSO THE LAST OF A LIST/SEQUENCE
		# else: 
		# 	articleInTextRefs[articleDOI]['singleITR'].append( (inTextRefValue, bibRefPMID, discourseElement) )
			#print('single:', ET.tostring(parent_map[inTextRef], encoding='utf-8', method="text"))
	#print(counting)	
	#pp.pprint(articleInTextRefs)


# TODO wrapper to parse every document in a folder/ got from the api? dump?
filePMC = 'xml_PMC_sample/PMC2563889.nxml'
extract_intext_ref(filePMC)

# extraction of sentences, xpointers
# handler of identifiers of document components
# handler of identifiers of existing OC entities