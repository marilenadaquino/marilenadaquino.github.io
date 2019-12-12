## QUESTIONS
 * should I look in the triplestore for disambiguating pl/rp? NO
 * xpaths are identifier that can be shared. Should I create a new identifier everytime or just one for all the xpath with the same XPath? YES
 * who has hasNext? rp in pl, de at same level
 * the hierarchy of de is for both pl and rp or just for pl when it exists? and sentence? only pl when is pl, otherwise rp


## NOTES

* URI of the new corpus = https://w3id.org/oc/ccc/
* prefix of ccc 070
* NOTE FOR Silvio: provided_url to be changed
* JSON-LD to be converted in ntriples

## TODO
 * method for associating titles to sections and not only  
 * annotation / citation .. annotations have incremental numbers!
 * ci modify support find_paths() for ci
 * hasNext in graphlib and add in script

### other

 * graphlib - add methods for annotations (hasBody and hasAnnotation) and control prefixes everywhere
 * jats2oc.py - remove n_rp
 * jats2oc.py - check mistakes in pl_string bee
 * jats2oc.py - refactor extract_intext_refs() in functions
 * jats2oc.py - run BEE
 * graphlib - trick for json labels (part of/reference)
 * config_spacin and ocdm/config - change folder names for production


### FUTURE

 * run again SPACIN to check whether "derived_from" and "update_action" are correctly included in se
 * speed up BEE by using a directory (new method)
 * review queries to crossref

## DONE

 * remove all labels from data
 * simplify ProvSet
 * remove useless methods in conf_bee
 * conf_spacin.py - name and URI of new corpus w3id
 * conf_spacin.py - prefix of supplier
 * rp_n in JSON should start from 1 and not 0
 * "label": "OCC / br", to be changed
 * method for sentence/chunk for pl and rp
 * method for extracting all de from xpath
 * double check URI in final data
 * method for reconciling DE to the right one (no duplictes)
 * associate classes to DE and discard the elements that are not mapped to OCDM
 * remove prov folder pa.txt
 * refactor the URI patter for all the entities that need the prefix

## PLAN

* [14/12/2019] storer da fabio, e dare graphlib senza prov a fabio
* [7/1/2020] speed up CrossrefProcessor (text search) + preliminary questions per Leiden: cosa vi potrebbe interessare?
* [14/1/2020] deploy BEE/SPACIN on production: change config SPACIN, create new blazegraph (ccc.properties uguale al corpus)
* [entro febbraio?] merge con Fabio
* [20/1/2020] API Ramose (locally) + custom interesting per noi
* [1/2/2020] API Ramose (remote) + accordi con Leiden / Cambridge
* write papers? ISWC? Journal
