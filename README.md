# scripts
Various utility scripts

### build_kernel.py
- **Requires [trash-cli](https://github.com/andreafrancia/trash-cli)**
- **Requires [dev-python/colorama](https://packages.gentoo.org/packages/dev-python/colorama)**
- Helper script for building kernel and out-of-source modules as well as installing to
  my rEFInd boot directory
- Deletes kernels based on age but will always keep the 3 newest kernels in the boot dir
- Requires python's colorama package for color-coded output
- Hard-codes the job count and load averages for building based on my CPU (12 core)
- **TODO** Figure out why trash-cli doesn't work across partitions (`/boot -> /`)
  - just using `rm` for now

### backlight.desktop
- Sets the backlight (brightness) for on login
- For Gnome, use a hardlink and put this in /etc/xdg/autostart
