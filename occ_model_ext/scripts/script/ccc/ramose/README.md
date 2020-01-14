# Restful API Manager Over SPARQL Endpoints (RAMOSE)

Restful API Manager Over SPARQL Endpoints (RAMOSE) is an application that allows agile development and publication of documented RESTful APIs for querying against RDF triplestores, according to a particular specification document.

## Configuration

RAMOSE is developed in Python 3.8. To install dependencies use: `pip3 install -r requirements.txt` (see [requirements.txt](https://github.com/opencitations/ramose/requirements.txt) for details).

RAMOSE application accepts the following arguments:

```
    -h, --help            show this help message and exit
    -s SPEC, --spec SPEC  The file in hashformat containing the specification of the API.
    -m METHOD, --method METHOD
                          The method to use to make a request to the API.
    -c CALL, --call CALL  The URL to call for querying the API.
    -f FORMAT, --format FORMAT
                          The format in which to get the response.
    -d, --doc             Say to generate the HTML documentation of the API (if it is specified, all the arguments '-m', '-c', and '-f' won't be considered).
    -o OUTPUT, --output OUTPUT
                          A file where to store the response.
    -w WEBSERVER, --webserver WEBSERVER
                          The host:port where to deploy a Flask webserver for testing the API.
```

`-s` is a mandatory argument identifying the configuration file of the API (an hashformat cinfiguration file `.hf`).

### Hashformat configuration file

[TODO]

### Addon python files

Additional python files can be added for preprocessing variables in the API URL call, and for postprocessing responses. In the specification file, addons are specified in the `#addon` field.

**Preprocessing**

RAMOSE preprocesses the URL of the API call according to the functions specified in the `#preprocess` field (e.g. `"#preprocess lower(doi)"`), which is applied to the specified parameters of the URL specified as input of the function in consideration (e.g. "/api/v1/citations/10.1108/jd-12-2013-0166", converting the DOI in lowercase).

It is possible to run multiple functions sequentially by concatenating them with `-->` in the API specification document. In this case the output of the function `f_i` will becomes the input operation URL of the function `f_i+1`.

Finally, it is worth mentioning that all the functions specified in the `#preprocess` field must return a tuple of strings defining how the particular value indicated by the URL parameter must be changed.

**Postprocessing**

RAMOSE takes the result table returned by the SPARQL query performed against the triplestore (as specified in an API operation as input) and change some of such results according to the functions specified in the `#postprocess` field (e.g. `"#postprocess remove_date("2018")"`).

These functions can take parameters as input, while the first unspecified parameters will be always the result table. It is worth mentioning that this result table (i.e. a list of tuples) actually contains, in each cell, a tuple defining the plain value as well as the typed value for enabling better comparisons and operations if needed. An example of this table of result is shown as follows:

```
    [
        ("id", "date"),
        ("my_id_1", "my_id_1"), (datetime(2018, 3, 2), "2018-03-02"),
        ...
    ]
```

In addition, it is possible to run multiple functions sequentially by concatenating them with `"-->"` in the API specification document. In this case the output of the function `f_i` will becomes the input result table of the function `f_i+1`.

## Run RAMOSE

### Run locally

RAMOSE can be run via CLI by specifying configuration file and URL of the desired operation (including parameters). For example, run in the root directory:

```
python3 -m ramose -s <conf_name>.hf -c '<api_base><api_operation_url>?<parameters>'
```

Results are streamed in the shell in the following format:

```
# Response HTTP code: <status_code>
# Body: <response_content>
# Content-type: <format>
```

**Output formats.** RAMOSE returns responses in two formats, namely: `text/csv` and `application/json`. Formats can be specified as values of the argument `-f` or, alternatively, as parameters of the call. For example:

```
python3 -m ramose -f <csv|json|text/csv|application/json> -s <conf_name>.hf -c '<api_base><api_operation_url>|<api_base><api_operation_url>?<parameters>'

python3 -m ramose -s <conf_name>.hf -c '<api_base><api_operation_url>|<api_operation_url>?format=<csv|json|text/csv|application/json>'
```

If no format is specified, a JSON response is returned.

**Ouput.** To store responses in a local file, use the argument `-o` to specify the output file:

```
python3 -m ramose -s <conf_name>.hf -c '<api_base><api_operation_url>?<parameters>' -o '<file_name>.<format>'
```

**API Documentation.** To produce an HTML document including the automatically generated documentation of the API, use the arguments `-d` and `-o` to specify the output file:

```
python3 -m ramose -s <conf_name>.hf -d -o <doc_name>.html
```

### Run with webserver

Additionally, a Flask webserver is available for testing and debugging purposes by specifying as value of the argument `-w` the desired `<host>:<port>`. For example, to run your API in localhost:

```
python3 -m ramose -s <conf_name>.hf -w 127.0.0.1:8080
```

The web application includes:

 * a basic dashboard for tracking API calls (available at `<host>:<port>/`)
 * the documentation of the API (available at `<host>:<port>/<api_base>`)

The local API can be tested via browser or via curl:

```
 curl -X GET --header "Accept: <format>" "http://<host>:<port>/<api_base><operation_url>?<parameters>"
```

## RAMOSE `APIManager`

RAMOSE allows developers to handle several APIs by instantiating the main class `APIManager` and initialising it with a specification file.

The method `exec_op(op_complete_url, method="get", content_type="application/json")` takes in input the url of the call (i.e. the API base URL plus the operation URL), the HTTP method to use for the call, and the content type to return. It executes the operation as indicated in the specification file, by running (in the following order):

  1. the methods to preprocess the query (as defined in the specification file at `#{var}` and `#preprocess`);
  2. the SPARQL query related to the operation called, by using the parameters indicated in the URL (`#sparql`);
  3. the specification of all the types of the various rows returned (`#field_type`);
  4. the methods to postprocess the result (`#postprocess`);
  5. the application of the filter to remove, filter, sort the result (parameters);
  6. the removal of the types added at the step 3, so as to have a data structure ready to be returned;
  7. the conversion in the format requested by the user (`content_type`).

For example:

```
conf = { "api_1": "1_v1.hf", "api_2": "2_v1.hf"}

first_api_manager = APIManager(conf["api_1"])
second_api_manager = APIManager(conf["api_2"])

call_1 = "{api_base}/{operation_url_1}/{var}{?par}"
call_2 = "{api_base}/{operation_url_2}/{var}{?par}"

first_api_manager.exec_op(call_1, content_type={content_type})
second_api_manager.exec_op(call_2, content_type={content_type})
```

### Parameters and filters
Parameters can be used to filter and control the results returned by the API. They are passed as normal HTTP parameters in the URL of the call. They are:

 * `exclude=<field_name>`: all the rows that have an empty value in the `<field_name>` specified are removed from the result set - e.g. `exclude=given_name` removes all the rows that do not have any string specified in the `given_name` field.

 * `filter=<field_name>:<operator><value>`: only the rows compliant with <value> are kept in the result set. The parameter `<operation>` is not mandatory. If `<operation>` is not specified, `<value>` is interpreted as a regular expression, otherwise it is compared by means of the specified operation. Possible operators are "=", "<", and ">". For instance, `filter=title:semantics?` returns all the rows that contain the string "semantic" or "semantics" in the field title, while `filter=date:>2016-05` returns all the rows that have a date greater than May 2016.

 * `sort=<order>(<field_name>)`: sort in ascending (`<order>` set to `"asc"`) or `descending` (`<order>` set to `"desc"`) order the rows in the result set according to the values in `<field_name>`. For instance, `sort=desc(date)` sorts all the rows according to the value specified in the field date in descending order.

 * `format=<format_type>`: the final table is returned in the format specified in `<format_type>` that can be either `"csv"` or `"json"` - e.g. `format=csv` returns the final table in CSV format. This parameter has higher priority of the type specified through the "Accept" header of the request. Thus, if the header of a request to the API specifies `Accept: text/csv` and the URL of such request includes `format=json`, the final table is returned in JSON.

 * `json=<operation_type>("<separator>",<field>,<new_field_1>,<new_field_2>,...)`: in case a JSON format is requested in return, transform each row of the final JSON table according to the rule specified. If `<operation_type>` is set to `"array"`, the string value associated to the field name `<field>` is converted into an array by splitting the various textual parts by means of `<separator>`. For instance, considering the JSON table `[ { "names": "Doe, John; Doe, Jane" }, ... ]`, the execution of `array("; ",names)` returns `[ { "names": [ "Doe, John", "Doe, Jane" ], ... ]`. Instead, if `<operation_type`> is set to `"dict"`, the string value associated to the field name <field> is converted into a dictionary by splitting the various textual parts by means of <separator> and by associating the new fields `<new_field_1>`, `<new_field_2>`, etc., to these new parts. For instance, considering the JSON table `[ { "name": "Doe, John" }, ... ]`, the execution of `dict(", ",name,fname,gname)` returns `[ { "name": { "fname": "Doe", "gname": "John" }, ... ]`.

It is possible to specify one or more filtering operation of the same kind (e.g. `exclude=given_name&exclude=family_name`). In addition, these filtering operations are applied in the order presented above - first all the `exclude` operation, then all the `filter` operations followed by all the `sort` operation, and finally the `format` and the `json` operation (if applicable). It is worth mentioning that each of the aforementioned rules is applied in order, and it works on the structure returned after the execution of the previous rule.

Example:

```
 <api_operation_url>?exclude=doi&filter=date:>2015&sort=desc(date).
```

## Examples

[TODO]
