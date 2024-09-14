####################
Contributing
####################

We welcome contributions to Argus! Whether you're fixing bugs, adding new features, improving documentation, or providing feedback, your participation helps make Argus better for everyone.

*********************
How to Contribute
*********************

Follow these steps to contribute to the Argus project:

1. **Fork the Repository**

   Click the "Fork" button at the top-right corner of the [Argus GitHub repository](https://github.com/yourusername/argus) to create your own copy of the repository.

2. **Clone Your Fork**

   Clone your forked repository to your local machine:

   .. code-block:: bash

      git clone https://github.com/Jhonnyr97/argus.git
      cd argus

3. **Create a New Branch**

   Create a new branch for your feature or bugfix. Use a descriptive name for the branch to indicate the purpose of your changes:

   .. code-block:: bash

      git checkout -b feature/your-feature-name

4. **Make Your Changes**

   Implement your changes in the codebase. Ensure that your code adheres to the project's coding standards and includes appropriate tests.

5. **Run Tests**

   Before committing your changes, run the existing tests to ensure that your changes do not break any functionality:

   .. code-block:: bash

      python3 main.py

   If you've added new features or made changes that require new tests, please include them.

6. **Commit Your Changes**

   Commit your changes with a clear and descriptive commit message:

   .. code-block:: bash

      git add .
      git commit -m "Add feature X to enhance Y"

7. **Push to Your Fork**

   Push your changes to your forked repository on GitHub:

   .. code-block:: bash

      git push origin feature/your-feature-name

8. **Create a Pull Request**

   Navigate to the original Argus repository on GitHub and click the "Compare & pull request" button. Provide a clear description of your changes and submit the pull request.

*********************
Reporting Issues
*********************

If you encounter any issues or have suggestions for improvements, please open an issue in the [Argus GitHub Issues](https://github.com/yourusername/argus/issues) section. When reporting a bug, include the following information:

- **Description**: A clear and concise description of the problem.
- **Steps to Reproduce**: Detailed steps to reproduce the issue.
- **Expected Behavior**: What you expected to happen.
- **Actual Behavior**: What actually happened.
- **Screenshots**: If applicable, add screenshots to help explain your problem.
- **Environment**: Include information about your system environment (e.g., OS, Python version).

*********************
Code of Conduct
*********************

Please adhere to our [Code of Conduct](CODE_OF_CONDUCT.rst) when interacting with the Argus community. We expect everyone to be respectful, inclusive, and considerate.

*********************
Style Guide
*********************

To maintain consistency across the project, please follow these style guidelines:

======================
Code Style
======================

- **Python Standards**: Follow [PEP 8](https://pep8.org/) for Python code.
- **Naming Conventions**: Use clear and descriptive names for variables, functions, classes, and modules.
- **Documentation**: Document your code with clear and concise docstrings. Use the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) as a reference.

======================
Documentation
======================

- **Consistency**: Ensure that all new features and changes are well-documented.
- **Clarity**: Write documentation that is clear and easy to understand.
- **Examples**: Provide examples where applicable to illustrate how to use new features.

======================
Testing
======================

- **Coverage**: Write tests for new features and ensure existing tests pass.
- **Best Practices**: Follow best practices for writing unit and integration tests.
- **Continuous Integration**: Ensure that your changes integrate smoothly with the existing CI/CD pipeline.

*****************************
Development Environment Setup
*****************************

To set up your development environment, follow these steps:

1. **Install Dependencies**

   Ensure you have Python 3.7 or higher installed. Install the required dependencies using `pip`:

   .. code-block:: bash

      pip install -r requirements.txt

2. **Build and Run Docker Image**

   If you prefer using Docker for development, build and run the Docker image:

   .. code-block:: bash

      docker build -t my-python-tests .
      docker run --rm -it -v .:/app my-python-tests bash

3. **Run Tests**

   Inside the Docker container or your local environment, run the tests to verify your setup:

   .. code-block:: bash

      python3 main.py

*********************
Acknowledgements
*********************

Thank you for considering contributing to Argus! Your efforts help improve the tool for all users.

For any questions or further assistance, feel free to contact the maintainers or open an issue in the repository.
