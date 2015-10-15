#!/usr/bin/python
#
#  build.py - create a VirtualBox image running Debian Jessie


#

import os
import sys
import time

__version__='0.1'

# XSysroot details
xsysroot_profile='vbox-debian'
nbdev='/dev/nbd0' # it will be used to create and partition the new image
backing_image=os.path.join(os.path.expanduser('~'), 'osimages/vbox-debian.img')
virtualbox_image='./{}-{}.vdi'.format(xsysroot_profile, __version__)

# VirtualBox image details
arch='i386'
suite='jessie'
repo_url='ftp://ftp.es.debian.org/debian'
cmd_debootstrap='sudo debootstrap --no-check-gpg --verbose --include {} --variant=minbase --arch={} {} {} {}'
extra_pkgs='less,nano,ssh,psmisc,ifplugd,curl,htop,binutils,isc-dhcp-client,iputils-ping,net-tools,sudo'
kernel_image='linux-image-686-pae'
root_password='thor'
grub_bootfile='grub-40-boot.cfg'
hostname='vbox-debian'
motd='Welcome to VirtualBox Debian {}'.format(__version__)


def import_xsysroot():
    '''
    Find path to XSysroot and import it
    You need to create a symlink xsysroot.py -> xsysroot
    '''
    which_xsysroot=os.popen('which xsysroot').read().strip()
    if not which_xsysroot:
        print 'Could not find xsysroot tool'
        print 'Please install from https://github.com/skarbat/xsysroot'
        return None
    else:
        print 'xsysroot found at: {}'.format(which_xsysroot)
        sys.path.append(os.path.dirname(which_xsysroot))
        import xsysroot
        return xsysroot


if __name__=='__main__':

    if os.path.isfile(backing_image):
        print 'backing image exists - aborting:', backing_image
        sys.exit(1)

    xsysroot=import_xsysroot()
    xvbox=xsysroot.XSysroot(profile=xsysroot_profile)

    if xvbox.is_mounted() and not xvbox.umount():
        sys.exit(1)

    print '>>> Creating empty image for OS at {}'.format(time.ctime())
    success=xsysroot.create_image('{} ext3:1000'.format(backing_image), nbdev=nbdev)
    if success:
        # Baptize the image for first time work
        if not xvbox.renew():
            sys.exit(1)

        expanded_debootstrap=cmd_debootstrap.format(extra_pkgs, arch, suite, xvbox.query('sysroot'), repo_url)
        print '>>> Installing core OS... '
        print expanded_debootstrap
        rc=os.system(expanded_debootstrap)
        if rc:
            print 'Error running debootstrap - aborting'
            sys.exiy(1)
    else:
        sys.exit(1)

    # remount image so that /dev and cousins are now correctly mapped to the host
    xvbox.umount()
    if not xvbox.mount():
        sys.exit(1)

    # Install a linux kernel
    print '>>> Installing a kernel and a boot loader'
    xvbox.execute('/bin/bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y --force-yes grub-pc {}"'.format(kernel_image))

    # Along with grub PC Bios version, so VirtualBox can boot it up
    disk_device=xvbox.query('nbdev')
    print '>>> Installing Grub boot code into partition:', disk_device
    xvbox.execute('grub-install --force {}'.format(disk_device))

    # Create an entry for Grub, because the image will be seen as a SCSI disk
    print '>>> Customizing Grub to boot on a Virtualbox SCSI drive'
    os.system('sudo cp {} {}/etc/grub.d/40_custom'.format(grub_bootfile, xvbox.query('sysroot')))
    xvbox.execute('update-grub')

    # Stop the IRQ service. Force root password. Create a hostname, login message
    xvbox.execute('/etc/init.d/irqbalance stop')
    xvbox.execute('/bin/bash -c "echo \'root:{}\' | chpasswd"'.format(root_password))

    # Change some system settings
    xvbox.edfile('/etc/hostname', hostname)
    xvbox.edfile('/etc/hosts', '127.0.0.1   localhost')
    xvbox.edfile('/etc/hosts', '127.0.0.1   {}'.format(hostname), append=True)
    xvbox.edfile('/etc/motd', motd)

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
