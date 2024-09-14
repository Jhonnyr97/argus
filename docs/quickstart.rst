Quickstart
==========

Getting started with Argus is quick and easy! You have two options to run Argus: building the image locally or pulling the pre-built Docker image from Docker Hub.

1. **Clone the Repository**

   First, clone the Argus repository:

   .. code-block:: bash

      git clone https://github.com/Jhonnyr97/argus.git
      cd argus

2. **Run Argus with Docker**

   Argus can be run using Docker. You can either build the Docker image locally or use the pre-built image from Docker Hub.

   **Option 1: Build Locally**

   To build the image locally, run:

   .. code-block:: bash

      docker build -t my-python-tests .

   Then, run the Docker container with:

   .. code-block:: bash

      docker run --rm -it -v .:/app my-python-tests bash

   **Option 2: Use Pre-Built Docker Image**

   For an easier and faster setup, pull the pre-built image from Docker Hub:

   .. code-block:: bash

      docker pull nilthrojas/argus:latest

   Run the Docker container with:

   .. code-block:: bash

      docker run --rm -it -v .:/app nilthrojas/argus:latest bash

3. **Running Tests**

   Inside the Docker container, you can run your Argus tests using the following command:

   .. code-block:: bash

      python3 main.py

   This will execute all the tests defined in your YAML files. If you want to run specific test files, provide their names as arguments:

   .. code-block:: bash

      python3 main.py magic.yml test.yml

   **Alternative: Run Tests Directly**

   You can also run tests directly from your host machine without entering the container:

   .. code-block:: bash

      docker run --rm -v $(pwd):/app nilthrojas/argus:latest python3 main.py

4. **Viewing Results**

   After running the tests, Argus will display a formatted table showing the test results, including test names, pass/fail status, and any errors encountered.

   You can now explore and customize your tests with the example files provided in the repository!
