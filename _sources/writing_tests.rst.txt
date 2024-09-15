####################
Writing Tests
####################

Argus allows you to define system tests in simple YAML files. This section will guide you through creating your first tests, explaining the structure of the files and the various options available to ensure your frontend remains intact.

**************************
Introduction to YAML Tests
**************************

Each test in Argus is defined within a YAML file and consists of three main sections:

1. **`name`**: A unique identifier for the test.
2. **`request`**: Details of the HTTP request to be made.
3. **`expected`**: The expected outcome of the request.

======================
Basic Test Structure
======================

Here is a basic example of a YAML test file:

.. code-block:: yaml

    name: "Test list all cards"
    description: "Verify that the endpoint returns a list of cards."
    request:
      method: "GET"
      endpoint: "{{base_url}}/cards"
      params:
        page: 1
        pageSize: "{{default_page_size}}"
    expected:
      status: 200
      response:
        type: "json"
        json:
          - key: "cards"
            type: "list"
            length: "{{default_page_size}}"

---------------------------------
Detailed Breakdown of Test Fields
---------------------------------

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
`name`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A unique name for the test, used to identify it in the results.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
`description`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An optional field that describes the purpose of the test.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
`request`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Defines the HTTP request to be made.

- **`method`**: The HTTP method to use (e.g., GET, POST).
- **`endpoint`**: The API endpoint to call. It can include constants like `{{base_url}}`.
- **`params`**: (Optional) Query parameters for the request.
- **`headers`**: (Optional) HTTP headers to include in the request.
- **`body`**: (Optional) JSON body for POST/PUT requests.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
`expected`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Defines the expected response from the request.

- **`status`**: The expected HTTP status code (e.g., 200).
- **`response`**:
- **`type`**: The expected type of response (e.g., `json`).
- **`json`**: A list of expectations for the JSON response data.
- **`key`**: The JSON key to validate.
- **Validation Rules**: Such as `type`, `equal`, `not_equal`, `contains`, `regex`, etc.

======================
Using Constants
======================

You can define constants to reuse values across your tests. Constants are defined in the `constants` section of the YAML file.

**Example:**

.. code-block:: yaml

    constants:
      base_url: "https://api.magicthegathering.io/v1"
      default_page_size: 10

    tests:
      - name: "Test list all cards"
        request:
          method: "GET"
          endpoint: "{{base_url}}/cards"
          params:
            page: 1
            pageSize: "{{default_page_size}}"
        expected:
          status: 200
          response:
            type: "json"
            json:
              - key: "cards"
                type: "list"
                length: "{{default_page_size}}"

======================
Handling Dependencies
======================

Tests can depend on responses from previous tests using the `response_from` field. This allows you to chain tests and use dynamic data.

**Example:**

.. code-block:: yaml

    - name: "Test filter cards by name with response"
      request:
        method: "GET"
        endpoint: "{{base_url}}/cards"
        params:
          name:
            response_from:
              name: "Test filter cards by name"
              response:
                json:
                  - key: "cards[0].name"
      expected:
        status: 200
        response:
          type: "json"
          json:
            - key: "cards[0].name"
              equal:
                response_from:
                  name: "Test filter cards by name"
                  response:
                    json:
                      - key: "cards[0].name"

In this example, the `name` parameter is populated with the value extracted from the response of the `"Test filter cards by name"` test.

======================
Validation Rules
======================

Argus supports various validation rules to ensure that API responses meet your expectations:

- **`type`**: Checks the data type (e.g., `list`, `dict`, `str`).
- **`equal`**: Asserts that a value equals the expected value.
- **`not_equal`**: Asserts that a value does not equal the expected value.
- **`contains`**: Checks if a list or string contains a specific value.
- **`not_contains`**: Checks if a list or string does not contain a specific value.
- **`regex`**: Validates strings against a regular expression.
- **`date_format`**: Validates date strings against a specified format.
- **`range`**: Asserts that a numeric value falls within a specified range.
- **`empty`** / **`not_empty`**: Checks if a value is empty or not.

======================
Creating a Test File
======================

To create a new test, follow these steps:

1. **Define Constants (Optional)**

   If your test uses repeated values, define them in the `constants` section.

   .. code-block:: yaml

       constants:
         base_url: "https://api.magicthegathering.io/v1"

2. **Add a New Test**

   Insert a new block under the `tests` section.

   .. code-block:: yaml

       - name: "Test name"
         description: "Description of the test."
         request:
           method: "GET"
           endpoint: "{{base_url}}/cards"
           params:
             name: "Black Lotus"
         expected:
           status: 200
           response:
             type: "json"
             json:
               - key: "cards"
                 type: "list"
               - key: "cards[0].name"
                 equal: "Black Lotus"

3. **Save the File**

   Save your YAML file in the tests directory, for example, `tests/magic.yml`.

======================
Complete Test Example
======================

Here is a complete example of a YAML test file that verifies various aspects of the cards endpoint:

.. code-block:: yaml

    constants:
      base_url: "https://api.magicthegathering.io/v1"
      default_page_size: 10

    tests:
      - name: "Test list all cards with pagination"
        description: "Verify that the endpoint returns a list of cards with pagination."
        request:
          method: "GET"
          endpoint: "{{base_url}}/cards"
          params:
            page: 1
            pageSize: "{{default_page_size}}"
        expected:
          status: 200
          response:
            type: "json"
            json:
              - key: "cards"
                type: "list"
                length: "{{default_page_size}}"

      - name: "Test filter cards by name"
        description: "Verify that the endpoint filters cards by name."
        request:
          method: "GET"
          endpoint: "{{base_url}}/cards"
          params:
            name: "Black Lotus"
        expected:
          status: 200
          response:
            type: "json"
            json:
              - key: "cards"
                type: "list"
              - key: "cards[0].name"
                equal: "Black Lotus"

      - name: "Test filter cards by name and check image URL"
        description: "Verify that the endpoint filters cards by name and validates the image URL."
        request:
          method: "GET"
          endpoint: "{{base_url}}/cards"
          params:
            name: "Black Lotus"
        expected:
          status: 200
          response:
            type: "json"
            json:
              - key: "cards"
                type: "list"
              - key: "cards[0].imageUrl"
                regex: 'https?:\/\/[a-zA-Z0-9\-_\.]+(\.[a-zA-Z]{2,})(\/[a-zA-Z0-9\-_\.]*)*(\?[a-zA-Z0-9=&_]*)?'

      - name: "Test invalid request returns error"
        description: "Verify that an invalid request returns an error."
        request:
          method: "GET"
          endpoint: "{{base_url}}/invalid_endpoint"
          params:
            invalid_param: "invalid"
        expected:
          status: 404
          response:
            type: "json"
            json:
              - key: "error"
                contains: "not-found"

================================
Best Practices for Writing Tests
================================

- **Clear Naming**: Assign descriptive names to your tests to easily understand the results.
- **Detailed Descriptions**: Use the `description` field to explain the purpose of the test.
- **Reuse Constants**: Define constants to avoid repetition and make maintenance easier.
- **Comprehensive Validations**: Utilize various validation rules to cover different aspects of the response.
- **Manage Dependencies**: If a test depends on another's response, use `response_from` to maintain consistency.

======================
Conclusion
======================

Writing tests with Argus is straightforward and intuitive thanks to well-structured YAML files. By following this guide, you'll be able to define effective tests that ensure your APIs function correctly. For more examples and details, refer to the sample test files included in the repository.
