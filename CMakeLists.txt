cmake_minimum_required(VERSION 3.13)

# RP2350-PiZero: GPIOs >31 erfordern die B-Variante des RP2350.
# Eingebettete Treiber werden mit tools/vendor_frank.py bereitgestellt.
set(FRANK_MICRO_DIR "${CMAKE_CURRENT_LIST_DIR}/third_party/frank-micro" CACHE PATH
    "Verzeichnis mit FRANK-Treibern, standardmaessig lokaler Snapshot")
if(NOT EXISTS "${FRANK_MICRO_DIR}/frank-hdmi-sound/src/CMakeLists.txt")
    message(FATAL_ERROR
        "FRANK-Treiber fehlen. Zuerst ausfuehren: python tools/vendor_frank.py ../frank-micro ")
endif()
if(NOT EXISTS "${FRANK_MICRO_DIR}/drivers/sdcard/CMakeLists.txt")
    message(FATAL_ERROR "FRANK-SD-Kartentreiber fehlen unter FRANK_MICRO_DIR")
endif()

set(PICO_BOARD_HEADER_DIRS "${FRANK_MICRO_DIR}/src/boards" CACHE PATH "" FORCE)
set(PICO_BOARD waveshare_rp2350_pizero CACHE STRING "" FORCE)
set(PICO_PLATFORM rp2350-arm-s CACHE STRING "" FORCE)

if(NOT DEFINED ENV{PICO_SDK_PATH})
    message(FATAL_ERROR "PICO_SDK_PATH auf das Pico SDK setzen")
endif()
include("$ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake")
project(pico_hdmi_player C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
pico_sdk_init()

# 252 MHz TMDS/CPU; PIO-Treiber besitzt die Z0-GPIO-Korrekturen.
set(FRANK_HDMI_SM_CLKDIV "1" CACHE STRING "" FORCE)
add_subdirectory("${FRANK_MICRO_DIR}/frank-hdmi-sound/src"
                 "${CMAKE_BINARY_DIR}/frank-hdmi-sound")

# Nur FatFs-Kernmodule. FRANKs ffsystem.c braucht einen PSRAM-Allocator;
# der Ersatz unten verwendet stattdessen den normalen SRAM-Heap.
add_library(fatfs INTERFACE)
target_sources(fatfs INTERFACE
    "${FRANK_MICRO_DIR}/drivers/fatfs/ff.c"
    "${FRANK_MICRO_DIR}/drivers/fatfs/ffunicode.c"
    "${CMAKE_CURRENT_LIST_DIR}/src/fatfs_heap.c"
)
target_include_directories(fatfs INTERFACE "${FRANK_MICRO_DIR}/drivers/fatfs")
add_subdirectory("${FRANK_MICRO_DIR}/drivers/sdcard"
                 "${CMAKE_BINARY_DIR}/frank-sdcard")

target_compile_definitions(frank_hdmi_sound INTERFACE
    FRANK_HDMI_PIN_CLK=38
    FRANK_HDMI_PIN_D0=36
    FRANK_HDMI_PIN_D1=34
    FRANK_HDMI_PIN_D2=32
    FRANK_HDMI_INVERT_DIFFPAIRS=0
    PLATFORM_Z0=1
    PICO_PIO_USE_GPIO_BASE=1
    FRANK_HDMI_AUDIO_RATE=32000
)

add_executable(pico_hdmi_player src/main.c)
target_compile_definitions(pico_hdmi_player PRIVATE
    SDCARD_SPI_BUS=spi1
    SDCARD_PIN_SPI0_CS=43
    SDCARD_PIN_SPI0_SCK=30
    SDCARD_PIN_SPI0_MOSI=31
    SDCARD_PIN_SPI0_MISO=40
)
target_link_libraries(pico_hdmi_player PRIVATE
    pico_stdlib pico_multicore hardware_clocks hardware_vreg
    hardware_spi hardware_pio hardware_dma
    frank_hdmi_sound fatfs sdcard)

pico_enable_stdio_usb(pico_hdmi_player 0)
pico_enable_stdio_uart(pico_hdmi_player 0)
pico_add_extra_outputs(pico_hdmi_player)
target_link_options(pico_hdmi_player PRIVATE
    -Xlinker --print-memory-usage --data-sections --function-sections)
