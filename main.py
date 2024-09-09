import argparse
import os
import yaml
import logging
import re
import json
import requests
from box import Box
from rich.logging import RichHandler
from rich.console import Console
from rich.table import Table
from rich.text import Text

# Initialize Rich console
console = Console()

# ANSI escape sequences for colored logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    handlers=[RichHandler()])

logger = logging.getLogger("API_Tester")


# Adjusting the logging levels with rich
def set_logging_level(log_level):
    """Set the logging level based on the provided string."""
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    logger.setLevel(levels.get(log_level.upper(), logging.DEBUG))  # Default to DEBUG if not found


def get_required_keys():
    """Returns a list of required keys for each test case."""
    return ['name', 'request', 'expected']


def read_yaml(file_path):
    """Reads a YAML file and returns the contents as a dictionary."""
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None


def resolve_constants(constants, data):
    """Recursively resolve constants in the data by replacing placeholders with their actual values."""
    if isinstance(data, dict):
        return {key: resolve_constants(constants, value) for key, value in data.items()}
    elif isinstance(data, list):
        return [resolve_constants(constants, item) for item in data]
    elif isinstance(data, str):
        for key, value in constants.items():
            if isinstance(value, str):
                data = re.sub(r'\{' + re.escape(key) + r'\}', value, data)
        return data
    return data  # return the data as is for other types


def validate_test(test, required_keys):
    """Validates that all required keys are present in the test."""
    missing_keys = [key for key in required_keys if key not in test]
    if missing_keys:
        logger.error(f"Test missing required keys: {', '.join(missing_keys)} in test: {test}")
        raise ValueError(f"Test is invalid due to missing keys: {', '.join(missing_keys)}")

    # Validate the request structure
    if 'request' not in test or not isinstance(test['request'], dict):
        logger.error(f"Request must be a dictionary in test: {test}")
        raise ValueError("Request must be a dictionary.")

    if 'method' not in test['request'] or 'endpoint' not in test['request']:
        logger.error(f"Request missing 'method' or 'endpoint' in test: {test}")
        raise ValueError("Request must contain both 'method' and 'endpoint.'")


def set_logging_level(log_level):
    """Set the logging level based on the provided string."""
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return levels.get(log_level.upper(), logging.INFO)  # Default to DEBUG if not found


def parse_json_response(response_text):
    """Parse the JSON response text and return a formatted string for logging."""
    try:
        response_json = json.loads(response_text)
        pretty_json = json.dumps(response_json, indent=4)  # Pretty-JSON
        return response_json, pretty_json
    except json.JSONDecodeError:
        logger.error("Response content is not valid JSON.")
        return None  # Return None if response is not JSON


def validate_type(expected_key, actual_value, expected_type):
    """Validate the type of a given value against the expected type."""
    type_mapping = {
        "list": list,
        "dict": dict,
        "str": str,
    }
    if expected_type in type_mapping and not isinstance(actual_value, type_mapping[expected_type]):
        logger.error(
            f"Key '{expected_key}' is expected to be a {expected_type}, but got {type(actual_value).__name__}.")
        raise ValueError(
            f"Key '{expected_key}' is expected to be a {expected_type}, but got {type(actual_value).__name__}.")


def validate_membership(expected_key, actual_value, expected_value, should_contain=True):
    """Validate that a string or list contains or does not contain a specified value."""
    if isinstance(actual_value, str):
        check = expected_value in actual_value
    elif isinstance(actual_value, list):
        check = expected_value in actual_value
    else:
        logger.error(
            f"Key '{expected_key}' has unsupported type '{type(actual_value).__name__}'. Expected a string or list.")
        raise TypeError(
            f"Key '{expected_key}' has unsupported type '{type(actual_value).__name__}'. Expected a string or list.")

    if check != should_contain:
        action = "contains" if should_contain else "does not contain"
        logger.error(
            f"Key '{expected_key}' ({type(actual_value).__name__}) {action} '{expected_value}', but got '{actual_value}'.")
        raise ValueError(
            f"Key '{expected_key}' ({type(actual_value).__name__}) {action} '{expected_value}', but got '{actual_value}'.")


def validate_not_equal(expected_key, actual_value, expected_value):
    """Validate that a value is not equal to an expected value."""
    if actual_value == expected_value:
        logger.error(f"Key '{expected_key}' expected value not to be '{expected_value}', but got '{actual_value}'.")
        raise ValueError(f"Key '{expected_key}' expected value not to be '{expected_value}', but got '{actual_value}'.")


def validate_equal(expected_key, actual_value, expected_value):
    """Validate that a value equals the expected value."""
    if actual_value != expected_value:
        logger.error(f"Key '{expected_key}' expected value '{expected_value}', but got '{actual_value}'.")
        raise ValueError(f"Key '{expected_key}' expected value '{expected_value}', but got '{actual_value}'.")


