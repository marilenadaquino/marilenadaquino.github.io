## QUESTIONS
 * snapshots for all entities or only br?


## NOTES
* URI of the new corpus = https://w3id.org/ccc/
* prefix of ccc 070

## TODO

### other
 * graphlib add annotations and control prefixes everywhere
 * refactor the URI patter for all the entities that need the prefix
 * jats2oc.py - run again BEE to create rp_n in JSON that start from 1 and not 0
 * trick for json labels (part of/reference)
 * NOTE FOR Silvio: provided_url to be changed
 * change folder config for production (config_spacin and ocdm>config)

### to_rdf
 * IRI design including ccc number prefix - which entities?
 * handle citation entities
 * does not find the context file -- change the path of context.json
 * hasNext in graphlib and add in script
 * remove parameter graph (?)

### FUTURE
 * jats2oc.py - refactor extract_intext_refs() in functions
 * run again SPACIN to check whether "derived_from" and "update_action" are correctly included in se


## DONE
 * remove all labels from data
 * simplify ProvSet
 * remove useless methods in conf_bee
 * conf_spacin.py - name and URI of new corpus w3id
 * conf_spacin.py - prefix of supplier
 * rp_n in JSON should start from 1 and not 0
