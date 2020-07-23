# scripts
Various utility scripts

### build_kernel.py
- Helper script for building kernel and out-of-source modules as well as installing to
  my rEFInd boot directory
- Deletes kernels based on age but will always keep the 3 newest kernels in the boot dir
- Requires python's colorama package for color-coded output
- Hard-codes the job count and load averages for building based on my CPU (12 core)
