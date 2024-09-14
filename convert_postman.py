"""
postman_to_argus.py
===================

A script to convert Postman collection JSON files into Argus YAML test files.

This script parses Postman collections, extracts requests, parameters, headers,
and expected responses, and formats them into YAML files compatible with the
Argus testing framework.

Usage:
    python postman_to_argus.py path/to/postman_collection.json path/to/output_argus.yaml
"""

from ruamel.yaml import YAML
import json
import argparse
import os
from urllib.parse import urlparse, parse_qs
from typing import Any, Dict, List, Optional

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)


def convert_postman(postman_collection_path: str, output_yaml_path: str) -> None:
    """
    Convert a Postman collection JSON file into an Argus YAML file.

    This function reads a Postman collection, extracts necessary information,
    and writes it into a YAML file compatible with the Argus testing framework.

    Args:
        postman_collection_path (str): The file path to the Postman collection JSON.
        output_yaml_path (str): The desired file path for the output Argus YAML file.

    Raises:
        FileNotFoundError: If the Postman collection file does not exist.
        json.JSONDecodeError: If the Postman collection file contains invalid JSON.
    """
    # Verify that the Postman file exists
    if not os.path.exists(postman_collection_path):
        raise FileNotFoundError(f"The file '{postman_collection_path}' does not exist.")

    # Load the Postman collection JSON file
    with open(postman_collection_path, 'r', encoding='utf-8') as postman_file:
        try:
            postman_collection = json.load(postman_file)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Error reading JSON file: {e}", e.doc, e.pos)

    # Initialize the base structure for Argus YAML
    argus_yaml: Dict[str, Any] = {
        "constants": {},
        "tests": []
    }

    # Add Postman variables to the constants section
    if "variable" in postman_collection:
        for variable in postman_collection["variable"]:
            key = variable['key']
            value = variable.get('value', '')
            argus_yaml["constants"][key] = value

    def process_items(items: List[Dict[str, Any]], parent_name: str = "") -> None:
        """
        Recursively process items in the Postman collection, handling nested folders.

        Args:
            items (List[Dict[str, Any]]): A list of items (requests or folders) from the Postman collection.
            parent_name (str, optional): The hierarchical name prefix for nested items. Defaults to "".
        """
        for item in items:
            current_name = f"{parent_name} > {item['name']}" if parent_name else item['name']
            if 'item' in item:
                # It's a folder, process recursively
                process_items(item['item'], parent_name=current_name)
            else:
                # It's a request, process the request
                process_request(item, current_name)

    def process_request(item: Dict[str, Any], test_name: str) -> None:
        """
        Process a single Postman request and add it as a test to the Argus YAML.

        Args:
            item (Dict[str, Any]): The Postman request item.
            test_name (str): The hierarchical name of the test.
        """
        request = item.get('request', {})
        response = item.get('response', [])
        if not response:
            print(f"Skipping test '{test_name}' as no response body was found.")
            return

        # Use the first available response
        first_response = response[0]
        body_content = first_response.get('body', '')

        # Attempt to load the body as JSON, otherwise treat it as a string
        try:
            body_json = json.loads(body_content) if isinstance(body_content, str) else body_content
        except json.JSONDecodeError:
            body_json = body_content

        # Extract the first key from the JSON body for validation example
        first_key = next(iter(body_json.keys()), None) if isinstance(body_json, dict) else None

        # Construct the endpoint by replacing variables and separating path and query parameters
        url = request.get('url', {})
        raw_url = url.get('raw', '')
        parsed_url = urlparse(raw_url)

        # Replace Postman variables with Argus-compatible syntax in the path
        path = parsed_url.path
        for variable in argus_yaml["constants"]:
            path = path.replace(f"{{{{{variable}}}}}", f"{{{{{variable}}}}}")

        # Extract and process query parameters
        query_params = parse_qs(parsed_url.query)
        params: Dict[str, str] = {}
        for key, values in query_params.items():
            # Postman can have multiple values for the same key; Argus expects single values
            value = values[0] if values else ''
            if value.startswith("{{") and value.endswith("}}"):
                params[key] = value
            else:
                params[key] = value

        # Additionally, if there are query parameters defined separately, they should be merged
        if 'query' in url:
            for param in url['query']:
                key = param.get('key')
                value = param.get('value', '')
                if value.startswith("{{") and value.endswith("}}"):
                    params[key] = value
                else:
                    params[key] = value

        # Extract headers, if present
        headers: Dict[str, str] = {}
        if 'header' in request:
            for header in request['header']:
                key = header.get('key')
                value = header.get('value', '')
                if value.startswith("{{") and value.endswith("}}"):
                    headers[key] = value
                else:
                    headers[key] = value

        # Extract the request body, if present
        body: Optional[Any] = None
        if 'body' in request:
            body_mode = request['body'].get('mode')
            if body_mode == 'raw':
                raw_body = request['body'].get('raw', '')
                try:
                    body = json.loads(raw_body)
                except json.JSONDecodeError:
                    body = raw_body
            elif body_mode == 'urlencoded':
                body = {param['key']: param.get('value', '') for param in request['body'].get('urlencoded', [])}
            elif body_mode == 'formdata':
                body = {param['key']: param.get('value', '') for param in request['body'].get('formdata', [])}
            # You can add more body modes if necessary

        # Build the test entry
        test_entry: Dict[str, Any] = {
            "name": f"Test {test_name}",
            "description": item.get('description', f"Verify that the {test_name} endpoint works as expected."),
            "request": {
                "method": request.get('method', 'GET').upper(),
                "endpoint": path,
            },
            "expected": {
                "status": 200,  # Default status, can be customized if needed
                "response": {
                    "type": "json",
                }
            }
        }

        # Add query parameters if present
        if params:
            test_entry["request"]["params"] = params

        # Add headers if present
        if headers:
            test_entry["request"]["headers"] = headers

        # Add the body if present
        if body:
            test_entry["request"]["body"] = body

        # Add validations based on the response body
        if first_key:
            # Determine the type and length if applicable
            value = body_json[first_key] if isinstance(body_json, dict) else body_json
            value_type = type(value).__name__ if value is not None else "null"
            value_length = len(value) if isinstance(value, (list, dict, str)) else None

            validation: Dict[str, Any] = {
                "key": first_key,
                "type": value_type
            }
            if value_length is not None:
                validation["length"] = value_length

            test_entry["expected"]["response"]["json"] = [validation]

        # Add additional validations based on response properties
        # You can extend this part to include more complex validations

        # Add the test to the Argus YAML structure
        argus_yaml["tests"].append(test_entry)

    # Start processing the collection items
    process_items(postman_collection.get('item', []))

    # Save the Argus YAML file
    with open(output_yaml_path, 'w', encoding='utf-8') as yaml_file:
        yaml.dump(argus_yaml, yaml_file)

    print(f"Conversion complete! YAML saved to: {output_yaml_path}")


def main() -> None:
    """
    Main entry point of the script.

    Parses command-line arguments and initiates the conversion process.
    """
    parser = argparse.ArgumentParser(description="Convert a Postman collection JSON into an Argus YAML file.")
    parser.add_argument('postman_collection', type=str, help='Path to the Postman JSON file')
    parser.add_argument('output_yaml', type=str, help='Path to the output YAML file')

    # Parse the arguments
    args = parser.parse_args()

    try:
        # Start the conversion process
        convert_postman(args.postman_collection, args.output_yaml)
    except Exception as e:
        print(f"An error occurred during conversion: {e}")
        exit(1)


if __name__ == "__main__":
    main()
