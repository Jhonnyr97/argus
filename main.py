import argparse
import os
from typing import Dict, Any

import yaml
import logging
import re
import json
import requests
from box import Box
from rich.logging import RichHandler
from rich.console import Console
from rich.table import Table
from pydantic import BaseModel, validator, field_validator, Field, ValidationError

# Initialize Rich console
console = Console()

# ANSI escape sequences for colored logging
logging.basicConfig(level=logging.INFO,
                    format='%(message)s',
                    datefmt='%H:%M:%S',
                    handlers=[RichHandler()])

logger = logging.getLogger("API_Tester")


class HTTPRequestModel(BaseModel):
    verb: str

    @field_validator('verb')
    def check_verb_http(cls, value):
        valid_verbs = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'CONNECT', 'TRACE']
        if value not in valid_verbs:
            raise ValueError(f"Invalid HTTP verb: {value}")
        return value


class RequestModel(BaseModel):
    method: str
    endpoint: str


# Define a Pydantic model for the test structure
class TestModel(BaseModel):
    request: RequestModel
    extra_data: Dict[str, Any] = Field(default_factory=dict)  # To allow additional data


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


# Function to validate the test using Pydantic
def validate_test(test: dict, required_keys: list):
    """Validates that all required keys are present in the test."""

    # Check for missing required keys
    missing_keys = [key for key in required_keys if key not in test]
    if missing_keys:
        logger.error(f"Test missing required keys: {', '.join(missing_keys)} in test: {test}")
        raise ValueError(f"Test is invalid due to missing keys: {', '.join(missing_keys)}")

    # Validate the request structure using Pydantic
    try:
        TestModel(**test)
    except ValidationError as e:
        logger.error(f"Test validation failed: {e}")
        raise ValueError(f"Test structure is invalid: {e}")


def set_logging_level(log_level):
    """Set the logging level based on the provided string."""
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
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
    """Validate the type of given value against the expected type."""
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
        process_request(test, constants, saved_responses)

    if 'expected' in test and isinstance(test['expected'], dict):
        process_expected(test, constants, saved_responses)


def process_request(test, constants, saved_responses):
    """Process the request part of the test."""
    test['request'] = resolve_constants(constants, test['request'])

    if 'params' in test['request']:
        process_request_params(test['request']['params'], saved_responses)


def process_request_params(params, saved_responses):
    """Process parameters in the request."""
    for param_key, param_value in params.items():
        if isinstance(param_value, dict) and 'response_from' in param_value:
            actual_value = get_value_from_saved_response(saved_responses, param_value['response_from'], param_key)
            params[param_key] = actual_value


def process_expected(test, constants, saved_responses):
    """Process the expected part of the test."""
    test['expected'] = resolve_constants(constants, test['expected'])

    for i, keys in enumerate(test['expected']['response']['json']):
        for real_key, value in keys.items():
            if isinstance(value, dict) and 'response_from' in value:
                actual_value = get_value_from_saved_response(saved_responses, value['response_from'], real_key)
                test['expected']['response']['json'][i][real_key] = actual_value


def get_value_from_saved_response(saved_responses, response_from, param_key):
    """Retrieve a value from a saved response."""
    response_name = response_from['name']
    json_key = response_from['response']['json'][0]['key']

    actual_value = saved_responses[response_name][json_key]

    if actual_value is None:
        error_message = f"Response '{response_name}' not found for parameter '{param_key}'."
        logger.error(error_message)
        raise ValueError(error_message)

    return actual_value


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


def check_verb_http(test):
    verb = test['request']['method'].upper()
    HTTPRequestModel(verb=verb)


def run_tests(test_file):
    """Loads and processes the test file."""
    console.print(f"Loading test file: '{test_file}'")
    data = read_yaml(test_file)

    if not data:
        logger.warning("Failed to load the test data from the YAML file.")
        return

    constants = data.get('constants', {})
    data = resolve_constants(constants, data)
    saved_responses = Box(box_dots=True)
    saved_responses["results"] = []

    if 'tests' not in data:
        logger.warning("No tests found in the YAML file.")
        return

    for test in data['tests']:
        run_single_test(test, constants, saved_responses)

    print_results_summary(saved_responses.results)


def run_single_test(test, constants, saved_responses):
    """Runs a single test case."""
    set_up_logging(test)
    logger.debug(f"Running test: {test['name']}")
    logger.debug(f"- Request: {json.dumps(test['request'], indent=4)}")
    logger.debug(f"- Expected: {json.dumps(test['expected'], indent=4)}")
    console.print(".", style="bold green", end="")

    try:
        validate_test(test, get_required_keys())
        process_test(test, constants, saved_responses)
        check_verb_http(test)

        response = make_request(test['request'], constants, saved_responses)
        log_response(response)
        save_response(test['name'], response, saved_responses)

        validate_expected_response(response, test['expected'])

        saved_responses["results"].append({
            'name': test['name'],
            'result': 'OK',
            'error': None
        })
    except Exception as e:
        handle_test_failure(test['name'], e, saved_responses)


def set_up_logging(test):
    """Sets up logging for a test."""
    log_level = test.get('log', 'INFO')
    logging_level = set_logging_level(log_level)
    logging.getLogger().setLevel(logging_level)


def log_response(response):
    """Logs the response from a request."""
    logger.debug(f"- Response: {json.dumps(response.json(), indent=4)}")


def save_response(test_name, response, saved_responses):
    """Saves the response for future reference."""
    json_response, _ = parse_json_response(response.text)
    saved_responses[test_name] = json_response


def handle_test_failure(test_name, error, saved_responses):
    """Handles a test failure."""
    logger.error(f"Test '{test_name}' failed: {error}")
    saved_responses["results"].append({
        'name': test_name,
        'response': None,
        'result': 'Failed',
        'error': str(error)
    })


def print_results_summary(results):
    """Prints a summary of test results."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="white")
    table.add_column("Result")
    table.add_column("Error", style="red")

    for result in results:
        status = "[green]OK[/green]" if result['result'] == 'OK' else "[red]Failed[/red]"
        table.add_row(result['name'], status, result['error'] or "")

    console.print("\n")
    console.print(table)


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
