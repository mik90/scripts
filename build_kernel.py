#!/usr/bin/python3
""" Script for building/installing new kernels """

import os
import sys
import subprocess
from subprocess import CalledProcessError
from collections import namedtuple
from pathlib import Path
from colorama import init, Fore, Style

def error_and_exit(error):
    """ print error then exit with return code 1 """
    print(Fore.RED + f"build_kernel.py: " + Style.RESET_ALL + f"Error! {error}, exiting...")
    sys.exit(1)

def script_info(info):
    """ print debugging info """
    print(Fore.GREEN + f"build_kernel.py: " + Style.RESET_ALL + f"{info}")

def check_perm():
    """ ensure that the user is seen as root """
    script_info("Checking permissions")
    if os.geteuid() != 0:
        error_and_exit("This script must be run as root!")
    script_info("Permissions are okay")

def sync_config():
    """ syncing configuration to new kernel """
    os.chdir("/usr/src/linux")
    script_info(f"syncing configuration to new kernel in {os.getcwd()}")
    try:
        subprocess.run(["make", "syncconfig"], check=True)
    except CalledProcessError as err:
        error_and_exit(err)


def compile_kernel():
    """ compile just the kernel """
    os.chdir("/usr/src/linux")
    script_info(f"Compiling kernel in {os.getcwd()}")
    try:
        subprocess.run(["/bin/bash", "-c", "\"make\" --jobs $(nproc) --load-average 24"], check=True)
    except CalledProcessError as err:
        error_and_exit(err)

def install():
    """ install modules and kernel image itself """
    os.chdir("/usr/src/linux")

    script_info(f"Installing modules")
    try:
        subprocess.run(["make", "modules_install"], check=True)
    except CalledProcessError as err:
        error_and_exit(err)

    install_path = "/boot/EFI/Gentoo"
    script_info(f"Installing kernel image, system map, and config to {install_path}")
    try:
        # This copies over the system environment but appends the INSTALL_PATH variable
        # needed during "make install"
        subprocess.run(["/bin/bash", "-c", "\"make\" install"],
                       env=dict(os.environ, INSTALL_PATH="/boot/EFI/Gentoo"), check=True)
    except CalledProcessError as err:
        error_and_exit(err)

def recompile_modules():
    """ recompile modules included by portage (nvidia-drivers) """
    os.chdir("/usr/src/linux")
    script_info("Recompiling modules from portage")
    try:
        subprocess.run(["emerge", "@module-rebuild"], check=True)
    except CalledProcessError as err:
        error_and_exit(err)

class VersionInfo:
    """ Container for organizing all the kernel versions and files """
    def __init__(self, version_triple: str, vmlinuz: Path, system_map: Path, config: Path, is_old: bool):
        self.version_triple = version_triple
        self.vmlinuz = vmlinuz
        self.system_map = system_map
        self.config = config
        self.is_old = is_old
    def __repr__(self):
        return "VersionInfo()"
    def __str__(self):
        if self.is_old:
            return f"VersionInfo({self.version_triple}.old, {self.vmlinuz}, {self.system_map}, {self.config}, is_old={self.is_old})"
        else:
            return f"VersionInfo({self.version_triple}, {self.vmlinuz}, {self.system_map}, {self.config}, is_old={self.is_old})"

def extract_version_info(vmlinuzes, system_maps, configs):
    """
    Get a set of all the versions and .olds
        - X.Y.Z[.old] preserve the .old aspect if there
    vmlinuzes: a list or generator of strings like "vmlinuz-5.7.5-gentoo.old"
    """
    versions = set()
    
    for vmlinuz in vmlinuzes:
        version_triple = str(vmlinuz).split(sep="-") # Split up the vmlinuz string
        if len(version_triple) != 3:
            error_and_exit(f"Expected len(version) == 3, got {len(version_triple)}!")
        version_triple = version_triple[1] # extract the X.Y.Z

        is_old = bool(vmlinuz.suffix == '.old')
        # Find the accompying System.map and config
        # Get a newer generator
        system_maps = Path().glob("System.map*")
        configs = Path().glob("config*")
        if is_old:
            # Iterate through all of the system_maps and configs and check each stringified filename
            # to see if it has our version_triple and if the filename ends with .old
            # Note: .pop() is a lazy way to convert a single-element list to the underlying type
            # Ensure that the suffix is .old
            system_map = [s for s in system_maps if version_triple in str(s) and str(s).endswith(".old")].pop()
            config = [s for s in configs if version_triple in str(s) and str(s).endswith(".old")].pop()
        else:
            # Ensure that the suffix isn't .old
            system_map = [s for s in system_maps if version_triple in str(s) and not str(s).endswith(".old")].pop()
            config = [s for s in configs if version_triple in str(s) and not str(s).endswith(".old")].pop()

        versions.add(VersionInfo(version_triple, vmlinuz, system_map, config, is_old))
    return versions

