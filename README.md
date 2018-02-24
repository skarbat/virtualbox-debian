## VirtualBox Debian Jessie

This tiny tool will allow you to create a Debian Jessie for Intel/AMD 32 bit ready to boot inside VirtualBox.

### Building

You will need a Linux system to build the image. Debian is a very good candidate.

Download and install `xsysroot`: https://github.com/skarbat/xsysroot, also install `debootsrap`.

Copy the file `xsysroot.conf` from this folder to your home directory, and do:

```
 $ python -u build.py >build.log 2>&1
```

On completion you should get a VDI file. This is all you need to create the VirtualBox VM.

### VirtualBox setup

Open Virtual box and create a new Linux Debian virtual machine.

When asked to create a disk, choose a SCSI controller, and select the VDI file generated above.
Make sure you enable the PAE option in the Machine tab settings, then boot the VM.

### Booting the VM

When starting the virtual machine, Grub should come up with an entry called Debian VM,
and boot the system directly after a few seconds.

You should get a login prompt shortly after. Use *root* for the username and *thor* for password.

The virtual machine should acquire an IP from Virtualbox, you can ssh remotely into it as root.

Enjoy!

Albert - September 2015.
