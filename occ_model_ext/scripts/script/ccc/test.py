#!/usr/bin/env python
# -*- coding: utf-8 -*-
import script.ccc.jats2oc as jats2oc
import script.ccc.conf as conf
import pprint
from script.ocdm.graphlib import *

# test
pp = pprint.PrettyPrinter(indent=1)
#xml_doc = 'script/ccc/xml_PMC_sample/PMC5906705.nxml'
xml_doc = 'script/ccc/xml_PMC_sample/6test.xml'

jats = jats2oc.Jats2OC(xml_doc)
jats.extract_intext_refs()
#pp.pprint(jats.metadata)

# context_path_local = 'context.json'
# cccgraph= GraphSet("https://w3id.org/oc/corpus/", context_path_local, "ccc/")
# jats.to_rdf(cccgraph)
# jats.BRgraph.serialize(destination='ccc/br/'+conf.file_in_folder('br')+'.json', format='json-ld', context=context_path_local, auto_compact=True)
# jats.IDgraph.serialize(destination='ccc/id/'+conf.file_in_folder('id')+'.json', format='json-ld', context=context_path_local, auto_compact=True)
# jats.DEgraph.serialize(destination='ccc/de/'+conf.file_in_folder('de')+'.json', format='json-ld', context=context_path_local, auto_compact=True)
