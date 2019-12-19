
## NOTES

* URI of the new corpus = https://w3id.org/oc/ccc/
* prefix of ccc 070
* NOTE FOR Silvio: provided_url to be changed

* should I look in the triplestore for disambiguating pl/rp? NO
* xpaths are identifier that can be shared. I create a new identifier everytime (YES)
* who has hasNext? rp in pl, de at same level
* the hierarchy of de is for both pl and rp or just for pl when it exists? and sentence? only pl when is pl, otherwise rp

## TODO

 * [FIX] We got an HTTP error when retrieving data (HTTP status code: 404): is this an actual problem of mine?
 * triplestore per silvio/ david con un 1000 paper
 * [ADD] control doi2doi self citation
 * merge with fabio's graphlib : prov, labels, storer (save in nt11) other boolean values here and there

### Christmas homework

 * evaluation on lists (compare cites and the presence of rp for that link)

 * jats2oc.py - BEE: remove n_rp
 * jats2oc.py - BEE: check mistakes in pl_string bee
 * jats2oc.py - BEE: refactor extract_intext_refs() in functions
 * jats2oc.py - BEE: method for running BEE on a directory

 * config_spacin and ocdm/config - change folder names for production


### FUTURE

 * run again SPACIN to check whether "derived_from" and "update_action" are correctly included in se


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
 * method for associating titles to sections and not only  
 * annotation / citation .. annotations have incremental numbers!
 * ci modify support find_paths() for ci
 * graphlib - add methods for annotations (hasBody and hasAnnotation) and control prefixes everywhere
 * hasNext in graphlib and add in script
 * change add_ci to work without /n_rp
 * send prov to fabio
 * remove text search to api crossref
 * [FIX] WARNING:rdflib.term:https://w3id.org/oc/ccc/ci/07085-07089/Europe PubMed Central does not look like a valid URI,
 * [FIX] id-counter wrong folders
 * [FIX] ci folder structure: review regex find_paths : ci/070/10000/1000.json

## PLAN

* [14/12/2019] storer da fabio, e dare graphlib senza prov a fabio
* [7/1/2020] speed up CrossrefProcessor (text search) + preliminary questions per Leiden: cosa vi potrebbe interessare?
* [14/1/2020] deploy BEE/SPACIN on production: change config SPACIN, create new blazegraph (ccc.properties uguale al corpus)
* [entro febbraio?] merge con Fabio
* [20/1/2020] API Ramose (locally) + custom interesting per noi
* [1/2/2020] API Ramose (remote) + accordi con Leiden / Cambridge
* write papers? ISWC? Journal