def version_cmp(version_info: VersionInfo):
    """ Sort based on version, and then based on .old if versions are equal """
    # Indices:
    # 0 1 2 3 4
    # X . Y . Z
    major = version_info.version_triple[0] # X
    minor = version_info.version_triple[2] # Y
    patch = version_info.version_triple[4] # Z
    if version_info.is_old:
        # is .old, penalize it in the sorting by making this 0
        old_adj = 0
    else:
        # is NOT .old, give it an advantage in sorting by making this 1
        old_adj = 1
    return (major, minor, patch, old_adj)


def clean_up():
    """ delete old kernels """

    efi_gentoo_dir = "/boot/EFI/Gentoo"
    os.chdir(efi_gentoo_dir)
    script_info(f"Cleaning up old kernels in {os.getcwd()}")

    # Find all vmlinuz, config, and system map files
    vmlinuzes = Path().glob("vmlinuz-*-gentoo*")
    system_maps = Path().glob("System.map*")
    configs = Path().glob("config*")

    # Ensure that the 3 lists are the same length
    if not len(list(vmlinuzes)) == len(list(system_maps)) and len(list(system_maps)) == len(list(configs)):
        error_and_exit(f"There are {len(list(vmlinuzes))} vmlinuz files, {len(list(system_maps))} "
                       + f"system maps, and {len(list(configs))} config files")

    # Re-gen the generators, probably could've just copied this as a list
    vmlinuzes = Path().glob("vmlinuz-*-gentoo*")
    system_maps = Path().glob("System.map*")
    configs = Path().glob("config*")

    version_infos = extract_version_info(vmlinuzes, system_maps, configs)

    # If there's 2 or less versions, exit 
    if len(version_infos) <= 2:
        script_info(f"Only {len(version_infos)} kernels are there, not deleting any")
        return

    # Otherwise delete everything but the 2 newest versions
    # Sort them by age
    # The lowest values (newest) should be first, and highest (oldest) at the end
    version_infos = sorted(version_infos, key=version_cmp, reverse=True)
    script_info(f"sorted version_infos (newest to oldest):")
    for v in version_infos:
        script_info(f"    {v}")

    # Also delete the accompying System map and configs
    num_to_delete = len(version_infos) - 2
    script_info(f"Deleting {num_to_delete} old kernel versions...")
    for _ in range(num_to_delete):
        version_to_delete = version_infos.pop()
        if version_to_delete.is_old:
            script_info(f"Deleting version {version_to_delete.version_triple}.old")
        else:
            script_info(f"Deleting version {version_to_delete.version_triple}")

        # Evidently "unlink" is the same as remove
        script_info(f"Deleting file {str(version_to_delete.vmlinuz.absolute())}")
        version_to_delete.vmlinuz.unlink()
        script_info(f"Deleting file {str(version_to_delete.system_map.absolute())}")
        version_to_delete.system_map.unlink()
        script_info(f"Deleting file {str(version_to_delete.config.absolute())}")
        version_to_delete.config.unlink()


def main():
    """ main """
    init() # Init colorama, not necessarily needed for Linux but why not
    script_info("-----------------------")
    check_perm()
    sync_config()
    compile_kernel()
    install()
    recompile_modules()
    clean_up()
    script_info("-----------------------")

if __name__ == '__main__':
    main()
