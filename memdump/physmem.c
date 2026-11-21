// Android GKI 5.10 module: scan the XNU framebuffer breadcrumb column.
// The breadcrumbs are 72x72 blocks painted by the XNU stage_*() functions at
// fb PA 0xB8000000, column-1 x=64..135 and column-2 x=192..263 (uint32 index).
// A forced (warm) reboot keeps DRAM alive, so the blocks survive into Android;
// this module samples one pixel per fb row and prints the two column colors,
// which decodes exactly which breadcrumb slots were painted.
// Loaded with `ksud insmod` (kallsyms symbol resolution, no MODVERSIONS need).
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/io.h>

static unsigned long phys = 0xB8546000UL;  /* fb + row y240 (240*23040) */
static unsigned long size = 0x2F4A000UL;   /* 2160 rows * 23040 bytes */
static unsigned long stride = 23040UL;     /* fb row stride in bytes */
module_param(phys, ulong, 0);
module_param(size, ulong, 0);
module_param(stride, ulong, 0);

static int __init physmem_init(void)
{
	void __iomem *p;
	unsigned long off;

	if (stride == 0 || size < stride) {
		pr_err("physmem: bad stride/size\n");
		return -EINVAL;
	}
	p = ioremap_cache(phys & ~(unsigned long)0xFFF, (size + 0xFFF) & ~(unsigned long)0xFFF);
	if (!p) {
		pr_err("physmem: ioremap failed\n");
		return -ENOMEM;
	}
	pr_info("physmem: fb scan 0x%lx..0x%lx stride %lu\n", phys, phys + size, stride);
	for (off = 0; off + 1024 <= size; off += stride) {
		const volatile u32 *w = (const volatile u32 *)(p + (phys & 0xFFF) + off);
		u32 c1 = w[100];   /* column-1 block middle (x=64..135) */
		u32 c2 = w[228];   /* column-2 block middle (x=192..263) */
		if (c1 == 0 && c2 == 0)
			continue;
		pr_info("physmem row %08lx: c1=%08x c2=%08x\n",
			phys + off, c1, c2);
	}
	iounmap(p);
	pr_info("physmem: fb scan complete\n");
	return 0;
}

static void __exit physmem_exit(void)
{
}

module_init(physmem_init);
module_exit(physmem_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("unicorn port");
MODULE_DESCRIPTION("scan the XNU fb breadcrumb columns from Android");
