#!/usr/bin/python3
""" Script for building/installing new kernels """

import os
import sys
import subprocess
import shutil
import argparse
import time
import configparser
from subprocess import CalledProcessError
from pathlib import Path
from colorama import init, Fore, Style


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

    def __init__(self, version_triple: str, vmlinuz: Path, system_map: Path, config: Path, is_old: bool, kernel_modules_path: Path):
        self.version_triple = version_triple
        self.vmlinuz = vmlinuz
        self.system_map = system_map
        self.config = config
        self.is_old = is_old
        self.__kernel_modules_path = kernel_modules_path

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

    def remove(self):
        if self.is_old:
            script_info(
                f"Deleting version {self.version_triple}.old")
        else:
            script_info(
                f"Deleting version {self.version_triple}")

        # Evidently "unlink" is the same as remove
        script_info(
            f"Deleting file {str(self.vmlinuz.absolute())}")
        self.vmlinuz.unlink()
        script_info(
            f"Deleting file {str(self.system_map.absolute())}")
        self.system_map.unlink()
        script_info(
            f"Deleting file {str(self.config.absolute())}")
        self.config.unlink()

        source_dir = Path(
            f"/usr/src/linux-{self.version_triple}-gentoo")
        script_info(f"Deleting source directory {str(source_dir)}")
        shutil.rmtree(source_dir)

        if not self.is_old:
            # Assume that there's a non .old kernel that's using the modules
            modules_dir = Path(
                f"{self.__kernel_modules_path}/{self.version_triple}-gentoo")
            script_info(f"Deleting kernel modules in {str(modules_dir)}")
            shutil.rmtree(modules_dir)

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
    """
    Contains all the logic for building and installing a new kernel.
    Run using the update() method
    """

    def __init__(self, manual_edit: bool, install_path: Path, kernel_source_path: Path, kernel_modules_path: Path,
                 versions_to_keep: int, clean_only: bool, gen_grub_config: bool):
        self.__manual_edit = manual_edit
        self.__install_path = install_path
        self.__kernel_source_path = kernel_source_path
        self.__kernel_modules_path = kernel_modules_path
        self.__versions_to_keep = versions_to_keep
        self.__clean_only = clean_only
        self.__gen_grub_config = gen_grub_config
        self.__current_kernels: [VersionInfo] = []
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
        os.chdir(str(self.__kernel_source_path))

        # Could get running config from /proc/config.gz but I'll just copy the newest one in /boot
        # The newest config we have
        src = self.__install_path / self.__current_kernels[0].config
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
        os.chdir(str(self.__kernel_source_path))
        script_info(f"Compiling kernel in {os.getcwd()}")
        try:
            subprocess.run(
                ["/bin/bash", "-c", "\"make\" --jobs $(nproc) --load-average $(nproc)"], check=True)
        except CalledProcessError as err:
            error_and_exit(err)

    def __install_new_kernel(self):
        """ install modules and kernel image itself """
        os.chdir(str(self.__kernel_source_path))

        script_info("Installing modules")
        try:
            subprocess.run(["make", "modules_install"], check=True)
        except CalledProcessError as err:
            error_and_exit(err)

        script_info(
            f"Installing kernel image, system map, and config to {str(self.__install_path)}")
        try:
            # This copies over the system environment but appends the INSTALL_PATH variable
            # needed during "make install"
            subprocess.run(["/bin/bash", "-c", "\"make\" install"],
                           env=dict(os.environ, INSTALL_PATH=str(self.__install_path)), check=True)
        except CalledProcessError as err:
            error_and_exit(err)

    def __recompile_extra_modules(self):
        """ recompile out-of-tree modules included by portage (nvidia-drivers) """
        os.chdir(str(self.__kernel_source_path))
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
        self.__current_kernels = []
        os.chdir(str(self.__install_path))
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
            system_maps = Path().glob("System.map*")
            configs = Path().glob("config*")
            if is_old:
                # Iterate thr__clean_upe ends with .old
                # Note: .pop() is a lazy way to convert a single-element list to the underlying type
                #
                # Be extra sure that the suffix is .old
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

            self.__current_kernels.append(VersionInfo(
                version_triple, vmlinuz, system_map, config, is_old, self.__kernel_modules_path))

        self.__current_kernels = sorted(self.__current_kernels, reverse=True)

    def __grub_mk_config(self):
        """ Generate grub config """
        grub_cfg_location = f"{self.__install_path}/grub/grub.cfg"
        script_info(f"Regenerating grub configuration at {grub_cfg_location}")

        try:
            subprocess.run(
                ["grub-mkconfig", "-o", grub_cfg_location], check=True)
        except CalledProcessError as err:
            error_and_exit(err)

    def __clean_up(self):
        """ delete old kernels """

        self.__find_installed_kernels()

        # If there's MAX_VERSIONS_TO_KEEP or less versions, exit
        if len(self.__current_kernels) <= len(self.__versions_to_keep):
            script_info(
                f"Only {len(self.__current_kernels)} kernels are there, not deleting any")
            return

        # Otherwise delete everything but the 2 newest versions
        # Sort them by age
        # The lowest values (newest) should be first, and highest (oldest) at the end
        self.__current_kernels = sorted(self.__current_kernels, reverse=True)
        script_info(f"sorted version_infos (newest to oldest):")
        for v in self.__current_kernels:
            script_info(f"    {v}")

        # Also delete the accompying System map and configs
        num_to_delete = len(self.__current_kernels) - 2
        script_info(f"Deleting {num_to_delete} old kernel versions...")
        for _ in range(num_to_delete):
            self.__current_kernels.pop().remove()

    def update(self):
        """ Run all of the private methods in the proper order """
        if self.__clean_only:
            script_info("Cleaning and then returning...")
            self.__clean_up()
            return

        if self.__manual_edit:
            script_info("Using user-updated configuration")
        else:
            # Do nothing, assume that the user updated the config
            script_info("Updating configuration automatically")
            self.__update_config()

        self.__compile_kernel()
        self.__install_new_kernel()
        self.__recompile_extra_modules()
        self.__clean_up()
        if self.__gen_grub_config:
            self.__grub_mk_config()


