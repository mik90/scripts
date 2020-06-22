#!/usr/bin/python3

import os
import subprocess
from subprocess import CalledProcessError
import pathlib
from pathlib import Path

def error_and_exit(error):
  print(f"build_kernel.py: Error:{error}, exiting...")
  exit(1)

def script_info(info):
  print(f"build_kernel.py: {info}")

def check_perm():
  script_info("Checking permissions")
  if os.geteuid() != 0:
    error_and_exit("This script must be run as root!")

def compile_kernel():
  os.chdir("/usr/src/linux")
  script_info("Compiling kernel")
  try:
    subprocess.run(["make", "$(nproc)"], check=True)
  except CalledProcessError as err:
    error_and_exit(err)

def install():
  os.chdir("/usr/src/linux")

  script_info("Installing modules")
  try:
    subprocess.run(["make", "modules_install"], check=True)
  except CalledProcessError as err:
    error_and_exit(err)

  script_info("Installing kernel image, system map, and config")
  try:
    subprocess.run(["make", "install"],
            env={"INSTALL_PATH" : "/boot/EFI/Gentoo"}, check=True)
  except CalledProcessError as err:
    error_and_exit(err)


def clean_up():
  # Maybe preserve lts kernels as well?

  efi_gentoo_dir = "/boot/EFI/Gentoo"
  os.chdir(efi_gentoo_dir)
  script_info("Cleaning up old kernels")

  # Find all vmlinuz, config, and system map files
  vmlinuzes = Path().glob("/boot/EFI/Gentoo/vmlinuz-*-gentoo")
  system_maps = Path().glob("/boot/EFI/Gentoo/System.map*")
  configs = Path().glob("/boot/EFI/Gentoo/config*")

  # Ensure that the 3 lists are the same length
  if not len(list(vmlinuzes))  == len(list(system_maps)) == len(list(configs)):
    error_and_exit(f"There are {len(list(vmlinuzes))} vmlinuz files, {len(list(system_maps))} "
                    + f"system maps, and {len(list(configs))} config files")

  # TODO Get a list of all the versions and .olds
  #   - Counting a .old as a separate version
  #   - Should probably store these in a map of some sort
  #     - X.Y.Z[.old] so preserve the .old aspect

  # TODO Sort them by age

  # TODO If there's 2 or less versions, leave them be

  # TODO Otherwise delete everything but the 2 newest versions


def main():
  check_perm()
  compile_kernel()
  install()
  #clean_up()

if __name__ == 'main':
  main()

