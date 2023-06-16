# jupyterkernelgen

Generates a jupyter kernel from a given conda environment
while ensuring that ipykernel is installed in that environment
so that the kernel can be used.

It prompts the user for the necessary inputs as it goes along
and will not touch existing jupyter kernels.

## Installation

Pypi Installation:
[https://pypi.org/project/jupyterkernelgen](https://pypi.org/project/jupyterkernelgen)

```sh
pip install jupyterkernelgen
```

## How to use:

### Command Line:

- You can use the `jupyterkernelgen` command.
- If environment or name is specified in the command line arguments,
    the user will not be prompted for the specified argument while running
- `--name`, `--environement`, both, or neither can be specified

#### Examples

```sh
jupyterkernelgen --help
jupyterkernelgen
jupyterkernelgen -e ~/path/to/environment-1 -n kernel-name1
jupyterkernelgen -e ../path/to/environment-2 -n kernel-name2 -y
jupyterkernelgen -e ~/path/to/environment-3 -n kernel-name3
```

#### Arguments

| Name            | Shortcut | Type     | Example              | Description                                                          |
|-----------------|----------|----------|----------------------|----------------------------------------------------------------------|
| `--help`        | `-h`     | N/A      | N/A                  | Show help message.                                                   |
| `--version`     | `-v`     | N/A      | N/A                  | The current version of jupyterkernelgen                              |
| `--environment` | `-e`     | `string` | /path/to/environment | The path to a conda environment. May be an absolute or relative path |
| `--name`        | `-n`     | `string` | kernel-name          | The name of the kernel to create                                     |
| `--yes`         | `-y`     | N/A      | N/A                  | Install necessary packages without prompt                            |

### In Python:

- Import `jupyterkernelgen` and run the `install()` function

#### Examples

```py
import jupyterkernelgen

jupyterkernelgen.install() # Install a kernel interactively
jupyterkernelgen.install(environment="/path/to/environment-1", name="kernel-name1") # Install a kernel with a specified path and name
jupyterkernelgen.install(environment="/path/to/environment-2", name="kernel-name2", yes=True) # Install a kernel without prompts
```

#### Arguments

| Name          | Type     | Example               | Description                                                          |
|---------------|----------|-----------------------|----------------------------------------------------------------------|
| `environment` | `string` | "path/to/environment" | The path to a conda environment. May be an absolute or relative path |
| `name`        | `string` | "kernel-name"         | The name of the kernel to create                                     |
| `yes`         | `bool`   | `True`                | Install necessary packages without prompt                            |

## Installing from source code

1. Clone the repository:

```sh
git clone https://github.com/phac-nml/jupyterkernelgen.git
```

2. Install the project:

```sh
cd jupyterkernelgen
pip install .
```

3. Execute the program:
```sh
jupyterkernelgen [-h] [-e ENVIRONMENT] [-n NAME] [-y]
```

## Developer Notes

### Legal

Copyright Government of Canada 2023

Written by: National Microbiology Laboratory, Public Health Agency of Canada

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this work except in compliance with the License.
You may obtain a copy of the License at:

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.

### Contact

**Philip Mabon**: [philip.mabon@phac-aspc.gc.ca](philip.mabon@phac-aspc.gc.ca)
