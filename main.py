import argparse
import os
import yaml
import logging
import re
import json
import requests
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, ValidationError
from rich.logging import RichHandler
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

# Initialize Rich console
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("API_Tester")

# Define data models
class RequestModel(BaseModel):
    method: str
    endpoint: str
    params: Optional[Dict[str, Any]] = {}
    headers: Optional[Dict[str, str]] = {}
    body: Optional[Any] = None

class ExpectedResponseModel(BaseModel):
    status: int
    response: Dict[str, Any]

class TestCase(BaseModel):
    name: str
    request: RequestModel
    expected: ExpectedResponseModel
    log: Optional[str] = "INFO"

class TestSuite(BaseModel):
    constants: Dict[str, Any] = {}
    tests: List[TestCase]

def set_logging_level(log_level: str) -> None:
    """Set the logging level based on the provided string."""
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    logger.setLevel(levels.get(log_level.upper(), logging.INFO))

def read_yaml(file_path: str) -> Dict[str, Any]:
    """Reads a YAML file and returns the contents as a dictionary."""
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        raise

def resolve_constants(constants: Dict[str, Any], data: Any) -> Any:
    """Recursively resolve constants in the data."""
    if isinstance(data, dict):
        return {key: resolve_constants(constants, value) for key, value in data.items()}
    elif isinstance(data, list):
        return [resolve_constants(constants, item) for item in data]
    elif isinstance(data, str):
        for key, value in constants.items():
            if isinstance(value, str):
                data = re.sub(r'\{' + re.escape(key) + r'\}', value, data)
        return data
    return data

def parse_json_response(response_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse the JSON response text and return a formatted string for logging."""
    try:
        response_json = json.loads(response_text)
        pretty_json = json.dumps(response_json, indent=4)
        return response_json, pretty_json
    except json.JSONDecodeError:
        logger.error("Response content is not valid JSON.")
        return None, None

def log_request_details(request: RequestModel):
    """Log the details of a request if log level is DEBUG."""
    if logger.level == logging.DEBUG:
        console.print(Panel(
            f"[bold]Request Details:[/bold]\n"
            f"Method: {request.method}\n"
            f"Endpoint: {request.endpoint}\n"
            f"Params: {json.dumps(request.params, indent=2)}\n"
            f"Headers: {json.dumps(request.headers, indent=2)}\n"
            f"Body: {json.dumps(request.body, indent=2) if request.body else 'None'}",
            title="Request",
            expand=False
        ))

def log_response_details(response: requests.Response):
    """Log the details of a response if log level is DEBUG."""
    if logger.level == logging.DEBUG:
        try:
            response_json = response.json()
            response_body = json.dumps(response_json, indent=2)
        except json.JSONDecodeError:
            response_body = response.text

        console.print(Panel(
            f"[bold]Response Details:[/bold]\n"
            f"Status Code: {response.status_code}\n"
            f"Headers: {json.dumps(dict(response.headers), indent=2)}\n"
            f"Body: {response_body}",
            title="Response",
            expand=False
        ))

def validate_expected_response(response: requests.Response, expected: ExpectedResponseModel) -> None:
    """Validate the actual response against the expected values."""
    console.print("[bold]Validating Response[/bold]")

    if response.status_code != expected.status:
        console.print(f"[red]❌ Status Code Mismatch: Expected {expected.status}, got {response.status_code}[/red]")
        raise ValueError(f"Expected status {expected.status}, but got {response.status_code}")
    else:
        console.print(f"[green]✓ Status Code Matches: {response.status_code}[/green]")

    response_json, _ = parse_json_response(response.text)
    if response_json is None:
        console.print("[red]❌ Response is not a valid JSON[/red]")
        raise ValueError("Response is not a valid JSON.")

    for key, value in expected.response.items():
        if key in response_json:
            if response_json[key] == value:
                console.print(f"[green]✓ '{key}' matches expected value[/green]")
            else:
                console.print(f"[red]❌ '{key}' mismatch: Expected {value}, got {response_json[key]}[/red]")
                raise ValueError(f"Mismatch in '{key}': Expected {value}, got {response_json[key]}")
        else:
            console.print(f"[yellow]⚠ '{key}' not found in response[/yellow]")


def make_request(request: RequestModel) -> requests.Response:
    """Make an HTTP request based on the provided request parameters."""
    try:
        log_request_details(request)
        response = requests.request(
            method=request.method,
            url=request.endpoint,
            params=request.params,
            headers=request.headers,
            json=request.body if isinstance(request.body, dict) else None,
            data=request.body if not isinstance(request.body, dict) else None
        )
        log_response_details(response)
        return response
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise

def run_tests(test_file: str) -> None:
    """Loads and processes the test file."""
    logger.info(f"Loading test file: {test_file}")
    data = read_yaml(test_file)

    try:
        test_suite = TestSuite(**data)
    except ValidationError as e:
        logger.error(f"Invalid test suite structure: {e}")
        return

    constants = test_suite.constants
    logger.info(f"Constants Loaded: {json.dumps(constants, indent=4)}")

    results = []

    for test in test_suite.tests:
        console.print(f"\n[bold cyan]Running Test: {test.name}[/bold cyan]")
        set_logging_level(test.log)

        try:
            resolved_test = resolve_constants(constants, test.dict())
            test = TestCase(**resolved_test)

            response = make_request(test.request)
            validate_expected_response(response, test.expected)

            console.print(f"[bold green]✓ Test Passed: {test.name}[/bold green]")
            results.append({'name': test.name, 'status': 'OK', 'error': None})
        except Exception as e:
            console.print(f"[bold red]❌ Test Failed: {test.name}[/bold red]")
            console.print(f"[red]Error: {str(e)}[/red]")
            results.append({'name': test.name, 'status': 'FAIL', 'error': str(e)})

    print_results_summary(results)

def print_results_summary(results: List[Dict[str, Any]]) -> None:
    """Print results summary using rich."""
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
        yml_files = [f for f in os.listdir('.') if f.endswith('.yml')]
        if yml_files:
            for file in yml_files:
                run_tests(file)
        else:
            logger.warning("No YAML files found in the current directory.")
