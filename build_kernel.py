#!/usr/bin/python3

# TODO Make script that:
# Compiles kernel with "make $(nproc)"
# installs modules with "make modules_install"
# installs Kernel image with "INSTALL_PATH=/boot/EFI/Gentoo make install"
#   But this should also append the ".efi" to the end of the image name

import os
import subprocess, subprocess.CalledProcessError
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


def rename_kernel():
  # vmlinuz.*gentoo as vmlinuz.*gentoo.efi
  vmlinuzes = Path.glob("/boot/EFI/Gentoo/vmlinuz-*-gentoo")
  for v in vmlinuzes:
    old_name = v.name
    new_name = f"{v.name}.efi"
    script_info(f"Renaming {old_name} to {new_name}")
    Path(v).rename(new_name)

def clean_up():
  efi_gentoo_dir = "/boot/EFI/Gentoo"
  os.chdir(efi_gentoo_dir)
  script_info("Cleaning up old kernels")

  # Find all vmlinuz, config, and system map files
  vmlinuzes = pathlib.Path.glob("/boot/EFI/Gentoo/vmlinuz*.efi")
  system_maps = pathlib.Path.glob("/boot/EFI/Gentoo/System.map*")
  configs = pathlib.Path.glob("/boot/EFI/Gentoo/config*")


  # TODO Ensure that the 3 lists are the same length

  # TODO Get a list of all the versions and .olds
  #   - Counting a .old as a separate version
  #   - Should probably store these in a map of some sort

  # TODO Sort them by age

  # TODO If there's 2 or less versions, leave them be

  # TODO Otherwise delete everything but the 2 newest versions


def main():
  check_perm()
  compile_kernel()
  install()
  clean_up()

if __name__ == 'main':
  main()

