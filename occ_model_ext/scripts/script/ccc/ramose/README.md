# Restful API Manager Over SPARQL Endpoints (RAMOSE)

Restful API Manager Over SPARQL Endpoints (RAMOSE) is an API Manager that allows agile development, customisation, and publication of documented APIs for querying RDF triplestores.

## Configuration

RAMOSE is developed in Python 3.8. See [requirements.txt](https://github.com/opencitations/ramose/requirements.txt) for details.
  <p>CLI or web server </p>
  <p>run in in the root directory</p>
  <p>hf configuration file </p>
  <p>addon py file: preprocessing and post processing</p>
  <p><strong>Main class:</strong> <code>API Manager</code></p>
</div>

<h2>Examples</h2>
<p>call from cli:
 * python3 -m ramose -s ccc_v1.hf -c '/api/v1/metadata/10.1080/14756366.2019.1680659?json=array(";",occ_reference)
 * curl -X GET --header "Accept: */*" "http://localhost:8080/api/v1/metadata/10.1080/14756366.2019.1680659?format=json&json=array(%22;%22,occ_reference)"
 and from browser</p>
<p>JSON and CSV output</p>
<p>operations on json out-of-the-box</p>
