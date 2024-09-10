from ruamel.yaml import YAML
import json
import argparse
import os

yaml = YAML()

def convert_postman(postman_collection_path, output_yaml_path):
    # Check if the Postman file exists
    if not os.path.exists(postman_collection_path):
        print(f"Error: The file '{postman_collection_path}' does not exist.")
        return

    # Load the Postman collection JSON file
    with open(postman_collection_path, 'r') as postman_file:
        try:
            postman_collection = json.load(postman_file)
        except json.JSONDecodeError as e:
            print(f"Error reading JSON file: {e}")
            return

    # Initialize the base structure for Argus YAML
    argus_yaml = {
        "constants": {},
        "tests": []
    }

    # Add Postman variables to the constants section
    if "variable" in postman_collection:
        for variable in postman_collection["variable"]:
            key = variable['key']
            value = variable['value']
            argus_yaml["constants"][key] = value

    # Iterate through each item in the Postman collection
    for item in postman_collection.get('item', []):
        body_content = item['response'][0]['body']

        if isinstance(body_content, str):
            body_json = json.loads(body_content)
        else:
            body_json = body_content

        first_key = next(iter(body_json.keys()))

        host = item['request']['url']['host'][0]
        path = "/".join(item['request']['url']['path'])

        # Build each test entry
        test_entry = {
            "name": f"Test {item['name']}",
            "description": f"Verify that the {item['name']} endpoint works as expected.",
            "request": {
                "method": item['request']['method'],
                "endpoint": f"{host}/{path}",
                "params": {param['key']: param['value'] for param in item['request'].get('url', {}).get('query', [])}
            },
            "expected": {
                "status": 200,
                "response": {
                    "type": "json",
                    "json": [{
                        "key": f"{first_key}",
                        "type": f"{type(body_json[first_key]).__name__}",
                        "length": len(body_json[first_key])
                    }]
                }
            }
        }

        # Add the test to the Argus YAML structure
        argus_yaml["tests"].append(test_entry)

    # Save the Argus YAML to file
    with open(output_yaml_path, 'w') as yaml_file:
        yaml.dump(argus_yaml, yaml_file)

    print(f"Conversion complete! YAML saved to: {output_yaml_path}")

if __name__ == "__main__":
    # Argument parsing for command line
    parser = argparse.ArgumentParser(description="Convert a Postman collection JSON into an Argus YAML file.")
    parser.add_argument('postman_collection', type=str, help='Path to the Postman JSON file')
    parser.add_argument('output_yaml', type=str, help='Path to the output YAML file')

    # Parse the arguments
    args = parser.parse_args()

    # Start the conversion process
    convert_postman(args.postman_collection, args.output_yaml)
