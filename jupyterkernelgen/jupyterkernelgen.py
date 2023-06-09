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

# define ANSI escape codes for coloured text
class colors:
    HEADER = '\033[95m'
    OK = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def clean_exit(exit_code: int, path: str | None) -> None:
    """
    Exit the program and remove the created directory if applicable

    :param exit_code:   the exit code to pass to the operating system
    :param path:        the path to remove if applicable
    """
    try:
        if path != None:
            shutil.rmtree(path)
    except shutil.Error as e:
        print(f"{colors.FAIL}failed to remove directory: {e}{colors.ENDC}")

    sys.exit(exit_code)

def check_for_conda() -> str:
    """
    Looks for a mamba or conda executable on the system with a preference
    for mamba

    :returns: the path to the mamba or conda executable
    """
    print(f"{colors.HEADER}Looking for conda...{colors.ENDC}")

    conda_exe = None
    try:
        conda_exe = shutil.which("mamba") # first try getting mamba because its faster
    except shutil.Error as e:
        print(f"{colors.WARNING}error occurred getting mamba from path: {e}{colors.ENDC}", file=sys.stderr)

    if conda_exe == None:
        try:
            conda_exe = shutil.which("conda") # try finding conda if mamba isn't available
        except shutil.Error as e:
            raise JupyterKernelGenException(f"error occurred getting conda from path: {e}")

        if conda_exe == None:
            raise JupyterKernelGenException("no conda executable on the path")

    print(f"- found conda executable: {colors.OK}{conda_exe}{colors.ENDC}\n")

    return conda_exe

def get_conda_env():
    """
    Gets a path to a conda environment from the user.

    :returns: the path to the conda environment
    """
    try:
        # replace ~ with user's home directory and make it an absolute path
        # if ~ is not used to refer to the user's home directory, it will
        # just create an absolute path to the specified location
        conda_env = os.path.abspath(os.path.expanduser(input(f"{colors.HEADER}Enter path to conda environment{colors.ENDC}: ")))

        if os.path.isdir(conda_env + "/conda-meta"): # all conda environments have a /conda-meta directory
            print(f"- found conda env: {colors.OK}{conda_env}{colors.ENDC}\n")
        else:
            raise JupyterKernelGenException("given conda env path is not a conda environment")

    except (OSError, EOFError) as e:
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
    print(f"{colors.HEADER}Checking for ipython in conda env...{colors.ENDC}")

    # We check for both ipykernel and ipython to be installed just to be doubly sure
    # that we have everything we need
    found_kernel = False
    for file in glob.glob(conda_env + "/lib/python3.*/site-packages/ipykernel"):
        try:
            if os.path.exists(file):
                found_kernel = True
                break # exit the loop if one of the python versions has ipykernel
        except OSError as e:
            print(f"{colors.FAIL}error occurred checking for conda environment: {e}{colors.ENDC}", file=sys.stderr)

    if found_kernel:
        print(f"- {colors.OK}found ipykernel{colors.ENDC}")
    else:
        print(f"- {colors.WARNING}no ipykernel found{colors.ENDC}")

    found_ipython = os.path.isfile(conda_env + "/bin/ipython")
    if found_ipython:
        print(f"- {colors.OK}found ipython{colors.ENDC}")
    else:
        print(f"- {colors.WARNING}no ipython found{colors.ENDC}")
    print()

    return found_ipython and found_kernel

def install_ipykernel(conda_exe: str, conda_env: str) -> None:
    """
    Installs ipykernel into a specific conda envionment using a given
    conda executable

    :param conda_exe:   the path to the executable for conda
    :param conda_env:   the path to the environment to install to
    """
    # only install if the user enters `y`
    print(f"{colors.HEADER}Install ipykernel? [y/N]{colors.ENDC} ", end="", flush=True)

    inp = sys.stdin.read(1)
    if inp == "y":
        try:
            subprocess.run([conda_exe, "install", "-p", conda_env, "-y", "ipykernel"])
        except subprocess.CalledProcessError as e:
            raise JupyterKernelGenException(f"ipykernel installation failed: {e}")
    else:
        # exit the script if the user does not want to install ipykernel since
        # we cannot continue without it
        raise JupyterKernelGenException("not installing ipykernel")
    print()

