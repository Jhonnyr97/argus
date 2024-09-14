import argparse
import datetime
import json
import logging
import os
import re
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml
from box import Box
from pydantic import BaseModel, Field, field_validator
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

# Initialize Rich console
console = Console()

# Configure logging with Rich handler
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    datefmt='%H:%M:%S',
    handlers=[RichHandler()],
)
logger = logging.getLogger("API_Tester")


class HTTPRequestModel(BaseModel):
    """
    Model to validate HTTP verbs.

    Attributes:
        verb (str): The HTTP verb to validate. :no-index:
    """

    verb: str

    @field_validator('verb')
    def check_verb_http(cls, value: str) -> str:
        """
        Validates that the HTTP verb is one of the allowed verbs.

        Args:
            value (str): The HTTP verb to validate.

        Raises:
            ValueError: If the HTTP verb is not valid.

        Returns:
            str: The validated HTTP verb in uppercase.
        """
        valid_verbs = [
            'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'CONNECT', 'TRACE'
        ]
        if value.upper() not in valid_verbs:
            raise ValueError(f"Invalid HTTP verb: {value}")
        return value.upper()


class Validator:
    """
    Class containing methods for validating response data.
    """

    def __init__(self):
        """
        Initializes the Validator with a map of validation functions.
        """
        self.validation_map = {
            'type': self.validate_type,
            'equal': self.validate_equal,
            'not_equal': self.validate_not_equal,
            'contains': lambda k, v, e: self.validate_membership(k, v, e, should_contain=True),
            'not_contains': lambda k, v, e: self.validate_membership(k, v, e, should_contain=False),
            'not_empty': lambda k, v: self.validate_empty(k, v, should_be_empty=False),
            'empty': lambda k, v: self.validate_empty(k, v, should_be_empty=True),
            'regex': self.validate_regex,
            'date_format': self.validate_date_format,
            'range': self.validate_range,
        }

    def validate_type(self, expected_key: str, actual_value: Any, expected_type: str) -> None:
        """
        Validates the type of a given value against the expected type.

        Args:
            expected_key (str): The key being validated.
            actual_value (Any): The actual value to check.
            expected_type (str): The expected type as a string.

        Raises:
            ValueError: If the actual value does not match the expected type.
        """
        type_mapping = {
            "list": list,
            "dict": dict,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
        }
        if expected_type in type_mapping and not isinstance(actual_value, type_mapping[expected_type]):
            logger.error(
                f"Key '{expected_key}' is expected to be a {expected_type}, but got {type(actual_value).__name__}."
            )
            raise ValueError(
                f"Key '{expected_key}' is expected to be a {expected_type}, but got {type(actual_value).__name__}."
            )

    def validate_equal(self, expected_key: str, actual_value: Any, expected_value: Any) -> None:
        """
        Validates that a value is equal to the expected value.

        Args:
            expected_key (str): The key being validated.
            actual_value (Any): The actual value to check.
            expected_value (Any): The expected value.

        Raises:
            ValueError: If the actual value does not equal the expected value.
        """
        if actual_value != expected_value:
            logger.error(f"Key '{expected_key}' expected value '{expected_value}', but got '{actual_value}'.")
            raise ValueError(
                f"Key '{expected_key}' expected value '{expected_value}', but got '{actual_value}'."
            )

    def validate_not_equal(self, expected_key: str, actual_value: Any, expected_value: Any) -> None:
        """
        Validates that a value is not equal to the expected value.

        Args:
            expected_key (str): The key being validated.
            actual_value (Any): The actual value to check.
            expected_value (Any): The value that should not be equal.

        Raises:
            ValueError: If the actual value equals the expected value.
        """
        if actual_value == expected_value:
            logger.error(f"Key '{expected_key}' expected value not to be '{expected_value}', but got '{actual_value}'.")
            raise ValueError(
                f"Key '{expected_key}' expected value not to be '{expected_value}', but got '{actual_value}'."
            )

    def validate_membership(self, expected_key: str, actual_value: Any, expected_value: Any, should_contain: bool = True) -> None:
        """
        Validates that a string or list contains or does not contain a specified value.

        Args:
            expected_key (str): The key being validated.
            actual_value (Any): The actual value to check.
            expected_value (Any): The value that should or should not be present.
            should_contain (bool): Whether the value should be contained.

        Raises:
            ValueError: If the validation fails.
        """
        if isinstance(actual_value, (str, list)):
            check = expected_value in actual_value
            if check != should_contain:
                action = "contain" if should_contain else "not contain"
                logger.error(
                    f"Key '{expected_key}' ({type(actual_value).__name__}) should {action} '{expected_value}', but got '{actual_value}'."
                )
                raise ValueError(
                    f"Key '{expected_key}' ({type(actual_value).__name__}) should {action} '{expected_value}', but got '{actual_value}'."
                )
        else:
            logger.error(
                f"Key '{expected_key}' has unsupported type '{type(actual_value).__name__}'. Expected a string or list."
            )
            raise TypeError(
                f"Key '{expected_key}' has unsupported type '{type(actual_value).__name__}'. Expected a string or list."
            )

    def validate_empty(self, expected_key: str, actual_value: Any, should_be_empty: bool = True) -> None:
        """
        Validates that a value is empty or not empty based on the flag.

        Args:
            expected_key (str): The key being validated.
            actual_value (Any): The actual value to check.
            should_be_empty (bool): Whether the value should be empty.

        Raises:
            ValueError: If the validation fails.
        """
        is_empty = not actual_value
        if is_empty != should_be_empty:
            state = "empty" if should_be_empty else "not empty"
            logger.error(f"Key '{expected_key}' is expected to be {state}.")
            raise ValueError(f"Key '{expected_key}' is expected to be {state}.")

    def validate_regex(self, expected_key: str, actual_value: str, expected_regex: str) -> None:
        """
        Validates that a string matches the expected regex pattern.

        Args:
            expected_key (str): The key being validated.
            actual_value (str): The actual value to check.
            expected_regex (str): The regex pattern.

        Raises:
            ValueError: If the actual value does not match the regex.
        """
        if not re.match(expected_regex, actual_value):
            logger.error(f"Key '{expected_key}' does not match the regex pattern.")
            raise ValueError(f"Key '{expected_key}' does not match the regex pattern.")

    def validate_date_format(self, expected_key: str, actual_value: str, expected_format: str) -> None:
        """
        Validates that a date string matches the expected format.

        Args:
            expected_key (str): The key being validated.
            actual_value (str): The actual date string.
            expected_format (str): The expected date format.

        Raises:
            ValueError: If the date format does not match.
        """
        try:
            datetime.datetime.strptime(actual_value, expected_format)
        except ValueError:
            logger.error(f"Key '{expected_key}' does not match the expected date format.")
            raise ValueError(f"Key '{expected_key}' does not match the expected date format.")

    def validate_range(self, expected_key: str, actual_value: Any, expected_range: List[float]) -> None:
        """
        Validates that a value falls within the expected range.

        Args:
            expected_key (str): The key being validated.
            actual_value (Any): The actual value to check.
            expected_range (List[float]): The range as [min, max].

        Raises:
            ValueError: If the value is not within the range.
        """
        if not (expected_range[0] <= actual_value <= expected_range[1]):
            logger.error(f"Key '{expected_key}' is not within the expected range.")
            raise ValueError(f"Key '{expected_key}' is not within the expected range.")


