"""
Generates a jupyter kernel from a given conda environment while ensuring
that ipykernel is installed in that environment so that the kernel can be used.

It prompts the user for the necessary inputs as it goes along and will not
touch existing jupyter kernels.
"""
import argparse
import os
import re
import glob
import shutil
import sys
import readline
import subprocess
import pkg_resources

# allow tab completion in input()
readline.set_completer_delims(' \t\n=')
readline.parse_and_bind("tab: complete")

class ArgResult: # pylint: disable=too-few-public-methods
    """
    Defines the values that will be returned by the command line arguments
    """
    environment = None
    name = None
    yes = False

class JupyterKernelGenException(BaseException):
    """
    Defines an exception type for errors generating
    a jupyter kernel
    """

class TextStyles: # pylint: disable=too-few-public-methods
    """
    Defines a set of text styling options to be placed in strings
    """
    # Font styles
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    # Colours
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'

    # Text styles
    WARNING = f'{BOLD}{YELLOW}'
    DIRECTORY = f'{UNDERLINE}{BOLD}'
    OK = f'{BOLD}{GREEN}'
    FAIL = f'{BOLD}{RED}'

    # Reset styling
    END = '\033[0m'

def clean_exit(exit_code: int, path: "str | None") -> None:
    """
    Exit the program and remove the created directory if applicable

    :param exit_code:   the exit code to pass to the operating system
    :param path:        the path to remove if applicable
    """
    try:
        if path is not None:
            shutil.rmtree(path)
    except shutil.Error as err:
        print(f"{TextStyles.FAIL}failed to remove directory: {err}{TextStyles.END}")

    sys.exit(exit_code)

def check_for_conda() -> str:
    """
    Looks for a mamba or conda executable on the system with a preference
    for mamba

    :returns:           the path to the mamba or conda executable
    """
    print(f"{TextStyles.BOLD}First we need to make sure that either \
mamba or conda is installed and is available on the PATH.{TextStyles.END}")

    conda_exe = None
    try:
        conda_exe = shutil.which("mamba") # first try getting mamba because its faster
    except shutil.Error as err:
        print(f"{TextStyles.FAIL}error occurred getting mamba from path: {err}{TextStyles.END}",
              file=sys.stderr)

    if conda_exe is None:
        try:
            conda_exe = shutil.which("conda") # try finding conda if mamba isn't available
        except shutil.Error as err:
            raise JupyterKernelGenException(f"error occurred getting conda from path: {err}") \
                    from err

        if conda_exe is None: # fatal error: no conda or mamba executable
            raise JupyterKernelGenException("No mamba or conda programs were found on the PATH. \
Make sure that you have installed conda or mamba and that you have initialized it.")

    print(f"Great! A conda program was found at {TextStyles.DIRECTORY}\
{TextStyles.OK}{conda_exe}{TextStyles.END}.\n")

    return conda_exe

def valid_conda_environment(path: str) -> bool:
    """
    Checks whether a conda environment is valid.

    :param path:    the path to check
    :returns:       true if the conda environment is valid, false otherwise
    """
    try:
        # all conda environments have a /conda-meta directory
        if os.path.isdir(get_abs_path(path) + "/conda-meta"):
            return True
    except OSError as err:
        raise JupyterKernelGenException(f"error occurred checking directory: {err}") from err
    return False

def get_abs_path(path: str) -> str:
    """
    replace ~ with user's home directory and make it an absolute path
    if ~ is not used to refer to the user's home directory, it will
    just create an absolute path to the specified location.
    Just returns the given path if it is already absolute.

    :param path:    the path to make absolute
    :return:        the created absolute path
    """
    try:
        return os.path.abspath(os.path.expanduser(path).strip()).strip()
    except OSError as err:
        raise JupyterKernelGenException(f"failed to create absolute path: {err}") from err

