#!/usr/bin/env python
# -*- coding: utf-8 -*-
from lxml import etree as ET
from collections import defaultdict
import pprint , re , uuid , html


def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v
                     for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v)
                        for k, v in t.attrib.items())
    if t.tag == 'xref' and t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
              d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d

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
	parentMapDict = etree_to_dict(tree.getroot())
	pp.pprint(parentMapDict)
	root = tree.getroot()
	counting = 0
	inTextRefElems = root.findall('.//xref[@ref-type="bibr"]')
	#parent_map = dict((parent, xref) for parent in root.getiterator() for xref in parent if xref in inTextRefElems ) # map parents/xref
	
	# store in-text	refs and context in a dictionary
	articleDOI = root.find('.//article-id[@pub-id-type="doi"]').text
	articleInTextRefs = {}
	articleInTextRefs[articleDOI] = {}
	articleInTextRefs[articleDOI]['lists'] = defaultdict(set)
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

	# extract in-text references in the same context from the nxml file
	#for parent, inTextRef in parent_map.items():
		#for inTextRef in root.findall('.//xref[@ref-type="bibr"]'): 
	
	#for discElemDict in parentMapDict['article']['body']['sec']: # iterate over sections
	for inTextRef in root.findall('.//xref[@ref-type="bibr"]'):
		counting += 1
		inTextRefValue = inTextRef.text
		bibRefID = inTextRef.get('rid')
		discourseElement = inTextRef.getparent().tag #discourseElement = inTextRef.getparent().tag
		
		# cited entities: doi, pmid, or random uuid
		patternDOI = './/ref[@id="'+bibRefID+'"]//pub-id[@pub-id-type="doi"]'
		patternPMID = './/ref[@id="'+bibRefID+'"]//pub-id[@pub-id-type="pmid"]'
		if root.find(patternDOI) is not None:
			bibRefUID = root.find(patternDOI).text
		elif root.find(patternDOI) is None and root.find(patternPMID) is not None:
			bibRefUID = root.find(patternPMID).text
		else:
			bibRefUID = uuid.uuid4()
		
		# lists
		countList = 0
		for inTextRefList in inTextRefLists:
			countList += 1
			listName = 'list_'+str(countList)
			
			for inTextRefVal in inTextRefList:
				# check if all xref are in the same parent
				if inTextRefVal == inTextRefValue:
					# inTextRefValue[i].getparent().tag == inTextRefValue[i+1].getparent().tag
					# PROBLEM 36, 38. 36 appears both in p (alone) 
					# and in td along with 38. in the list 36 is repeated because of the different context
					articleInTextRefs[articleDOI]['lists'][listName].add((','.join(inTextRefList), inTextRefVal, bibRefUID, discourseElement))
			
		
		# for inTextRefSeq in inTextRefSequencesExtended:
		# 	for inTextRefVal1 in inTextRefSeq:
		# 		if inTextRefVal1 == inTextRefValue: # first and last of the sequence
		# 			print('seq', inTextRefSeq, inTextRefVal1, bibRefUID, discourseElement)
		# 		elif inTextRefVal1 != inTextRefValue and root.find('.//ref[label="'+inTextRefVal1+'"]') is not None: # intermediate refs that do not have a xref in the full text
		# 			# doi, pubid, or random uuid
		# 			patternDOIlabel = './/ref[label="'+inTextRefVal1+'"]//pub-id[@pub-id-type="doi"]'
		# 			patternPMIDlabel = './/ref[label="'+inTextRefVal1+'"]//pub-id[@pub-id-type="pmid"]'
		# 			if root.find(patternDOIlabel) is not None:
		# 				bibRefUID = root.find(patternDOIlabel).text
		# 			elif root.find(patternDOIlabel) is None and root.find(patternPMIDlabel) is not None:
		# 				bibRefUID = root.find(patternPMIDlabel).text
		# 			else:
		# 				bibRefUID = uuid.uuid4()
		# 			# discourse element of first xref of the sequence
		# 			inTextRefPrev = root.find('.//xref[@ref-type="bibr"][.="'+inTextRefSeq[0]+'"]')
		# 			discourseElementPrev = inTextRefPrev.getparent().tag
		# 			print('seq', inTextRefSeq, inTextRefVal1, bibRefUID, discourseElementPrev)
					
		# for inTextRefVal2 in inTextRefSingle:
		# 	if inTextRefVal2 == inTextRefValue:
		# 		print('single', inTextRefSingle, inTextRefVal2, bibRefUID, discourseElement)
			
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
	pp.pprint(articleInTextRefs)


# TODO wrapper to parse every document in a folder/ got from the api? dump?
filePMC = 'xml_PMC_sample/PMC5906705.nxml'
extract_intext_ref(filePMC)

# extraction of sentences, xpointers
# handler of identifiers of document components
# handler of identifiers of existing OC entities