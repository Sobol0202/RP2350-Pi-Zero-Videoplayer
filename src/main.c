/* RP2350-PiZero HDMI-Bildtest + TEST.LOOP-Rohvideoplayer 0.3.1
 *
 * Eingaben: GPIO26 gegen GND, 40ms Entprellung (Pin 37 / Pin 39).
 * Ausgabe: FRANK HDMI Audio auf GPIO32..39, 640x480p60 (Inhalt 320x240).
 * Datei: /TEST.LOOP, 20fps, pro Frame 76800B RGB332 + 6400B PCM.
 * Die 6400B Ton werden noch NICHT wiedergegeben, nur gelesen/verworfen.
 * FAT32/FatFs + SPI1: FRANK-Treiber, Pins SCK30 MOSI31 MISO40 CS43.
 *
 * Abhaengigkeit: im Repository abgelegte FRANK-Treiber (PIO base=16,
 *               64-bit PIO masks). Die Bildwiedergabe wurde auf
 *               RP2350-PiZero Hardware erprobt.
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/clocks.h"
#include "hardware/vreg.h"
#include "ff.h"
#include "frank_hdmi.h"

#define W                320u
#define H                240u
#define FB_BYTES         (W*H)
#define AUDIO_BYTES      6400u
#define FRAME_BYTES      (FB_BYTES + AUDIO_BYTES)
#define FRAME_TIME_US    50000ULL
#define BUTTON_PIN       26u
#define BUTTON_DEBOUNCE  40000ULL
#define TEST_PAGE_TIME   5000000ULL
#define VIDEO_FILE       "0:/TEST.LOOP"

enum { MODE_TEST = 0, MODE_VIDEO = 1, MODE_ERROR = 2 };
enum { ERR_SD = 1, ERR_FILE = 2, ERR_SIZE = 3, ERR_READ = 4 };
#define BLACK   0x00u
#define WHITE   0xFFu
#define RED     0xE0u
#define GREEN   0x1Cu
#define BLUE    0x03u
#define YELLOW  0xFCu
#define CYAN    0x1Fu
#define MAGENTA 0xE3u
#define GRAY    0x92u

static uint8_t fb[2][FB_BYTES] __attribute__((aligned(4)));
static uint8_t scratch_audio[AUDIO_BYTES] __attribute__((aligned(4)));
static FATFS fs;
static FIL file;
static bool is_open;
static uint32_t num_frames;
static uint32_t frame_index;
static uint8_t front = 0;
static uint8_t mode = MODE_TEST;
static uint8_t error_code;
static uint64_t next_frame_us;
static uint64_t test_start_us;
static uint32_t last_test_page = UINT32_MAX;
static uint32_t last_anim_step = UINT32_MAX;
static uint32_t missed_deadlines;

typedef struct {
    bool raw_high;
    bool stable_high;
    uint64_t changed_at;
} button_t;

static void show(uint8_t index) {
    // Core 1 liest den Framebuffer live. Bufferwechsel nur vom Core 0.
    front = index;
    frank_hdmi_set_buffer(fb[front], (int)W, (int)H);
}
static uint8_t back(void) { return (uint8_t)(front ^ 1u); }

static void palette_init(void) {
    for (unsigned i = 0; i < 256; ++i) {
        uint32_t r = (((i >> 5) & 7u) * 255u) / 7u;
        uint32_t g = (((i >> 2) & 7u) * 255u) / 7u;
        uint32_t b = ((i & 3u) * 255u) / 3u;
        frank_hdmi_set_palette((uint8_t)i, (r<<16) | (g<<8) | b);
    }
}
static void button_init(button_t *b) {
    gpio_init(BUTTON_PIN);
    gpio_set_dir(BUTTON_PIN, GPIO_IN);
    gpio_pull_up(BUTTON_PIN);
    b->raw_high = b->stable_high = gpio_get(BUTTON_PIN);
    b->changed_at = time_us_64();
}
static bool button_pressed(button_t *b, uint64_t now) {
    bool high = gpio_get(BUTTON_PIN);
    if (high != b->raw_high) {
        b->raw_high = high;
        b->changed_at = now;
    }
    if (high != b->stable_high && now - b->changed_at >= BUTTON_DEBOUNCE) {
        b->stable_high = high;
        return !high;
    }
    return false;
}
static void fill_rect(uint8_t *dst, int x, int y, int w, int h, uint8_t color) {
    int x0 = x < 0 ? 0 : x;
    int y0 = y < 0 ? 0 : y;
    int x1 = x + w > (int)W ? (int)W : x + w;
    int y1 = y + h > (int)H ? (int)H : y + h;
    for (int yy = y0; yy < y1; ++yy)
        if (x1 > x0) memset(&dst[yy * W + x0], color, (size_t)(x1 - x0));
}
static uint8_t rgb332_gray(uint8_t n) {
    return (uint8_t)((n & 0xE0u) | ((n >> 3u)&0x1Cu) | (n>>6u));
}
static void test_pattern(uint8_t *dst, unsigned page, uint32_t step) {
    switch (page) {
    case 0: memset(dst, BLACK, FB_BYTES); break;
    case 1: memset(dst, WHITE, FB_BYTES); break;
    case 2: memset(dst, RED, FB_BYTES); break;
    case 3: memset(dst, GREEN, FB_BYTES); break;
    case 4: memset(dst, BLUE, FB_BYTES); break;
    case 5: {
        static const uint8_t bars[8] = {WHITE,YELLOW,CYAN,GREEN,
                                         MAGENTA,RED,BLUE,BLACK};
        for (unsigned y=0;y<H;++y) for (unsigned x=0;x<W;++x)
            dst[y*W+x] = bars[x/40];
        break;
    }
    case 6:
        for (unsigned y=0;y<H;++y) for (unsigned x=0;x<W;++x)
            dst[y*W+x] = rgb332_gray((uint8_t)((x/20u)*17u));
        break;
    case 7:
        for (unsigned y=0;y<H;++y) for (unsigned x=0;x<W;++x)
            dst[y*W+x] = ((x%20u)==0 || (y%20u)==0) ? GRAY : BLACK;
        fill_rect(dst, (int)W/2, 0, 1, (int)H, WHITE);
        fill_rect(dst, 0, (int)H/2, (int)W, 1, WHITE);
        break;
    default: {
        memset(dst, BLACK, FB_BYTES);
        unsigned period = 2u * (W - 24u);
        unsigned xpos = (step * 6u) % period;
        if (xpos > W - 24u) xpos = period - xpos;
        fill_rect(dst, (int)xpos, 100, 24, 24, WHITE);
        break;
    }
    }
}

// Kleine gut sichtbare Fehleranzeige, ohne String-/Schriftbibliothek:
// roter Hintergrund und Anzahl gelber Balken == Fehlernummer.
static void show_error(uint8_t err) {
    error_code = err;
    uint8_t *dst = fb[back()];
    memset(dst, RED, FB_BYTES);
    fill_rect(dst, 16, 16, 288, 35, WHITE);
    fill_rect(dst, 20, 20, 280, 27, BLACK);
    for (unsigned i=0; i<err; ++i)
        fill_rect(dst, 38+(int)i*62, 98, 35, 55, YELLOW);
    fill_rect(dst, 16, 205, 288, 8, BLACK);
    show(back());
    mode = MODE_ERROR;
}

static void close_video(void) {
    if (is_open) { f_close(&file); is_open = false; }
}

static bool read_exact(void *dest, UINT len) {
    UINT got = 0;
    return f_read(&file, dest, len, &got) == FR_OK && got == len;
}
static bool read_frame_into(uint8_t *dst) {
    // Wir lesen zur Kompatibilitaet die kompletten Audiobytes, geben sie
    // in V0.3 aber nicht aus. Kein f_lseek pro Frame notwendig.
    if (!read_exact(dst, (UINT)FB_BYTES)) return false;
    if (!read_exact(scratch_audio, (UINT)AUDIO_BYTES)) return false;
    return true;
}
static bool rewind_video(void) {
    return f_lseek(&file, 0) == FR_OK;
}
static bool open_video(void) {
    close_video();
    FRESULT fr = f_mount(&fs, "0:", 1);
    if (fr != FR_OK) { show_error(ERR_SD); return false; }
    fr = f_open(&file, VIDEO_FILE, FA_READ);
    if (fr != FR_OK) { show_error(ERR_FILE); return false; }
    is_open = true;
    FSIZE_t n = f_size(&file);
    if (n < FRAME_BYTES || (n % FRAME_BYTES) != 0) {
        close_video(); show_error(ERR_SIZE); return false;
    }
    num_frames = (uint32_t)(n / FRAME_BYTES);
    frame_index = 0;
    missed_deadlines = 0;
    uint8_t b = back();
    if (!read_frame_into(fb[b])) {
        close_video(); show_error(ERR_READ); return false;
    }
    ++frame_index;
    show(b);
    mode = MODE_VIDEO;
    // Deadline relativ zum ersten sichtbaren Videoframe.
    next_frame_us = time_us_64() + FRAME_TIME_US;
    return true;
}
static void next_video_frame(void) {
    if (!is_open) { show_error(ERR_FILE); return; }
    // Vor naechstem Frame am Dateiende an den Anfang zurueck.
    if (frame_index >= num_frames) {
        if (!rewind_video()) { close_video(); show_error(ERR_READ); return; }
        frame_index = 0;
    }
    uint8_t b = back();
    if (!read_frame_into(fb[b])) {
        close_video(); show_error(ERR_READ); return;
    }
    ++frame_index;
    show(b);
    next_frame_us += FRAME_TIME_US;
    // Wenn die SD-Karte zu langsam ist, keine Blockade-Schleife erzeugen.
    // Bild bleibt bis zum naechsten fertig gelesenen Frame stehen.
    uint64_t now = time_us_64();
    if (now > next_frame_us + 150000ULL) {
        ++missed_deadlines;
        next_frame_us = now + FRAME_TIME_US;
    }
}
static void enter_test(void) {
    close_video();
    mode = MODE_TEST;
    test_start_us = time_us_64();
    last_test_page = UINT32_MAX;
    last_anim_step = UINT32_MAX;
}

int main(void) {
    // Taktdaten entsprechend der mit RP2350-PiZero getesteten Konfiguration.
    vreg_set_voltage(VREG_VOLTAGE_1_50);
    sleep_ms(10);
    set_sys_clock_khz(252000, true);
    button_t button;
    button_init(&button);
    palette_init();
    memset(fb, BLACK, sizeof fb);
    frank_hdmi_init();
    frank_hdmi_set_buffer(fb[front], (int)W, (int)H);
    multicore_launch_core1(frank_hdmi_run_core1);
    enter_test();

    while (true) {
        uint64_t now = time_us_64();
        if (button_pressed(&button, now)) {
            if (mode == MODE_TEST) (void)open_video();
            else enter_test();
        }
        now = time_us_64();
        if (mode == MODE_TEST) {
            uint64_t elapsed = now - test_start_us;
            uint32_t page = (uint32_t)((elapsed / TEST_PAGE_TIME) % 9u);
            uint32_t anim_step = (uint32_t)((elapsed % TEST_PAGE_TIME) / 40000ULL);
            if (page != last_test_page || (page == 8 && anim_step != last_anim_step)) {
                uint8_t b = back();
                test_pattern(fb[b], page, anim_step);
                show(b);
                last_test_page = page;
                last_anim_step = anim_step;
            }
        } else if (mode == MODE_VIDEO) {
            if (now >= next_frame_us)
                next_video_frame();
        }
        // Fehlerbild bleibt stehen, bis Benutzer zum Testmodus zurueckwechselt.
        sleep_ms(1);
    }
}
