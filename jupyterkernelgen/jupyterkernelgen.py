#!/usr/bin/env python3
import os
import re
import glob
import shutil
import sys
import readline
import subprocess

# allow tab completion in input()
readline.set_completer_delims(' \t\n=')
readline.parse_and_bind("tab: complete")

class JupyterKernelGenException(BaseException):
    pass

class text_styles:
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
    INPUT = f'{BLUE}'
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
        if path != None:
            shutil.rmtree(path)
    except shutil.Error as e:
        print(f"{text_styles.FAIL}failed to remove directory: {e}{text_styles.END}")

    sys.exit(exit_code)

def check_for_conda() -> str:
    """
    Looks for a mamba or conda executable on the system with a preference
    for mamba

    :returns: the path to the mamba or conda executable
    """
    print(f"{text_styles.BOLD}First we need to make sure that either mamba or conda is installed and is available on the PATH.{text_styles.END}")

    conda_exe = None
    try:
        conda_exe = shutil.which("mamba") # first try getting mamba because its faster
    except shutil.Error as e: # error: exception trying to locate mamba, but we can still try conda
        print(f"{text_styles.FAIL}error occurred getting mamba from path: {e}{text_styles.END}", file=sys.stderr)

    if conda_exe == None:
        try:
            conda_exe = shutil.which("conda") # try finding conda if mamba isn't available
        except shutil.Error as e: # fatal error: exception trying to locate conda and mamba wasn't found
            raise JupyterKernelGenException(f"error occurred getting conda from path: {e}")

        if conda_exe == None: # fatal error: no conda or mamba executable
            raise JupyterKernelGenException("No mamba or conda programs were found on the PATH. Make sure that you have installed conda or mamba and that you have initialized it.")

    print(f"Great! A conda program was found at {text_styles.DIRECTORY}{text_styles.OK}{conda_exe}{text_styles.END}.\n")

    return conda_exe

