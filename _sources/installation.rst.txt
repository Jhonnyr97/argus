Installation
============

Getting started with Argus is as easy as 1, 2, 3:

1. **Clone the Repository**

   Begin by cloning the Argus repository to your local machine. Ensure you have [Git](https://git-scm.com/) installed before proceeding.

   .. code-block:: bash

      git clone https://github.com/Jhonnyr97/argus.git

   Navigate into the cloned repository directory:

   .. code-block:: bash

      cd argus

2. **Build the Docker Image**

   Argus uses Docker to provide a consistent testing environment. You can either build the image locally or pull the pre-built image from Docker Hub.

   **Option 1: Build Locally**

   Build the Docker image using the provided `Dockerfile`:

   .. code-block:: bash

      docker build -t my-python-tests .

   **Option 2: Use Pre-Built Image**

   Alternatively, you can pull the pre-built Docker image directly from Docker Hub:

   .. code-block:: bash

      docker pull nilthrojas/argus:latest

3. **Run the Docker Image**

   Once you have the Docker image, you can run it to start testing with Argus. Use one of the following commands:

   **Option 1: Run Locally Built Image**

   .. code-block:: bash

      docker run --rm -it -v .:/app my-python-tests bash

   **Option 2: Run Pre-Built Docker Hub Image**

   .. code-block:: bash

      docker run --rm -it -v .:/app nilthrojas/argus:latest bash

   This command starts the Docker container and mounts the current directory into `/app` inside the container. Once inside, you can execute your tests.

   **Run Tests Directly**

   If you prefer to run the tests directly without entering the container, you can do so with:

   .. code-block:: bash

      docker run --rm -v $(pwd):/app nilthrojas/argus:latest python3 main.py