def get_conda_env():
    """
    Gets a path to a conda environment from the user.

    :returns: the path to the conda environment
    """
    while True:
        try:
            print(f"{TextStyles.END}{TextStyles.BOLD}\
Which conda environment do you want to use? Enter the path to its directory here: \
{TextStyles.END}", end="")
            conda_env = get_abs_path(input())

            if valid_conda_environment(conda_env):
                print(f"Using the conda environment at {TextStyles.DIRECTORY}{TextStyles.OK}\
{conda_env}{TextStyles.END}.\n")
                break

            print(f"{TextStyles.FAIL}The given path is not a conda environment. \
Look for a directory that contains a folder called ``conda-meta''.{TextStyles.END}",
                  file=sys.stderr)
        except EOFError:
            continue
        except OSError as err:
            raise JupyterKernelGenException(f"error occurred checking directory: {err}") from err

    return conda_env

def ipykernel_installed(conda_env: str) -> bool:
    """
    Checks that the ipykernel is installed by checking for both the
    ipykernel package and the ipython executable. We check for files
    instead of trying to run `ipython --version` because doing so
    would require activating conda and also checking the error code
    from the shell which would add a lot of complexity to the function
    without being any more reliable than just checking for the files
    directly.

    :param conda_env:   the path to a conda environment to check
    :returns:           True if ipykernel and ipython are installed
                        and False otherwise
    """
    # We check for both ipykernel and ipython to be installed just to be doubly sure
    # that we have everything we need
    found_kernel = False
    for file in glob.glob(conda_env + "/lib/python3.*/site-packages/ipykernel"):
        try:
            if os.path.exists(file):
                found_kernel = True
                break # exit the loop if one of the python versions has ipykernel
        # error: os.path.exists() failed, but we can just check the other directories in the glob
        except OSError as err:
            print(f"{TextStyles.FAIL}error occurred checking for ipykernel: \
{err}{TextStyles.END}", file=sys.stderr)

    try:
        found_ipython = os.path.isfile(conda_env + "/bin/ipython")
    except OSError as err: # fatal error: os.path.isfile() failed
        raise JupyterKernelGenException(f"error occurred checking for ipython: {err}") from err

    return found_ipython and found_kernel

def install_ipykernel(conda_exe: str, conda_env: str, yes: bool) -> None:
    """
    Installs ipykernel into a specific conda envionment using a given
    conda executable

    :param conda_exe:   the path to the executable for conda
    :param conda_env:   the path to the environment to install to
    :param yes:         install without prompt
    """
    # only install if the user enters `y`. If any other character is entered, do not install
    print(f"{TextStyles.WARNING}The package ipykernel was not found in your conda environment. \
It is needed in order to create a jupyter kernel.{TextStyles.END}")
    if not yes:
        inp = input("Install ipykernel? [y/N] ")

        try:
            yes = re.search(r'^y', inp) is not None
        except re.error as err:
            print(f"{TextStyles.WARNING}Failed to check input: {err}{TextStyles.END}")
    else:
        print("Installing ipykernel...")

    if yes:
        try:
            subprocess.run([conda_exe, "install", "-p", conda_env, "-y", "ipykernel"], check=True)
        except subprocess.CalledProcessError as err:
            raise JupyterKernelGenException(f"ipykernel installation failed: {err}") from err
    else:
        # exit the script if the user does not want to install ipykernel since
        # we cannot continue without it
        print(f"{TextStyles.WARNING}ipykernel is needed \
to continue setting up the jupyter kernel. Exiting the program...{TextStyles.END}")
        clean_exit(0,None)

