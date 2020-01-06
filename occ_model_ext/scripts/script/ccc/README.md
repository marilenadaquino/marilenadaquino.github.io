## NOTES

* URI of the new corpus = https://w3id.org/oc/ccc/
* prefix of ccc 070
* NOTE FOR Silvio: provided_url to be changed

## TODO


 * [FIX] all pl exceptions
 * does not upload the provenance
 * [ADD] control doi2doi self citation

### Christmas homework

 * evaluation on lists (compare cites and the presence of rp for that link)
 * check if intrepid works correctly
 * jats2oc.py - BEE: check mistakes in pl_string bee
 * jats2oc.py - BEE: method for running BEE on a directory
 * run BEE on directory and provide folder for deployment and run SPACIN
 * config_spacin and ocdm/config - change folder names for production


### FUTURE

 * run again SPACIN to check whether "derived_from" and "update_action" are correctly included in se

## DONE

 * [FIX] no xmlid of be for intermediate
 * [FIX] duplicate rp
 * jats2oc.py - BEE: refactor extract_intext_refs() in functions
 * jats2oc.py - BEE: move all methods in conf in jats2oc.py and change prefix
 * add intrepid when creating the oci of the citation
 * BUG! http://localhost:9999/blazegraph/#explore:kb:%3Chttps://w3id.org/oc/ccc/be/0701%3E random annotations created for the same citation
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
 * jats2oc.py - BEE: remove n_rp
 * [7/1/2020] speed up CrossrefProcessor (text search)

## PLAN

* [14/12/2019] merge with fabio's graphlib : prov, labels, storer (save in nt11) other boolean values here and there
* [7/1/2020] preliminary questions to Leiden: what data would you like to access?
* [14/1/2020] deploy BEE/SPACIN on production: change config SPACIN, create new blazegraph (ccc.properties uguale al corpus)
* [20/1/2020] API Ramose (locally) + custom interesting stuff to provide
* [1/2/2020] API Ramose (remote) + agree w/ Leiden / Cambridge
* write papers? ISWC? Journal