def validate_empty(expected_key, actual_value, should_be_empty=True):
    """Validate that a value is either empty or not empty based on the flag."""
    is_empty = not actual_value
    if is_empty != should_be_empty:
        state = "empty" if should_be_empty else "not empty"
        logger.error(f"Key '{expected_key}' is expected to be {state}.")
        raise ValueError(f"Key '{expected_key}' is expected to be {state}.")


def validate_regex(expected_key, actual_value, expected_regex):
    """Validate that a string matches the expected regex pattern."""
    if not re.match(expected_regex, actual_value):
        logger.error(f"Key '{expected_key}' does not match the regex pattern.")
        raise ValueError(f"Key '{expected_key}' does not match the regex pattern.")


def validate_expected_response(response, expected):
    """Validate the actual response against the expected values."""
    # Validate status code
    expected_status = expected.get('status')
    if response.status_code != expected_status:
        logger.error(f"Expected status {expected_status}, but got {response.status_code}")
        raise ValueError(f"Expected status {expected_status}, but got {response.status_code}")

    # Parse the response JSON
    response_json, pretty_json = parse_json_response(response.text)
    if response_json is None:
        raise ValueError("Response is not a valid JSON.")

    # Validate JSON structure
    if expected.get('response', {}).get('type') == 'json':
        validation_map = {
            'type': validate_type,
            'equal': validate_equal,
            'not_equal': validate_not_equal,
            'contains': lambda k, v, e: validate_membership(k, v, e, should_contain=True),
            'not_contains': lambda k, v, e: validate_membership(k, v, e, should_contain=False),
            'not_empty': lambda k, v: validate_empty(k, v, should_be_empty=False),
            'empty': lambda k, v: validate_empty(k, v, should_be_empty=True),
            'regex': validate_regex,
        }

        for item in expected['response']['json']:
            key = f"json.{item['key']}"
            actual_value = navigate_json(response_json, key)

            for validation_key, validation_function in validation_map.items():
                if validation_key in item:
                    validation_function(key, actual_value, item[validation_key])

def navigate_json(json_data, key):
    """Navigate through a nested JSON object using a dot-separated key."""
    try:
        json_box = Box(box_dots=True)
        json_box.json = json_data

        return json_box[key]
    except Exception as e:
        logger.error(f"Key '{key}' in JSON {json_data} Error: {e}")
        raise ValueError(f"Key '{key}' in JSON {json_data} Error: {e}")


def process_test(test, constants, saved_responses):
    """Process a single test, resolving constants in the request and expected values."""
    if 'request' in test and isinstance(test['request'], dict):
        test['request'] = resolve_constants(constants, test['request'])  # Resolve constants in request

        if 'params' in test['request']:
            for param_key, param_value in test['request']['params'].items():
                if isinstance(param_value, dict) and 'response_from' in param_value:
                    response_name = param_value['response_from']['name']
                    for key in param_value['response_from']['response']['json']:
                        json_key = key['key']

                        actual_value = saved_responses[response_name][json_key]
                        test['request']['params'][param_key] = actual_value

                        if actual_value is None:
                            logger.error(f"Response '{response_name}' not found for parameter '{param_key}'.")
                            raise ValueError(f"Response '{response_name}' not found for parameter '{param_key}'.")

    if 'expected' in test and isinstance(test['expected'], dict):
        test['expected'] = resolve_constants(constants, test['expected'])  # Resolve constants in expected

        # find response_from in expected value or contains
        for i, (keys) in enumerate(test['expected']['response']['json']):
            for real_key, value in keys.items():
                if isinstance(value, dict) and 'response_from' in value:
                    response_name = value['response_from']['name']
                    for key in value['response_from']['response']['json']:
                        json_key = key['key']
                        actual_value = saved_responses[response_name][json_key]
                        test['expected']['response']['json'][i][real_key] = actual_value
                        if actual_value is None:
                            logger.error(f"Response '{response_name}' not found for parameter '{json_key}'.")
                            raise ValueError(f"Response '{response_name}' not found for parameter '{json_key}'.")

    # Pretty print JSON components
    params_pretty = json.dumps(test['request'].get('params', {}), indent=4)
    headers_pretty = json.dumps(test['request'].get('headers', {}), indent=4)
    body_pretty = json.dumps(test['request'].get('body', {}), indent=4)
    expected_pretty = json.dumps(test['expected'], indent=4)

    # Use Rich to log the request details
    text = Text()
    text.append("Request Details:\n", style="bold underline")
    text.append(f"  Method: {test['request']['method']}\n", style="bold cyan")
    text.append(f"  Endpoint: {test['request']['endpoint']}\n", style="cyan")
    text.append(f"  Params: {params_pretty}\n", style="cyan")
    text.append(f"  Headers: {headers_pretty}\n", style="cyan")
    text.append(f"  Body: {body_pretty}\n", style="cyan")
    text.append(f"  Expected Value: {expected_pretty}\n", style="cyan")
    logger.debug(text)