class YAMLLoader:
    """
    Class to handle loading and resolving YAML test files.
    """

    def __init__(self, test_file: str):
        """
        Initializes the YAMLLoader.

        Args:
            test_file (str): The path to the test YAML file.
        """
        self.test_file = test_file
        self.constants = {}
        self.tests = []

    def load(self) -> Optional[Dict[str, Any]]:
        """
        Loads the YAML file.

        Returns:
            Optional[Dict[str, Any]]: The contents of the YAML file, or None if an error occurs.
        """
        try:
            with open(self.test_file, 'r') as file:
                data = yaml.safe_load(file)
                self.constants = data.get('constants', {})
                self.tests = data.get('tests', [])
                return data
        except Exception as e:
            logger.error(f"Error reading {self.test_file}: {e}")
            return None

    def resolve_constants(self, data: Any) -> Any:
        """
        Recursively resolves constants in the data by replacing placeholders with their actual values.

        Args:
            data (Any): The data to process.

        Returns:
            Any: The data with constants resolved.
        """
        if isinstance(data, dict):
            return {key: self.resolve_constants(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.resolve_constants(item) for item in data]
        elif isinstance(data, str):
            for key, value in self.constants.items():
                if isinstance(value, str):
                    data = re.sub(r'\{{' + re.escape(key) + r'\}}', value, data)
            return data
        return data


class ResponseHandler:
    """
    Class to handle saving and retrieving responses.
    """

    def __init__(self):
        """
        Initializes the ResponseHandler.
        """
        self.saved_responses = Box()
        self.saved_responses["results"] = []
        self.lock = threading.Lock()

    def save_response(self, test_name: str, response: requests.Response) -> None:
        """
        Saves the response for future reference.

        Args:
            test_name (str): The name of the test.
            response (requests.Response): The HTTP response.
        """
        json_response, _ = self.parse_json_response(response.text)
        with self.lock:
            self.saved_responses[test_name] = json_response

    def append_result(self, result: Dict[str, Any]) -> None:
        """
        Appends a test result to the results list.

        Args:
            result (Dict[str, Any]): The test result.
        """
        with self.lock:
            self.saved_responses["results"].append(result)

    def get_response_value(self, response_from: dict, param_key: str) -> Any:
        """
        Retrieves a value from a saved response.

        Args:
            response_from (dict): The details of the response to retrieve from.
            param_key (str): The parameter key.

        Raises:
            ValueError: If the response or key is not found.

        Returns:
            Any: The value retrieved from the saved response.
        """
        response_name = response_from['name']
        json_key = response_from['response']['json'][0]['key']
        with self.lock:
            if response_name not in self.saved_responses:
                error_message = f"Response '{response_name}' not found for parameter '{param_key}'."
                logger.error(error_message)
                raise ValueError(error_message)
            actual_value = self.navigate_json(self.saved_responses[response_name], json_key)
        if actual_value is None:
            error_message = f"Value for key '{json_key}' in response '{response_name}' is None."
            logger.error(error_message)
            raise ValueError(error_message)
        return actual_value

    @staticmethod
    def navigate_json(json_data: dict, key: str) -> Any:
        """
        Navigates through a nested JSON object using a dot-separated key.

        Args:
            json_data (dict): The JSON data.
            key (str): The dot-separated key to navigate.

        Raises:
            ValueError: If navigation fails.

        Returns:
            Any: The value found at the specified key.
        """
        try:
            json_box = Box(json_data, box_dots=True)
            return json_box[key]
        except Exception as e:
            logger.error(f"Key '{key}' in JSON Error: {e}")
            raise ValueError(f"Key '{key}' in JSON Error: {e}")

    @staticmethod
    def parse_json_response(response_text: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        Parses the JSON response text and returns a formatted string for logging.

        Args:
            response_text (str): The response text to parse.

        Returns:
            Tuple[Optional[dict], Optional[str]]: A tuple containing the JSON object and the pretty-printed JSON string.
        """
        try:
            response_json = json.loads(response_text)
            pretty_json = json.dumps(response_json, indent=4)
            return response_json, pretty_json
        except json.JSONDecodeError:
            logger.error("Response content is not valid JSON.")
            return None, None


class APITestRunner:
    """
    Class to execute API tests defined in YAML files.
    """

    def __init__(self, test_file: str):
        """
        Initializes the test runner.

        Args:
            test_file (str): The path to the test YAML file.
        """
        self.test_file = test_file
        self.yaml_loader = YAMLLoader(test_file)
        self.validator = Validator()
        self.response_handler = ResponseHandler()

    def run(self) -> None:
        """
        Executes the tests defined in the YAML file.
        """
        console.print(f"Loading test file: '{self.test_file}'")
        data = self.yaml_loader.load()
        if not data:
            logger.warning("Failed to load the test data from the YAML file.")
            return
        data = self.yaml_loader.resolve_constants(data)
        if 'tests' not in data:
            logger.warning("No tests found in the YAML file.")
            return
        self.run_tests()

    def run_tests(self) -> None:
        """
        Executes all tests, managing dependencies and threading.
        """
        independent_tests = []
        dependent_tests = []
        for test in self.yaml_loader.tests:
            if self.test_has_response_from(test):
                dependent_tests.append(test)
            else:
                independent_tests.append(test)
        threads = []
        for test in independent_tests:
            t = threading.Thread(
                target=self.run_single_test,
                args=(test,)
            )
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        for test in dependent_tests:
            self.run_single_test(test)
        self.print_results_summary()

    @staticmethod
    def test_has_response_from(test: dict) -> bool:
        """
        Checks if 'response_from' is present in the test.

        Args:
            test (dict): The test case.

        Returns:
            bool: True if 'response_from' is present, False otherwise.
        """
        return 'response_from' in json.dumps(test)

    def run_single_test(self, test: dict) -> None:
        """
        Executes a single test case.

        Args:
            test (dict): The test case.
        """
        # Set logging level directly
        log_level = test.get('log', 'INFO')
        logging_level = self.set_logging_level(log_level)
        logging.getLogger().setLevel(logging_level)

        # Check required keys
        required_keys = ['name', 'request', 'expected']
        missing_keys = [key for key in required_keys if key not in test]
        if missing_keys:
            logger.error(f"Test missing required keys: {', '.join(missing_keys)} in test: {test}")
            return

        logger.debug(f"Running test: {test['name']}")
        logger.debug(f"- Request: {json.dumps(test['request'], indent=4)}")
        logger.debug(f"- Expected: {json.dumps(test['expected'], indent=4)}")
        console.print(".", style="bold green", end="")

        # Measure start of test execution time
        start_time = time.time()

        try:
            self.process_test(test)
            self.check_verb_http(test)

            # Measure the time before making the request
            request_start_time = time.time()
            response = self.make_request(test['request'])
            # Measure the time after receiving the response
            request_end_time = time.time()

            self.log_response(response)
            self.response_handler.save_response(test['name'], response)

            self.validate_expected_response(response, test['expected'])

            # Measure end of test execution time
            end_time = time.time()

            # Calculate execution and response times
            execution_time = end_time - start_time
            response_time = request_end_time - request_start_time

            self.response_handler.append_result({
                'name': test['name'],
                'result': 'OK',
                'error': None,
                'execution_time': execution_time,  # Total test execution time
                'response_time': response_time  # API response time
            })
        except Exception as e:
            self.handle_test_failure(test['name'], e)

    @staticmethod
    def set_logging_level(log_level: str) -> int:
        """
        Sets the logging level based on the provided string.

        Args:
            log_level (str): The logging level as a string.

        Returns:
            int: The logging level as an integer.
        """
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
        }
        return levels.get(log_level.upper(), logging.INFO)

    def process_test(self, test: dict) -> None:
        """
        Processes a single test, resolving constants in the request and expected.

        Args:
            test (dict): The test case.
        """
        test['request'] = self.yaml_loader.resolve_constants(test['request'])
        if 'params' in test['request']:
            self.process_request_params(test['request']['params'])

        test['expected'] = self.yaml_loader.resolve_constants(test['expected'])
        if 'json' in test['expected'].get('response', {}):
            self.process_expected_json(test['expected']['response']['json'])

    def process_request_params(self, params: Dict[str, Any]) -> None:
        """
        Processes parameters in the request.

        Args:
            params (Dict[str, Any]): The request parameters.
        """
        for param_key, param_value in params.items():
            if isinstance(param_value, dict) and 'response_from' in param_value:
                actual_value = self.response_handler.get_response_value(param_value['response_from'], param_key)
                params[param_key] = actual_value

    def process_expected_json(self, expected_json: List[Dict[str, Any]]) -> None:
        """
        Processes the expectations in the 'json' field of the expected response.

        Args:
            expected_json (List[Dict[str, Any]]): The expectations on the JSON response.
        """
        for item in expected_json:
            for key, value in item.items():
                if isinstance(value, dict) and 'response_from' in value:
                    actual_value = self.response_handler.get_response_value(value['response_from'], key)
                    item[key] = actual_value

    def make_request(self, request: dict) -> requests.Response:
        """
        Makes an HTTP request based on the provided request parameters.

        Args:
            request (dict): The request details.

        Raises:
            ValueError: If the HTTP method is unsupported.
            Exception: If the request fails.

        Returns:
            requests.Response: The HTTP response.
        """
        method = request['method'].upper()
        endpoint = request['endpoint']
        params = request.get('params', {})
        headers = request.get('headers', {})
        body = request.get('body')

        try:
            response = requests.request(method, endpoint, params=params, json=body, headers=headers)
            logger.debug(f"Response Status Code: {response.status_code}")
            return response
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"Request failed: {e}")

    def check_verb_http(self, test: dict) -> None:
        """
        Validates the HTTP verb in the test.

        Args:
            test (dict): The test case.

        Raises:
            ValidationError: If the HTTP verb is invalid.
        """
        verb = test['request']['method']
        HTTPRequestModel(verb=verb)

    def validate_expected_response(self, response: requests.Response, expected: dict) -> None:
        """
        Validates the actual response against the expected values.

        Args:
            response (requests.Response): The HTTP response.
            expected (dict): The expected response details.

        Raises:
            ValueError: If the validation fails.
        """
        expected_status = expected.get('status')
        if response.status_code != expected_status:
            logger.error(f"Expected status {expected_status}, but got {response.status_code}")
            raise ValueError(f"Expected status {expected_status}, but got {response.status_code}")

        response_json, _ = ResponseHandler.parse_json_response(response.text)
        if response_json is None:
            raise ValueError("Response is not a valid JSON.")

        if expected.get('response', {}).get('type') == 'json':
            for item in expected['response']['json']:
                key = item['key']
                actual_value = ResponseHandler.navigate_json(response_json, key)

                for validation_key in item:
                    if validation_key == 'key':
                        continue
                    validation_function = self.validator.validation_map.get(validation_key)
                    if validation_function:
                        if validation_key in ['empty', 'not_empty']:
                            validation_function(key, actual_value)
                        else:
                            validation_function(key, actual_value, item[validation_key])

    def log_response(self, response: requests.Response) -> None:
        """
        Logs the response from a request.

        Args:
            response (requests.Response): The HTTP response.
        """
        try:
            logger.debug(f"- Response: {json.dumps(response.json(), indent=4)}")
        except json.JSONDecodeError:
            logger.debug(f"- Response Text: {response.text}")

    def handle_test_failure(self, test_name: str, error: Exception) -> None:
        """
        Handles a test failure.

        Args:
            test_name (str): The name of the test.
            error (Exception): The exception that occurred.
        """
        logger.error(f"Test '{test_name}' failed: {error}")
        self.response_handler.append_result({
            'name': test_name,
            'result': 'Failed',
            'error': str(error),
            'execution_time': 'N/A',
            'response_time': 'N/A'
        })

    def print_results_summary(self) -> None:
        """
        Prints a summary of test results.
        """
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="white")
        table.add_column("Result")
        table.add_column("Error", style="red")
        table.add_column("Execution Time (s)", style="yellow")  # Adds execution time column
        table.add_column("Response Time (s)", style="cyan")  # Adds response time column

        for result in self.response_handler.saved_responses.results:
            status = "[green]OK[/green]" if result['result'] == 'OK' else "[red]Failed[/red]"
            exec_time = f"{result.get('execution_time', 'N/A'):.2f}" if isinstance(result.get('execution_time'), float) else result.get('execution_time', 'N/A')
            resp_time = f"{result.get('response_time', 'N/A'):.2f}" if isinstance(result.get('response_time'), float) else result.get('response_time', 'N/A')
            table.add_row(
                result['name'],
                status,
                result['error'] or "",
                exec_time,  # Shows execution time
                resp_time  # Shows response time
            )

        console.print("\n")
        console.print(table)


def main():
    """
    Main entry point of the script.
    """
    parser = argparse.ArgumentParser(description='Run API tests defined in YAML files.')
    parser.add_argument('test_files', nargs='*', help='YAML files containing the test cases.')
    args = parser.parse_args()

    if args.test_files:
        for test_file in args.test_files:
            if os.path.isfile(test_file):
                runner = APITestRunner(test_file)
                runner.run()
            else:
                logger.error(f"Error: the file '{test_file}' does not exist.")
                sys.exit(1)
    else:
        yml_files_found = False
        for file in os.listdir('.'):
            if file.endswith('.yml') or file.endswith('.yaml'):
                runner = APITestRunner(file)
                runner.run()
                yml_files_found = True

        if not yml_files_found:
            logger.warning("No YAML files found in the current directory.")
            sys.exit(1)


if __name__ == '__main__':
    main()
