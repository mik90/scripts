#!/usr/bin/python3
""" Script for building/installing new kernels """

import os
import sys
import subprocess
import shutil
from subprocess import CalledProcessError
from collections import namedtuple
from pathlib import Path
from colorama import init, Fore, Style

""" How many kernel versions should be preserved """
MAX_VERSIONS_TO_KEEP = 2
KERNEL_BUILD_DIR = Path("/usr/src/linux")
INSTALL_PATH = Path("/boot/EFI/Gentoo")


def error_and_exit(error):
    """ print error then exit with return code 1 """
    print(Fore.RED + f"{sys.argv[0]}: " +
          Style.RESET_ALL + f"Error! {error}, exiting...")
    sys.exit(1)


def script_info(info):
    """ print debugging info """
    print(Fore.GREEN + f"{sys.argv[0]}: " + Style.RESET_ALL + f"{info}")


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
            return f"VersionInfo({self.version_triple}.old, {self.vmlinuz}, {self.system_map}, {self.config})"
        else:
            return f"VersionInfo({self.version_triple}, {self.vmlinuz}, {self.system_map}, {self.config})"

    def as_tuple(self):
        """ Convert VersionInfo into a tuple """

        # Indices:
        # 0 1 2 3 4
        # X . Y . Z
        version_triple_split = self.version_triple.split(sep=".")
        major = version_triple_split[0]  # X
        minor = version_triple_split[1]  # Y
        patch = version_triple_split[2]  # Z
        if self.is_old:
            # is .old, penalize it in the sorting by making this -1
            old_adj = -1
        else:
            # is NOT .old, give it an advantage in sorting by making this 0
            old_adj = 0
        return (int(major), int(minor), int(patch), int(old_adj))

    def __eq__(self, other):
        return self.as_tuple() == other.as_tuple()

    def __ne__(self, other):
        return self.as_tuple() != other.as_tuple()

    def __gt__(self, other):
        return self.as_tuple() > other.as_tuple()

    def __ge__(self, other):
        return self > other or self == other

    def __lt__(self, other):
        return self.as_tuple() < other.as_tuple()

    def __le__(self, other):
        return self < other or self == other