def make_request(request, constants, saved_responses):
    """Make an HTTP request based on the provided request parameters."""
    method = request['method'].upper()
    endpoint = request['endpoint']
    params = request.get('params', {})
    headers = request.get('headers', {})
    body = request.get('body')

    try:
        if method == 'GET':
            response = requests.get(endpoint, params=params, headers=headers)
        elif method == 'POST':
            if isinstance(body, dict):
                response = requests.post(endpoint, json=body, headers=headers)
            else:
                response = requests.post(endpoint, data=body, headers=headers)
        elif method == 'PUT':
            if isinstance(body, dict):
                response = requests.put(endpoint, json=body, headers=headers)
            else:
                response = requests.put(endpoint, data=body, headers=headers)
        elif method == 'DELETE':
            response = requests.delete(endpoint, headers=headers)
        elif method in ['PATCH', 'OPTIONS', 'HEAD']:
            response = requests.request(method, endpoint, headers=headers, data=body)
        else:
            logger.error(f"Unsupported HTTP method: {method}")
            raise ValueError(f"Unsupported HTTP method: {method}")

        logger.debug(f"Response Status Code: {response.status_code}")
        _, pretty_json = parse_json_response(response.text)
        logger.debug(f"Response Content: {pretty_json}")  # Parse and log the response content
        return response
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise


def check_verb_http(verb):
    """Check if the HTTP verb is valid."""
    verbs = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'CONNECT', 'TRACE']
    if verb not in verbs:
        logger.error(f"Invalid HTTP verb: {verb}")
        raise ValueError(f"Invalid HTTP verb: {verb}")


def run_tests(test_file):
    """Loads and processes the test file."""
    logger.info(f"Loading test file: {test_file}")
    data = read_yaml(test_file)

    if data:
        constants = data.get('constants', {})  # Get the constants if defined
        logger.info(f"Constants Loaded: {json.dumps(constants, indent=4)}")

        # Resolve constants for the entire data structure
        data = resolve_constants(constants, data)
        saved_responses = Box(box_dots=True)  # Dictionary to store saved responses
        results = []  # List to store test results

        if 'tests' in data:
            required_keys = get_required_keys()  # Get the required keys
            for test in data['tests']:
                # Set the logging level if specified in the test
                log_level = test.get('log', 'INFO')  # Default to DEBUG level
                logging_level = set_logging_level(log_level)
                logging.getLogger().setLevel(logging_level)

                try:
                    validate_test(test, required_keys)  # Validate test case
                    process_test(test, constants, saved_responses)  # Process the test case

                    # Check if the HTTP verb is valid
                    verb = test['request']['method'].upper()
                    check_verb_http(verb)

                    # Make the request
                    response = make_request(test['request'], constants, saved_responses)

                    # Save the response for future reference if needed
                    json_response, pretty_json = parse_json_response(response.text)
                    saved_responses[f"{test['name']}"] = json_response

                    # Validate the expected response
                    validate_expected_response(response, test['expected'])

                    logger.info(f"'OK' - {test['name']}")
                    results.append({'name': test['name'], 'status': 'OK', 'error': None})
                except Exception as e:
                    logger.error(f"Test '{test['name']}' failed: {e}")
                    results.append({'name': test['name'], 'status': 'FAIL', 'error': str(e)})

        else:
            logger.warning("No tests found in the YAML file.")

        # Print results summary using rich
        console.print("\n[bold magenta]Test Results Summary:[/bold magenta]")
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Test Name", style="dim", width=30)
        table.add_column("Status", justify="center")
        table.add_column("Error")

        for result in results:
            status = result['status']
            name = result['name']
            error = result['error'] if result['error'] else "-"
            table.add_row(name, status, error)

        console.print(table)
    else:
        logger.warning("Failed to load the test data from the YAML file.")


# Entry point of the script
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run API tests defined in YAML files.')
    parser.add_argument('test_files', nargs='*', help='YAML files containing the test cases.')
    args = parser.parse_args()

    if args.test_files:
        for test_file in args.test_files:
            if os.path.isfile(test_file):
                run_tests(test_file)
            else:
                logger.error(f"Error: the file '{test_file}' does not exist.")
    else:
        yml_files_found = False
        for file in os.listdir('.'):
            if file.endswith('.yml'):
                run_tests(file)
                yml_files_found = True

        if not yml_files_found:
            logger.warning("No YAML files found in the current directory.")
