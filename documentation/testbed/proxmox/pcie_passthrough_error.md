# How to fix PCIe Passthrough issue in Proxmox

- I ran into the following error while trying to passthrough the Sangoma cards to the VMs.
- I *guess* that this error popped up because of the old hardware.

## The Error
```
vfio_iommu_type1_attach_group: No interrupt remapping support.  Use the module param "allow_unsafe_interrupts" to enable VFIO IOMMU support on this platform
```

## Solution
- On the proxmox host, go to ```/etc/modprobe.d/``` directory and create a file ```vfio_iommu_type1.conf```
- Add the following line to the file and restart the host.
```
options vfio_iommu_type1 allow_unsafe_interrupts=1
```

