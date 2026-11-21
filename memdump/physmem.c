// Minimal Android GKI 5.10 module: hexdump a physical memory range into dmesg.
// Loaded with `ksud insmod` which resolves kernel symbols via kallsyms, so no
// Module.symvers / MODVERSIONS CRC matching is required.
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/io.h>
#include <linux/uaccess.h>

static unsigned long phys = 0x808e4000UL;
static unsigned long size = 0x10000UL;
module_param(phys, ulong, 0);
module_param(size, ulong, 0);

static int __init physmem_init(void)
{
	void __iomem *p;
	unsigned int i;

	if (size == 0 || (size & 15)) {
		pr_err("physmem: bad size %lu\n", size);
		return -EINVAL;
	}
	p = ioremap_cache(phys, size);
	if (!p) {
		pr_err("physmem: ioremap(0x%lx, 0x%lx) failed\n", phys, size);
		return -ENOMEM;
	}
	pr_info("physmem: dump of 0x%lx..0x%lx (%lu bytes)\n", phys, phys + size, size);
	for (i = 0; i + 16 <= size; i += 16) {
		const volatile u32 *w = (const volatile u32 *)(p + i);
		if (w[0] == 0xffffffff && w[1] == 0xffffffff && w[2] == 0xffffffff && w[3] == 0xffffffff)
			continue;	/* skip all-FF bitmap rows */
		pr_info("physmem %08lx: %08x %08x %08x %08x\n",
			phys + i, w[0], w[1], w[2], w[3]);
	}
	iounmap(p);
	pr_info("physmem: dump complete\n");
	return 0;
}

static void __exit physmem_exit(void)
{
}

module_init(physmem_init);
module_exit(physmem_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("unicorn port");
MODULE_DESCRIPTION("read a physical memory range into dmesg");