class KernelUpdater:
    current_kernels: [VersionInfo] = []

    def __init__(self):
        self.__check_perm()
        self.__find_installed_kernels()

    def __check_perm(self):
        """ ensure that the user is seen as root """
        script_info("Checking permissions")
        if os.geteuid() != 0:
            error_and_exit("This script must be run as root!")
        script_info("Permissions are okay")

    def __update_config(self):
        """ syncing configuration to new kernel """
        os.chdir(str(KERNEL_BUILD_DIR))

        # Could get running config from /proc/config.gz but I'll just copy the newest one in /boot
        # The newest config we have
        src = INSTALL_PATH / self.current_kernels[0].config
        dest = Path(os.getcwd() + "/.config")

        script_info(f"Copying {src.absolute()} to {dest.absolute()}")
        shutil.copy(src, dest)

        script_info(f"syncing configuration to new kernel in {os.getcwd()}")
        try:
            subprocess.run(["make", "syncconfig"], check=True)
        except CalledProcessError as err:
            error_and_exit(err)

    def __compile_kernel(self):
        """ compile just the kernel """
        os.chdir(str(KERNEL_BUILD_DIR))
        script_info(f"Compiling kernel in {os.getcwd()}")
        try:
            subprocess.run(
                ["/bin/bash", "-c", "\"make\" --jobs $(nproc) --load-average $(nproc)"], check=True)
        except CalledProcessError as err:
            error_and_exit(err)

    def __install_new_kernel(self):
        """ install modules and kernel image itself """
        os.chdir(str(KERNEL_BUILD_DIR))

        script_info(f"Installing modules")
        try:
            subprocess.run(["make", "modules_install"], check=True)
        except CalledProcessError as err:
            error_and_exit(err)

        script_info(
            f"Installing kernel image, system map, and config to {str(INSTALL_PATH)}")
        try:
            # This copies over the system environment but appends the INSTALL_PATH variable
            # needed during "make install"
            subprocess.run(["/bin/bash", "-c", "\"make\" install"],
                           env=dict(os.environ, INSTALL_PATH=str(INSTALL_PATH)), check=True)
        except CalledProcessError as err:
            error_and_exit(err)

    def __recompile_extra_modules(self):
        """ recompile out-of-tree modules included by portage (nvidia-drivers) """
        os.chdir(str(KERNEL_BUILD_DIR))
        script_info("Recompiling modules from portage")
        try:
            subprocess.run(["emerge", "@module-rebuild"], check=True)
        except CalledProcessError as err:
            error_and_exit(err)

    def __find_installed_kernels(self):
        """
        Get a set of all the versions and .olds
            - X.Y.Z[.old] preserve the .old aspect if there
        vmlinuzes: a list or generator of strings like "vmlinuz-5.7.5-gentoo.old"
        """
        # Reset current list
        self.current_kernels = []
        os.chdir(str(INSTALL_PATH))
        script_info(
            f"Searching for installed kernel files in {os.getcwd()}...")

        # Find all vmlinuz, config, and system map files
        vmlinuzes = list(Path().glob("vmlinuz-*-gentoo*"))
        system_maps = list(Path().glob("System.map*"))
        configs = list(Path().glob("config*"))

        # Ensure that the 3 lists are the same length
        if not len(list(vmlinuzes)) == len(list(system_maps)) and len(list(system_maps)) == len(list(configs)):
            error_and_exit(f"There are {len(list(vmlinuzes))} vmlinuz files, {len(list(system_maps))} "
                           + f"system maps, and {len(list(configs))} config files")

        for vmlinuz in vmlinuzes:
            version_triple = str(vmlinuz).split(
                sep="-")  # Split up the vmlinuz string
            if len(version_triple) != 3:
                error_and_exit(
                    f"Expected len(version) == 3, got {len(version_triple)}!")
            version_triple = version_triple[1]  # extract the X.Y.Z

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
                system_map = [s for s in system_maps if version_triple in str(
                    s) and str(s).endswith(".old")].pop()
                config = [s for s in configs if version_triple in str(
                    s) and str(s).endswith(".old")].pop()
            else:
                # Ensure that the suffix isn't .old
                system_map = [s for s in system_maps if version_triple in str(
                    s) and not str(s).endswith(".old")].pop()
                config = [s for s in configs if version_triple in str(
                    s) and not str(s).endswith(".old")].pop()

            self.current_kernels.append(VersionInfo(
                version_triple, vmlinuz, system_map, config, is_old))

        self.current_kernels = sorted(self.current_kernels, reverse=True)

    def __clean_up(self):
        """ delete old kernels """

        self.__find_installed_kernels()

        # If there's MAX_VERSIONS_TO_KEEP or less versions, exit
        if len(self.current_kernels) <= MAX_VERSIONS_TO_KEEP:
            script_info(
                f"Only {len(self.current_kernels)} kernels are there, not deleting any")
            return

        # Otherwise delete everything but the 2 newest versions
        # Sort them by age
        # The lowest values (newest) should be first, and highest (oldest) at the end
        self.current_kernels = sorted(self.current_kernels, reverse=True)
        script_info(f"sorted version_infos (newest to oldest):")
        for v in self.current_kernels:
            script_info(f"    {v}")

        # Also delete the accompying System map and configs
        num_to_delete = len(self.current_kernels) - 2
        script_info(f"Deleting {num_to_delete} old kernel versions...")
        for _ in range(num_to_delete):
            kernel_to_delete = self.current_kernels.pop()
            if kernel_to_delete.is_old:
                script_info(
                    f"Deleting version {kernel_to_delete.version_triple}.old")
            else:
                script_info(
                    f"Deleting version {kernel_to_delete.version_triple}")

            # Evidently "unlink" is the same as remove
            script_info(
                f"Deleting file {str(kernel_to_delete.vmlinuz.absolute())}")
            kernel_to_delete.vmlinuz.unlink()
            script_info(
                f"Deleting file {str(kernel_to_delete.system_map.absolute())}")
            kernel_to_delete.system_map.unlink()
            script_info(
                f"Deleting file {str(kernel_to_delete.config.absolute())}")
            kernel_to_delete.config.unlink()

            source_dir = Path(
                f"{KERNEL_BUILD_DIR}/linux-{kernel_to_delete.version_triple}-gentoo")
            script_info(f"Deleting source directory {str(source_dir)}")
            shutil.rmtree(source_dir)

    def update(self):
        """ Run all of the private methods in the proper order """
        # self.__update_config()
        # self.__compile_kernel()
        # self.__install_new_kernel()
        # self.__recompile_extra_modules()
        self.__clean_up()


def main():
    """ main """
    init()  # Init colorama, not necessarily needed for Linux but why not
    script_info("-----------------------")
    updater = KernelUpdater()
    updater.update()
    script_info("-----------------------")


if __name__ == '__main__':
    main()
