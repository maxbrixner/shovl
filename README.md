# Shovl

A lightweight terminal-based database and S3 client built with Textual.

## Installation

Install Shovl using pip:

```bash
pip install shovl
```

### Database-Specific Dependencies

Shovl requires additional drivers depending on your target database systems. Install the appropriate extras for your use case (Sqlite is supported by default):

```bash
pip install shovl[postgresql]    # PostgreSQL support
pip install shovl[mysql]         # MySQL support
pip install shovl[oracle]        # Oracle Database support
pip install shovl[snowflake]     # Snowflake support
pip install shovl[duckdb]        # DuckDB support
pip install shovl[ibmdb]         # IBM DB2 support
```

**Note**: Shovl leverages SQLAlchemy's extensive database support. You may install additional SQLAlchemy-compatible drivers as needed for other database systems.

## Configuration

Shovl uses a hierarchical configuration system to manage connection details and application settings. The configuration file is loaded in the following priority order:

1. Path specified via the `--config` command-line option
2. Local configuration file (`.shovl` in the current directory)
3. User configuration file (`~/.config/shovl/shovl` or `%USERPROFILE%\.config\shovl\shovl` on Windows)
4. Global user configuration file (`~/.shovl` or `%USERPROFILE%\.shovl` on Windows)
5. Default configuration (fallback)

### Generating Configuration Files

Create a sample configuration file:

```bash
# Local configuration
shovl --sample-config > .shovl

# Global configuration
shovl --sample-config > ~/.shovl
```

View the complete configuration schema with detailed parameter descriptions:

```bash
shovl --config-schema
```

### Configuration of Database Connections

A mininmal configuration file with a single database connection looks like this:

```json
{
  "connections": [
    {
      "description": "A short description",
      "name": "My Database",
      "url": "<sqlalchemy connection url>"
    }
  ]
}
```

The `url` field should be a valid SQLAlchemy connection string, which includes the database type, username, password, host, port, and database name. See the [SQLAlchemy documentation](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls) for more details on constructing connection URLs.

See "Security Best Practices" below for how to handle credentials securely.

By default, Shovl will fetch a maximum of 1000 rows when executing a query. You can adjust this limit in the configuration file using the `fetch_limit` parameter.

```json
{
  "connections": [
    {
      ...
      "fetch_limit": 2000
    }
  ]
}
```

You may also pass other parameters to SQLAlchemy via the `engine_parameters` field, which accepts a dictionary of key-value pairs. These options will be passed directly to the SQLAlchemy engine when establishing a connection.

```json
{
  "connections": [
    {
      ...
      "engine_parameters": {
        "isolation_level": "REPEATABLE READ"
      }
    }
  ]
}
```

A comprehensive list of available engine parameters can be found in the [SQLAlchemy documentation](https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.create_engine.params). Here are some examples:

| Database | Example | Common Engine Parameters |
|----------|---------|-----------------|
| PostgreSQL | `postgresql://user:password@localhost:5432/mydatabase` | `{"connect_args": {"sslmode": "require"}}` |
| Oracle     | `oracle://user:password@localhost:1521/?service_name=myservice` | `{"thick_mode": true}` |

### Configuration of S3 Connections

Shovl also supports connections to S3-compatible storage services. A minimal S3 connection configuration looks like this:

```json
{
  "connections": [
    {
      "bucket_name": "my-bucket",
      "description": "A short description",
      "name": "My S3 Storage",
      "region_name": "us-east-1"
    }
  ]
}
```

This assumes that you have configured your AWS credentials using environment variables or the AWS CLI. You can also specify credentials directly in the configuration file (see "Security Best Practices" below):

```json
{
  "connections": [
    {
      ...
      "aws_access_key_id": "{{AWS_ACCESS_KEY_ID}}",
      "aws_account_id": "{{AWS_ACCOUNT_ID}}",
      "aws_secret_access_key": "{{AWS_SECRET_ACCESS_KEY}}",
      "aws_secret_access_key": "{{AWS_SECRET_ACCESS_KEY}}"
    }
  ]
}
```

You may also use AWS Secure Token Service (STS) to generate temporary credentials for enhanced security:

```json
{
  "connections": [
    {
      ...
      "role_name": "{{AWS_ROLE_NAME}}",
      "use_sts": true
    }
  ]
}
```

If you do not have permission to call the head bucket operation, you can disable the bucket existence check using `test_connection`:

```json
{
  "connections": [
    {
      ...
      "test_connection": false
    }
  ]
}
```

You may also specifiy a `head_prefix` that is automatically applied to all S3 operations:

```json
{
  "connections": [
    {
      ...
      "test_connection": false,
      "head_prefix": "my-prefix/"
    }
  ]
}
```

If you are using an S3-compatible service, you can specify a custom endpoint URL:

```json
{
  "connections": [
    {
      ...
      "endpoint_url": "https://s3-compatible-service.com"
    }
  ]
}
```

You may also pass additional parameters to the S3 client via the `client_config` field, which accepts a dictionary of key-value pairs. These options will be passed directly to the boto3 client when establishing a connection. This can also be used to configure proxies:

```json
{
  "connections": [
    {
      ...
      "client_config": {
          "connect_timeout": 10,
          "read_timeout": 30
      }
    }
  ]
}
```

See the [boto3 documentation](https://docs.aws.amazon.com/botocore/latest/reference/config.html) for more details.

### Configure Logging

By default, logging is disabled. You can enable logging and specify a log file path in the configuration file:

```json
{
  "connections": [
    ...
  ],
  "logging": {
    "enabled": true,
    "log_file": "~/.shovl.log",
    "log_level": "INFO",
    "mode": "w"
  }
}
```

### Configure the GUI

Shovl's GUI can be customized using the `gui` section of the configuration file. You can specify a theme and the maximum number of list items displayed:

```json
{
  "connections": [
    ...
  ],
  "gui": {
    "theme": "tokyo-night",
    "max_list_items": 1000
  }
}
```

Valid themes can be found in the [Textual documentation](https://textual.textualize.io/guide/design/).

### Security Best Practices

**Important**: It is good practice to not store credentials in plain text within configuration files. Shovl supports environment variable substitution using double curly bracket syntax: `{{VARIABLE_NAME}}`.

To configure an env-file, you can either use the `env_file` parameter in the configuration file:

```json
{
  "connections": [
    ...
  ],
  "env_file": ".env"
}
```

or pass the env-file path directly when launching Shovl:

```bash
shovl --env .env
```

## Usage

### Basic Usage

Launch Shovl with default settings:

```bash
shovl
```

Specify a custom configuration file:

```bash
shovl --config /path/to/custom/config.json
```

Display all available command-line options:

```bash
shovl --help
```

## System Requirements

- Python 3.14 or higher
- Terminal with Unicode support
- Network connectivity for database and S3 operations

## License

This project is distributed under the terms specified in the LICENSE.md file.

## Contributing

Shovl is an open-source project. For bug reports, feature requests, or contributions, please visit the [project repository](https://github.com/maxbrixner/shovl).

## Support

For issues and support requests, please use the [project's issue tracker](https://github.com/maxbrixner/shovl/issues)
