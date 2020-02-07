#!/usr/bin/env python
# -*- coding: utf-8 -*-
import script.ccc.jats2oc as jats2oc
import script.ccc.conf_bee as conf
import pprint
from script.ocdm.graphlib import *

# test
pp = pprint.PrettyPrinter(indent=1)
xml_doc = 'script/ccc/xml_PMC_sample/diff_graphs_test_citing.xml'

jats = jats2oc.Jats2OC(xml_doc)
jats.extract_intext_refs()
pp.pprint(jats.metadata)