def str_to_bool(string: str):
    if string.lower() in ["true", "t", "1", "on", "yes"]:
        return True
    elif string.lower() in ["false", "f", "0", "off", "no"]:
        return False
    else:
        raise TypeError(f"Could not parse {string} as boolean")


def main():
    """ main """
    parser = argparse.ArgumentParser(
        description='Build and install the Linux kernel.')
    parser.add_argument(
        '-m', '--manual-edit', dest='manual_edit', action='store_true',
        help="Let the user copy over and edit the kernel configuration before building. \
              By default, configuration will be copied over automatically.")
    parser.add_argument(
        '-c', '--clean-only', dest='clean_only', action='store_false',
        help="Clean up the install, source, and module directories then exit")
    parser.set_defaults(manual_edit=False, clean_only=False)
    args = parser.parse_args()

    init()  # Init colorama, not necessarily needed for Linux but why not
    script_info("-----------------------")

    if args.manual_edit == False:
        script_info(
            "Manual editing disabled. Kernel config will be automatically updated.")
    else:
        script_info(
            "Manual editing enabled. Assuming user updated the configuration manually.")

    config = configparser.ConfigParser()
    possible_conf_files = [
        Path("build_kernel.conf"),
        Path.home() / Path(".config/build_kernel.conf")
    ]

    try:
        config_file = next(x for x in possible_conf_files if x.exists())
    except StopIteration:
        error_and_exit(
            f"could not find build_kernel.conf in {''.join(map(str, possible_conf_files))}")

    script_info(f"Using conf file {str(config_file)}")
    config.read(str(config_file))
    # Any of these will throw if there's an issue
    try:
        install_path = config["paths"]["InstallPath"]
    except ValueError:
        error_and_exit("No InstallPath was configured!")

    try:
        source_path = config["paths"]["KernelSourcePath"]
    except ValueError:
        error_and_exit("No KernelSourcePath was configured!")

    try:
        modules_path = config["paths"]["KernelModulesPath"]
    except ValueError:
        error_and_exit("No KernelModulesPath was configured!")

    try:
        versions_to_keep = config["settings"]["VersionsToKeep"]
    except ValueError:
        error_and_exit("No VersionsToKeep was configured!")

    try:
        gen_grub_config = str_to_bool(
            config["settings"]["RegenerateGrubConfig"])
    except ValueError:
        error_and_exit(" RegenerateGrubConfig was not configured!")

    updater = KernelUpdater(manual_edit=args.manual_edit,
                            install_path=install_path,
                            kernel_source_path=source_path,
                            kernel_modules_path=modules_path,
                            versions_to_keep=versions_to_keep,
                            clean_only=args.clean_only,
                            gen_grub_config=gen_grub_config)
    updater.update()
    script_info("-----------------------")


if __name__ == '__main__':
    main()
