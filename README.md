# Argus: Streamline Your System Testing 

Argus is a Python tool that simplifies system testing by allowing you to write tests in YAML files. With Argus, you can easily describe your tests, make HTTP requests, and set expectations for the responses. Argus then runs the tests and provides you with a clear, concise summary of the results.
```
  .--.  .----.  .---. .-. .-. .----.
 / {} \ | {}  }/   __}| { } |{ {__  
/  /\  \| .-. \\  {_ }| {_} |.-._} }
`-'  `-'`-' `-' `---' `-----'`----' 
```
## Who is Argus?
In Greek mythology, Argus Panoptes was a giant with a hundred eyes. He was an all-seeing guardian, known for his keen observation and vigilance. Inspired by this mythical figure, Argus the tool aims to be your vigilant guardian in system testing, ensuring that your APIs perform exactly as expected.

## Quickstart

Getting started with Argus is as easy as 1, 2, 3:

1. Clone the repository.
2. Build a Docker image with `docker build -t my-python-tests .`.
3. Run the Docker image with `docker run --rm -it -v .:/app my-python-tests bash`.

## Crafting Your Tests

Argus lets you write your tests in straightforward YAML files. Each test should have:

- `name`: A unique identifier for your test.
- `request`: The HTTP method, endpoint, parameters, headers, and body.
- `expected`: The expected HTTP status and response.

Here's what a basic test might look like:

```yaml
name: "Test list all cards"
request:
  method: "GET"
  endpoint: "{base_url}/cards"
expected:
  status: 200
  response:
    type: "json"
    json:
      - key: "cards"
        type: "list"
```

## Running Your Masterpiece
To see Argus in action, use the command `python3 main.py`. You can even run specific tests by specifying the test files as arguments, like so: `python3 main.py magic.yml test.yml.

## Example Tests
We've provided several example tests for the Magic the Gathering API. They serve as templates for your own tests, showing you how to describe a test, make an HTTP request, and set expectations for the response.

## Results at a Glance
Immediately after running the tests, Argus presents you with a colored, formatted table of results. Each row represents a test, showcasing the test name, status (OK or FAIL), and any error message.

## Enhance Your Visual Feedback
Argus uses the Rich library to enhance your visual feedback, making it easier to read and understand the test results.

## Behind the Scenes
The Argus script is packed with numerous functions that handle different tasks, such as reading and processing the YAML files, validating the tests, making the HTTP requests, and validating the responses. The script's main function is `run_tests, which orchestrates the entire process of running the tests.

## Contributing
Argus is a collaborative project, and your contributions are more than welcome. Feel free to propose improvements, report issues, or enhance the functionalities. Together, we can make Argus even better!
