/* FatFs integration for the standalone RP2350 PiZero video player.
 * The FRANK emulator's ffsystem.c uses an optional PSRAM allocator;
 * for this application we use the normal SRAM heap instead.
 * Do not compile FRANK's ffsystem.c at the same time.
 */
#include "ff.h"
#include <stdlib.h>

#if FF_USE_LFN == 3
void *ff_memalloc(UINT size) {
    return malloc((size_t)size);
}

void ff_memfree(void *ptr) {
    free(ptr);
}
#endif

/* The SD-card driver itself implements get_fattime() for FF_FS_NORTC == 0.
 * FF_FS_REENTRANT is 0 in the FRANK FatFs configuration used here.
 */
#if FF_FS_REENTRANT
#error "This FatFs heap port requires FF_FS_REENTRANT=0"
#endif
