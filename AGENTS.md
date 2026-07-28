# AGENTS.md - Shovl Engineering Protocol

## Project Overview

Shovl is a tiny database and S3 client written in Python using Textual. It is designed to be simple and efficient. Database and S3 connections are stored in a config file and connections are established using SQLAlchemy for databases and Boto3 for S3.

## Coding Style

Always use type hints in your code. This helps with readability and maintainability. Follow the Black style guide for Python code. Use `ruff check` to ensure that your code adheres to the style guide and `ruff format` to automatically format your code.

## Agent Workflow

1. Read before write: Read the README.md file to understand the user flow.
2. Define the scope: one concern per change; avoid mixed feature+refactor+infrastructure patches.
3. Implement minimal patch: apply KISS/YAGNI/DRY rule-of-three explicitly.
4. Validate: use `ruff check` as a linter and `ruff format` for formatting.
5. Test: run unittests using `python -m unittest` to ensure that your changes do not break existing functionality.
6. Finally: run the application to ensure it starts up as expected. Use `python -m shovl` without any further options.

## Unittests

When writing unittests, use the `unittest` framework. Ensure that tests are isolated and do not depend on external resources (i.e. databases). The only exception is an Sqlite database that you may create called `test.db`.

Write one unittest file per module, and name it `test_<module_name>.py`. For example, if you have a module called `database.py`, the unittest file should be named `test_database.py`.

Unittests belong in the `tests` folder.