def valid_kernel_name(name: str) -> bool:
    """
    Checks that the kernel name contains only letters, numbers, '-', '.', and '_'.

    :param name:    the name to check
    :return:        returns True if valid, False otherwise
    """
    try:
        if re.search(r'^([a-zA-Z0-9]|-|\.|_)+$', name) is None:
            print(f"{TextStyles.FAIL}invalid kernel name. \
Use only letters, numbers, '-', '.', and '_'{TextStyles.END}")
            return False
    except re.error as err: # error: regex failed. Try again
        print(f"{TextStyles.FAIL}failed to check kernel name: {err}{TextStyles.END}")
        return False
    # Generate potential paths where this kernel name may already be used
    user_path = get_abs_path(f"~/.local/share/jupyter/kernels/{name}")
    system_path1 = f"/usr/share/jupyter/kernels/{name}"
    system_path2 = f"/usr/local/share/jupyter/kernels/{name}"
    env_path = f"{sys.prefix}/share/jupyter/kernels/{name}"

    try:
        if os.path.exists(user_path) or \
            os.path.exists(system_path1) or \
            os.path.exists(system_path2) or \
            os.path.exists(env_path):
            print(f"{TextStyles.FAIL}environment with that name already exists{TextStyles.END}")
            return False
    except OSError as err: # error: checking kernel name against existing kernels failed. Try again
        print(f"{TextStyles.FAIL}failed to check kernel name: {err}{TextStyles.END}")
        return False
    return True

def get_kernel_name() -> str:
    """
    Get the name of the kernel to create from the user

    :returns: the name of the kernel
    """
    while True:
        try_again = False
        print(f"{TextStyles.END}{TextStyles.BOLD}What do you want to call the kernel? \
Use only letters, numbers, '-', '.', and '_': {TextStyles.END}", end="", flush=True)
        kernel_name = input()

        if not valid_kernel_name(kernel_name):
            try_again = True

        # use a break instead of looping on try_again,
        # so that python type hinting knows that the return value cannot be None
        if not try_again:
            break

    return kernel_name

def create_kernel_dir(kernel_name: str) -> str:
    """
    Create the necessary directory for installing the kernel

    :param kernel_name: the name of the kernel to generate
    :return:            the path to the new directory
    """
    path = None
    try:
        # replace ~ with the path to the user's home directory
        path = get_abs_path(f"~/.local/share/jupyter/kernels/{kernel_name}")
        print(f"{TextStyles.BOLD}Installing the kernel at {TextStyles.DIRECTORY}\
{path}{TextStyles.END}{TextStyles.BOLD}.{TextStyles.END}")
        os.makedirs(path, exist_ok=True)
        print(f"Directory created at {TextStyles.DIRECTORY}{TextStyles.OK}\
{path}{TextStyles.END}.")
    except OSError as err: # fatal error: cannot create the directory
        raise JupyterKernelGenException(f"failed to create directory: {err}") from err
    return path

def create_kernel_helper_script(path: str, conda_env: str) -> None:
    """
    Create a script that launches the kernel

    :param path:        the path to install the kernel to
    :param conda_env:   the path to the conda environment to launch with
    """
    source = f"""#!/bin/bash

source activate {conda_env}
exec "$@"
"""
    try:
        with open(path + "/kernel-helper.sh", "w", encoding="UTF-8") as file:
            file.write(source)
        print(f"Helper script created at {TextStyles.DIRECTORY}\
{TextStyles.OK}{path}/kernel-helper.sh{TextStyles.END}.")
    except OSError as err: # fatal error: failed to create the helper script
        raise JupyterKernelGenException(f"failed to write to \
{path}/kernel-helper.sh: {err}") from err

def create_kernel_json(path, kernel_name):
    """
    Create the json defining the kernel

    :param path:        the path to install the kernel to
    :param kernel_name: the name of the kernel being installed
    """
    source = f"""{{
  "argv": ["{{resource_dir}}/kernel-helper.sh", "python3", "-m", "ipykernel_launcher", "-f", "{{connection_file}}"],
  "display_name": "{kernel_name}",
  "language": "python"
}}"""
    try:
        with open(path + "/kernel.json", "w", encoding="UTF-8") as file:
            file.write(source)
        print(f"Kernel definition created at {TextStyles.DIRECTORY}{TextStyles.OK}\
{path}/kernel.json{TextStyles.END}.")
    except OSError as err: # fatal error: failed to create kernel.json
        raise JupyterKernelGenException(f"failed to write to {path}/kernel.json: {err}") from err

