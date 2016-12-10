#!/usr/bin/python
#
#  build.py - create a VirtualBox image running Debian Jessie
#

import os
import sys
import time
import xsysroot

__version__='0.3'

# XSysroot details
xsysroot_profile='vbox-debian'
backing_image=os.path.join(os.path.expanduser('~'), 'osimages/vbox-debian.img')
virtualbox_image='./{}-{}.vdi'.format(xsysroot_profile, __version__)

# VirtualBox image details
arch='i386'
suite='jessie'
repo_url='ftp://ftp.uk.debian.org/debian'
cmd_debootstrap='sudo debootstrap --no-check-gpg --verbose --include {} --variant=minbase --arch={} {} {} {}'
extra_pkgs='less,nano,ssh,psmisc,ifplugd,curl,htop,binutils,isc-dhcp-client,iputils-ping,net-tools,sudo'
kernel_image='linux-image-686-pae'
root_password='thor'
grub_bootfile='grub-40-boot.cfg'
hostname='debianvm'
motd='Welcome to Debian VM {}'.format(__version__)



if __name__=='__main__':

    if os.path.isfile(backing_image):
        print 'backing image already exists - aborting:', backing_image
        sys.exit(1)

    xvbox=xsysroot.XSysroot(profile=xsysroot_profile)
    if xvbox.is_mounted() and not xvbox.umount():
        sys.exit(1)

    print '>>> Creating empty image for OS at {}'.format(time.ctime())
    if not xsysroot.create_image('{} ext4:1000'.format(backing_image)):
        sys.exit(1)

    # Baptize the image for first time work
    if not xvbox.renew():
        sys.exit(1)

    expanded_debootstrap=cmd_debootstrap.format(extra_pkgs, arch, suite, xvbox.query('sysroot'), repo_url)
    print '>>> Installing core OS... '
    print expanded_debootstrap
    rc=os.system(expanded_debootstrap)
    if rc:
        print 'Error running debootstrap - aborting'
        sys.exit(1)

    # remount image so that /dev and cousins are now correctly mapped to the host
    xvbox.umount()
    if not xvbox.mount():
        sys.exit(1)

    # Install a linux kernel
    print '>>> Installing a kernel and a boot loader'
    install_command='DEBIAN_FRONTEND=noninteractive apt-get install -y --force-yes grub-pc {}'.format(kernel_image)
    xvbox.execute('/bin/bash -c "{}"'.format(install_command))

    # Along with grub PC Bios version, so VirtualBox can boot it up
    disk_device=xvbox.query('nbdev')
    print '>>> Installing Grub boot code into partition:', disk_device
    xvbox.execute('grub-install --force {}'.format(disk_device))

    # Create an entry for Grub, because the image will be seen as a SCSI disk
    print '>>> Customizing Grub to boot on a Virtualbox SCSI drive'
    os.system('sudo cp {} {}/etc/grub.d/40_custom'.format(grub_bootfile, xvbox.query('sysroot')))
    xvbox.execute('rm /etc/grub.d/10_linux')
    xvbox.execute('rm /etc/grub.d/20_linux_xen')
    xvbox.execute('update-grub')

    # Stop the IRQ service. Force root password. Create a hostname, login message
    xvbox.execute('/etc/init.d/irqbalance stop')
    xvbox.execute('/bin/bash -c "echo \'root:{}\' | chpasswd"'.format(root_password))

    # Change some system settings
    xvbox.edfile('/etc/hostname', hostname)
    xvbox.edfile('/etc/hosts', '127.0.0.1   localhost')
    xvbox.edfile('/etc/hosts', '127.0.0.1   {}'.format(hostname), append=True)
    xvbox.edfile('/etc/motd', motd)
    xvbox.edfile('/etc/debianvm_version', __version__)

    # setup ethernet to get a dhcp lease
    interfaces_file='/etc/network/interfaces'
    xvbox.edfile(interfaces_file, 'auto eth0')
    xvbox.edfile(interfaces_file, 'iface eth0 inet dhcp', append=True)

    # permit root to login through ssh
    sshd_config='/etc/ssh/sshd_config'
    xvbox.execute("sed -e '/PermitRootLogin.*/ s/^#*/#/' -i {}".format(sshd_config))

    print '>>> Generating VirtualBox bootable image', virtualbox_image
    if not xvbox.umount():
        sys.exit(1)

    os.system('qemu-img convert -f qcow2 -O vdi {} {}'.format(xvbox.query('qcow_image'), virtualbox_image))
    print '>>> Build complete at {} !'.format(time.ctime())
    sys.exit(0)
