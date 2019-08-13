## QUESTIONS
 * I added in context.json the alias ''has_part''. How does it interact with the existing ''reference''?
 * should I put a graphset as parameter of to_rdf?
 * do we need rp > hasNext > rp when they are in lists?

## ISSUES

## TODO
### extract_intext_refs
  * check whether titles are correctly extracted

### to_rdf
 * remove the graphs and the serialisation
 * does not find the context file
 * how to put everything in the br graph?
 * does a br include par, secs, sentences etc. at the same level frbr:part? [ANSWER] only nested frbr:part
 * change the path of context.json
