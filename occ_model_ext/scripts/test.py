#!/usr/bin/env python
# -*- coding: utf-8 -*-
import jats2oc , conf , pprint
from script.ocdm.graphlib import *

# test
pp = pprint.PrettyPrinter(indent=1)
xml_doc = 'xml_PMC_sample/PMC5906705.nxml'

jats = jats2oc.Jats2OC(xml_doc)
jats.extract_intext_refs()
pp.pprint(jats.full_metadata)

context_path_local = 'context.json'
cccgraph= GraphSet("https://w3id.org/oc/corpus/", context_path_local, "ccc/")
jats.to_rdf(cccgraph)
jats.BRgraph.serialize(destination='ccc/br/'+conf.file_in_folder('br')+'.json', format='json-ld', context=context_path_local, auto_compact=True)
jats.IDgraph.serialize(destination='ccc/id/'+conf.file_in_folder('id')+'.json', format='json-ld', context=context_path_local, auto_compact=True)
jats.DEgraph.serialize(destination='ccc/de/'+conf.file_in_folder('de')+'.json', format='json-ld', context=context_path_local, auto_compact=True)