def program_info():
    """
    print program info if interactive mode is active
    """
    print(f"{TextStyles.BOLD}Welcome to jupyterkernelgen. \
This program will guide you through creating a \
new kernel for jupyter.{TextStyles.END}\n")

def handle_args() -> ArgResult:
    """
    Parse command line arguments.

    :return:    a tuple of strings (path,name)
    """
    parser = argparse.ArgumentParser(prog="jupyterkernelgen",
        description="generates a jupyter kernel from a given conda environment")
    parser.add_argument("-e", "--environment", action="store", dest="environment",
        help="the path to a conda environment to use. May be a relative or absolute path.")
    parser.add_argument("-n", "--name", action="store", dest="name",
        help="the name of the kernel to create. Must contain \
                only letters, numbers, '-', '.', and '_'.")
    parser.add_argument("-y", "--yes", action="store_true", dest="yes",
        help="automatically accept installation of packages.")
    parser.add_argument("-v", "--version", action="version", version="%(prog)s " +
                        pkg_resources.get_distribution('jupyterkernelgen').version)
    try:
        args = parser.parse_args()

        res = ArgResult()
        res.environment = args.environment
        res.name = args.name
        res.yes = args.yes

        return res
    except argparse.ArgumentError as err:
        print(f"{TextStyles.FAIL}Failed to parse arguments: {err}{TextStyles.END}")
        parser.print_help()
        sys.exit(1)

def install(environment: "str | None" = None, name: "str | None" = None, yes: bool = False) -> None:
    """
    Installs the jupyter kernel

    :param environment: the conda environment to use for the install
    :param name:        the name of the kernel to install
    :param yes:         accept installation of packages without prompts
    """

    program_info()

    path = None
    try:
        if environment is not None and not valid_conda_environment(environment):
            raise JupyterKernelGenException(f"{environment} is not a valid conda environment. \
Look for a directory containing a folder called ``conda-meta''.")
        if name is not None and not valid_kernel_name(name):
            raise JupyterKernelGenException()
        if environment is not None:
            environment = get_abs_path(environment)

        # Make sure conda or mamba is installed
        conda_exe = check_for_conda()

        # Figure out which conda environment to use
        if environment is None:
            environment = get_conda_env()

        # Get the name of the kernel
        if name is None:
            name = get_kernel_name()

        # Ensure that ipykernel is installed
        installed = ipykernel_installed(environment)
        if not installed:
            # Install ipykernel if necessary
            install_ipykernel(conda_exe, environment, yes)

            # Exit if ipykernel failed to install
            if not ipykernel_installed(environment):
                print(f"{TextStyles.FAIL}ipykernel installation failed{TextStyles.END}")
                clean_exit(1, path)
        print(f"{TextStyles.OK}All necessary packages are installed.\n{TextStyles.END}")

        # Create a directory for the kernel
        path = create_kernel_dir(name)

        # Create script to launch the kernel
        create_kernel_helper_script(path, environment)

        # Create json to define the kernel
        create_kernel_json(path, name)

        print(f"{TextStyles.OK}Installed kernel at {TextStyles.DIRECTORY}{path}{TextStyles.END}\
{TextStyles.OK} using conda environment: {TextStyles.DIRECTORY}{environment}{TextStyles.END}")

    except (KeyboardInterrupt, JupyterKernelGenException) as err:
        if len(str(err)) == 0:
            print(f"{TextStyles.END}\nEXITING...")
        else:
            print(f"{TextStyles.FAIL}ERROR: {err}{TextStyles.END}\nEXITING...")
        clean_exit(1, path)

def main() -> None:
    """
    main function: runs the program
    """
    args = handle_args()
    conda_env = args.environment
    kernel_name = args.name
    yes = args.yes
    install(conda_env, kernel_name, yes)