def get_kernel_name() -> str:
    """
    Get the name of the kernel to create from the user

    :returns: the name of the kernel
    """
    print(f"{colors.HEADER}Enter kernel name{colors.ENDC}: ", end="", flush=True)
    try:
        kernel_name = sys.stdin.readline().strip()

        if re.search(r'^([a-zA-Z0-9]|-|\.|_)+$', kernel_name) == None:
            raise JupyterKernelGenException("invalid kernel name. Use only letters, numbers, '-', '.', and '_'")

        # Generate potential paths where this kernel name may already be used
        user_path = os.path.expanduser(f"~/.local/share/jupyter/kernels/{kernel_name}")
        system_path1 = f"/usr/share/jupyter/kernels/{kernel_name}"
        system_path2 = f"/usr/local/share/jupyter/kernels/{kernel_name}"
        env_path = f"{sys.prefix}/share/jupyter/kernels/{kernel_name}"
        if os.path.exists(user_path) or os.path.exists(system_path1) or os.path.exists(system_path2) or os.path.exists(env_path):
            raise JupyterKernelGenException("environment with that name already exists")
    except OSError as e:
        raise JupyterKernelGenException(f"failed to get kernel name: {e}")
    print()

    return kernel_name

def create_kernel_dir(kernel_name: str) -> str:
    """
    Create the necessary directory for installing the kernel

    :param kernel_name: the name of the kernel to generate
    :return:            the path to the new directory
    """
    print(f"{colors.HEADER}Creating kernel directory...{colors.ENDC}")
    path = None
    try:
        # replace ~ with the path to the user's home directory
        path = os.path.expanduser(f"~/.local/share/jupyter/kernels/{kernel_name}")
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        raise JupyterKernelGenException(f"failed to create directory: {e}")
    print()
    return path

def create_kernel_helper_script(path: str, conda_env: str) -> None:
    """
    Create a script that launches the kernel

    :param path:        the path to install the kernel to
    :param conda_env:   the path to the conda environment to launch with
    """
    print(f"{colors.HEADER}Creating kernel helper script...{colors.ENDC}")
    source = f"""#!/bin/bash

source activate {conda_env}
exec "$@"
"""
    try:
        f = open(path + "/kernel-helper.sh", "w")
        f.write(source)
        f.close()
    except OSError as e:
        raise JupyterKernelGenException(f"failed to write to {path}/kernel-helper.sh: {e}")
    print()

def create_kernel_json(path, kernel_name):
    """
    Create the json defining the kernel

    :param path:        the path to install the kernel to
    :param kernel_name: the name of the kernel being installed
    """
    print(f"{colors.HEADER}Creating kernel json...{colors.ENDC}")
    source = f"""{{
  "argv": ["{{resource_dir}}/kernel-helper.sh", "python3", "-m", "ipykernel_launcher", "-f", "{{connection_file}}"],
  "display_name": "{kernel_name}",
  "language": "python"
}}"""
    try:
        f = open(path + "/kernel.json", "w")
        f.write(source)
        f.close()
    except OSError as e:
        raise JupyterKernelGenException(f"failed to write to {path}/kernel.json: {e}")
    print()

def main():
    path = None
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
                print(f"{colors.FAIL}ipykernel installation failed{colors.ENDC}")
                clean_exit(1, path)

        # Create a directory for the kernel
        path = create_kernel_dir(kernel_name)

        # Create script to launch the kernel
        create_kernel_helper_script(path, conda_env)

        # Create json to define the kernel
        create_kernel_json(path, kernel_name)

        print(f"{colors.OK}Kernel installation success{colors.ENDC}")
    except (KeyboardInterrupt, JupyterKernelGenException) as e:
        print(f"{colors.FAIL}ERROR: {e}{colors.ENDC}\nEXITING...")
        clean_exit(1, path)

if __name__=="__main__":
    main()