def get_conda_env():
    """
    Gets a path to a conda environment from the user.

    :returns: the path to the conda environment
    """
    while True:
        try:
            # replace ~ with user's home directory and make it an absolute path
            # if ~ is not used to refer to the user's home directory, it will
            # just create an absolute path to the specified location
            conda_env = os.path.abspath(os.path.expanduser(input(f"{text_styles.END}{text_styles.BOLD}Which conda environment do you want to use? Enter the path to its directory here: {text_styles.INPUT}")))
            print(text_styles.END, end="")

            if os.path.isdir(conda_env + "/conda-meta"): # all conda environments have a /conda-meta directory
                print(f"Using the conda environment at {text_styles.DIRECTORY}{text_styles.OK}{conda_env}{text_styles.END}.\n")
                break

            print(f"{text_styles.FAIL}The given path is not a conda environment. Look for a directory that contains a folder called ``conda-meta''.{text_styles.END}", file=sys.stderr)
        except EOFError as e:
            print()
            continue
        except OSError as e:
            raise JupyterKernelGenException(f"error occurred checking directory: {e}")

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
    :returns:           true if ipykernel and ipython are installed
                        and false otherwise
    """
    # We check for both ipykernel and ipython to be installed just to be doubly sure
    # that we have everything we need
    found_kernel = False
    for file in glob.glob(conda_env + "/lib/python3.*/site-packages/ipykernel"):
        try:
            if os.path.exists(file):
                found_kernel = True
                break # exit the loop if one of the python versions has ipykernel
        except OSError as e: # error: os.path.exists() failed, but we can just check the other directories in the glob
            print(f"{text_styles.FAIL}error occurred checking for ipykernel: {e}{text_styles.END}", file=sys.stderr)

    try:
        found_ipython = os.path.isfile(conda_env + "/bin/ipython")
    except OSError as e: # fatal error: os.path.isfile() failed
        raise JupyterKernelGenException(f"error occurred checking for ipython: {e}")

    return found_ipython and found_kernel

def install_ipykernel(conda_exe: str, conda_env: str) -> None:
    """
    Installs ipykernel into a specific conda envionment using a given
    conda executable

    :param conda_exe:   the path to the executable for conda
    :param conda_env:   the path to the environment to install to
    """
    # only install if the user enters `y`. If any other character is entered, do not install
    print(f"{text_styles.WARNING}The package ipykernel was not found in your conda environment. It is needed in order to create a jupyter kernel. Install it? [y/N]{text_styles.END} ", end="", flush=True)

    inp = sys.stdin.read(1)
    if inp == "y":
        try:
            subprocess.run([conda_exe, "install", "-p", conda_env, "-y", "ipykernel"])
        except subprocess.CalledProcessError as e:
            raise JupyterKernelGenException(f"ipykernel installation failed: {e}") # fatal error: we need ipykernel
    else:
        # exit the script if the user does not want to install ipykernel since
        # we cannot continue without it
        print(f"{text_styles.WARNING}ipykernel is needed to continue setting up the jupyter kernel. Exiting the program...{text_styles.END}")
        clean_exit(0,None)
    print()

def get_kernel_name() -> str:
    """
    Get the name of the kernel to create from the user

    :returns: the name of the kernel
    """
    while True:
        try_again = False
        print(f"{text_styles.END}{text_styles.BOLD}What do you want to call the kernel? Use only letters, numbers, '-', '.', and '_': {text_styles.INPUT}", end="", flush=True)
        kernel_name = sys.stdin.readline().strip()
        print(text_styles.END, end="")

        try:
            if re.search(r'^([a-zA-Z0-9]|-|\.|_)+$', kernel_name) == None:
                print(f"{text_styles.FAIL}invalid kernel name. Use only letters, numbers, '-', '.', and '_'{text_styles.END}")
                try_again = True
        except re.error as e: # error: regex failed. Try again
            print(f"{text_styles.FAIL}failed to check kernel name: {e}{text_styles.END}")
            continue

        # Generate potential paths where this kernel name may already be used
        user_path = os.path.expanduser(f"~/.local/share/jupyter/kernels/{kernel_name}")
        system_path1 = f"/usr/share/jupyter/kernels/{kernel_name}"
        system_path2 = f"/usr/local/share/jupyter/kernels/{kernel_name}"
        env_path = f"{sys.prefix}/share/jupyter/kernels/{kernel_name}"

        try:
            if os.path.exists(user_path) or os.path.exists(system_path1) or os.path.exists(system_path2) or os.path.exists(env_path):
                print(f"{text_styles.FAIL}environment with that name already exists{text_styles.END}")
                try_again = True
        except OSError as e: # error: checking kernel name against existing kernels failed. Try again
            print(f"{text_styles.FAIL}failed to check kernel name: {e}{text_styles.END}")
            continue

        # use a break instead of looping on try_again, so that python type hinting knows that the return value cannot be None
        if not try_again:
            break
    print()

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
        path = os.path.expanduser(f"~/.local/share/jupyter/kernels/{kernel_name}")
        print(f"{text_styles.BOLD}Installing the kernel at {text_styles.DIRECTORY}{path}{text_styles.END}{text_styles.BOLD}.{text_styles.END}")
        os.makedirs(path, exist_ok=True)
        print(f"Directory created at {text_styles.DIRECTORY}{text_styles.OK}{path}{text_styles.END}.")
    except OSError as e: # fatal error: cannot create the directory
        raise JupyterKernelGenException(f"failed to create directory: {e}")
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
        f = open(path + "/kernel-helper.sh", "w")
        f.write(source)
        f.close()
        print(f"Helper script created at {text_styles.DIRECTORY}{text_styles.OK}{path}/kernel-helper.sh{text_styles.END}.")
    except OSError as e: # fatal error: failed to create the helper script
        raise JupyterKernelGenException(f"failed to write to {path}/kernel-helper.sh: {e}")

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
        f = open(path + "/kernel.json", "w")
        f.write(source)
        f.close()
        print(f"Kernel definition created at {text_styles.DIRECTORY}{text_styles.OK}{path}/kernel.json{text_styles.END}.")
    except OSError as e: # fatal error: failed to create kernel.json
        raise JupyterKernelGenException(f"failed to write to {path}/kernel.json: {e}")
    print()

def program_info():
    print(f"{text_styles.BOLD}Welcome to jupyterkernelgen. This program will guide you through creating a new kernel for jupyter.{text_styles.END}\n")

def main():
    path = None
    program_info()
    try:
        # Make sure conda or mamba is installed
        conda_exe = check_for_conda()

        # Figure out which conda environment to use
        conda_env = get_conda_env()

        # Get the name of the kernel
        kernel_name = get_kernel_name()

        # Ensure that ipykernel is installed
        installed = ipykernel_installed(conda_env)
        if not installed:
            # Install ipykernel if necessary
            install_ipykernel(conda_exe, conda_env)

            # Exit if ipykernel failed to install
            if not ipykernel_installed(conda_env):
                print(f"{text_styles.FAIL}ipykernel installation failed{text_styles.END}")
                clean_exit(1, path)
        print(f"{text_styles.OK}All necessary packages are installed.\n{text_styles.END}")

        # Create a directory for the kernel
        path = create_kernel_dir(kernel_name)

        # Create script to launch the kernel
        create_kernel_helper_script(path, conda_env)

        # Create json to define the kernel
        create_kernel_json(path, kernel_name)

        print(f"{text_styles.OK}Kernel installation success{text_styles.END}")

    except (KeyboardInterrupt, JupyterKernelGenException) as e:
        if len(str(e)) == 0:
            print(f"{text_styles.END}\nEXITING...")
        else:
            print(f"{text_styles.FAIL}ERROR: {e}{text_styles.END}\nEXITING...")
        clean_exit(1, path)

if __name__=="__main__":
    main()
