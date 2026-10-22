cmake_minimum_required(VERSION 3.22)

# Also allow a developer to build the foundation without building the DAW.
if (CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    project(StudioForgeLink LANGUAGES CXX)
    include(CTest)
endif()

add_library(StudioForgeLinkCore STATIC core/AudioFormat.cpp core/RoutingCore.cpp)
target_compile_features(StudioForgeLinkCore PUBLIC cxx_std_20)
target_include_directories(StudioForgeLinkCore PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}")

# Keep local development deterministic while allowing the release build to
# supply a real Developer ID identity. The identity is intentionally a CMake
# cache value rather than a source edit or an environment-only convention:
# CI/release jobs can record exactly how the final .driver was signed.
set(STUDIOFORGE_LINK_CODESIGN_IDENTITY "-" CACHE STRING
    "codesign identity for StudioForge Link HAL; '-' uses an ad-hoc local seal")

# This is the real-time PCM transport used inside the future macOS HAL driver.
# It is intentionally not a driver bundle or an in-process substitute for one.
add_library(StudioForgeLinkVirtualDeviceTransport STATIC
    virtual-device/macos/StereoLoopbackRing.cpp
    virtual-device/macos/VirtualInputFormat.cpp)
target_compile_features(StudioForgeLinkVirtualDeviceTransport PUBLIC cxx_std_20)
target_include_directories(StudioForgeLinkVirtualDeviceTransport PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}")

# Phase 00 controller is a diagnostic entry point, not an audio application.
add_executable(StudioForgeLinkController standalone/main.cpp)
target_link_libraries(StudioForgeLinkController PRIVATE StudioForgeLinkCore)
if (APPLE)
    target_sources(StudioForgeLinkController PRIVATE platform/macos/NativeAudio.cpp)
    target_compile_definitions(StudioForgeLinkController PRIVATE STUDIOFORGE_LINK_MACOS=1)
    target_link_libraries(StudioForgeLinkController PRIVATE "-framework CoreAudio" "-framework CoreFoundation")

    # Read-only readiness check for the future AudioServerPlugIn bundle. This
    # target does not imply that an OS-visible driver has been implemented.
    add_executable(StudioForgeLinkHalPreflight virtual-device/macos/HalPreflight.cpp)
    target_compile_features(StudioForgeLinkHalPreflight PRIVATE cxx_std_20)
    # Let the read-only preflight inspect the artifact built by this tree by
    # default. An explicit STUDIOFORGE_LINK_HAL_BUNDLE environment value can
    # still be used to inspect a separately signed candidate.
    target_compile_definitions(StudioForgeLinkHalPreflight PRIVATE
        STUDIOFORGE_LINK_HAL_DEFAULT_BUNDLE="$<TARGET_BUNDLE_DIR:StudioForgeLinkHAL>")
    add_dependencies(StudioForgeLinkHalPreflight StudioForgeLinkHAL)
    target_link_libraries(StudioForgeLinkHalPreflight PRIVATE "-framework CoreAudio" "-framework CoreFoundation")

    # Explicitly invoked native diagnostic; it never changes system defaults.
    add_executable(StudioForgeLinkHalNativeProbe tests/HalNativeProbe.cpp)
    target_compile_features(StudioForgeLinkHalNativeProbe PRIVATE cxx_std_20)
    target_link_libraries(StudioForgeLinkHalNativeProbe PRIVATE "-framework CoreAudio" "-framework CoreFoundation")

    # Read-only environment report for comparing the restricted build agent
    # with a Terminal launched by the logged-in user.
    add_executable(StudioForgeCoreAudioEnvironmentProbe tests/CoreAudioEnvironmentProbe.cpp)
    target_compile_features(StudioForgeCoreAudioEnvironmentProbe PRIVATE cxx_std_20)
    target_link_libraries(StudioForgeCoreAudioEnvironmentProbe PRIVATE "-framework CoreAudio" "-framework CoreFoundation")

    # A loadable AudioServerPlugIn bundle, intentionally separate from the
    # DAW executable. Installation and production signing remain separate.
    add_library(StudioForgeLinkHAL MODULE
        virtual-device/macos/StudioForgeLinkHAL.cpp
        virtual-device/macos/HalDuplexLoopback.cpp)
    target_compile_features(StudioForgeLinkHAL PRIVATE cxx_std_20)
    target_include_directories(StudioForgeLinkHAL PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    target_link_libraries(StudioForgeLinkHAL PRIVATE "-framework CoreAudio" "-framework CoreFoundation")
    set_target_properties(StudioForgeLinkHAL PROPERTIES
        BUNDLE TRUE
        BUNDLE_EXTENSION driver
        PREFIX ""
        OUTPUT_NAME "StudioForgeLinkHAL"
        MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/virtual-device/macos/StudioForgeLinkHAL-Info.plist.in")

    # The linker signs only the Mach-O; seal the complete bundle after linking.
    # '-' is an ad-hoc local integrity seal. A non-empty Apple-issued identity
    # signs the completed bundle with a secure timestamp. Never use --deep:
    # every nested code item must be explicitly signed before its parent.
    find_program(STUDIOFORGE_CODESIGN_EXECUTABLE codesign REQUIRED)
    if (STUDIOFORGE_LINK_CODESIGN_IDENTITY STREQUAL "-")
        set(STUDIOFORGE_LINK_CODESIGN_TIMESTAMP_ARG "--timestamp=none")
    else()
        set(STUDIOFORGE_LINK_CODESIGN_TIMESTAMP_ARG "--timestamp")
    endif()
    add_custom_command(TARGET StudioForgeLinkHAL POST_BUILD
        COMMAND "${STUDIOFORGE_CODESIGN_EXECUTABLE}" --force --sign "${STUDIOFORGE_LINK_CODESIGN_IDENTITY}"
                "${STUDIOFORGE_LINK_CODESIGN_TIMESTAMP_ARG}"
                "$<TARGET_BUNDLE_DIR:StudioForgeLinkHAL>"
        VERBATIM)

    if (BUILD_TESTING)
        add_executable(StudioForgeLinkHalFoundationTests tests/HalFoundationTests.cpp)
        add_dependencies(StudioForgeLinkHalFoundationTests StudioForgeLinkHAL)
        target_compile_features(StudioForgeLinkHalFoundationTests PRIVATE cxx_std_20)
        target_compile_definitions(StudioForgeLinkHalFoundationTests PRIVATE
            STUDIOFORGE_LINK_HAL_BINARY="$<TARGET_BUNDLE_DIR:StudioForgeLinkHAL>/Contents/MacOS/StudioForgeLinkHAL")
        target_link_libraries(StudioForgeLinkHalFoundationTests PRIVATE "-framework CoreAudio" "-framework CoreFoundation")
        add_test(NAME StudioForgeLinkHalFoundationTests COMMAND StudioForgeLinkHalFoundationTests)
        add_executable(StudioForgeLinkHalLoopbackTests tests/HalDuplexLoopbackTests.cpp
            virtual-device/macos/HalDuplexLoopback.cpp)
        target_compile_features(StudioForgeLinkHalLoopbackTests PRIVATE cxx_std_20)
        target_include_directories(StudioForgeLinkHalLoopbackTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
        add_test(NAME StudioForgeLinkHalLoopbackTests COMMAND StudioForgeLinkHalLoopbackTests)
    endif()
endif()

if (BUILD_TESTING)
    add_executable(StudioForgeLinkSmokeTest tests/AudioFormatSmokeTest.cpp)
    target_link_libraries(StudioForgeLinkSmokeTest PRIVATE StudioForgeLinkCore)
    add_test(NAME StudioForgeLinkSmokeTest COMMAND StudioForgeLinkSmokeTest)
    add_executable(StudioForgeLinkRoutingTests tests/RoutingCoreTests.cpp)
    find_package(Threads REQUIRED)
    target_link_libraries(StudioForgeLinkRoutingTests PRIVATE StudioForgeLinkCore Threads::Threads)
    add_test(NAME StudioForgeLinkRoutingTests COMMAND StudioForgeLinkRoutingTests)
    add_executable(StudioForgeLinkVirtualDeviceTransportTests tests/StereoLoopbackRingTests.cpp)
    target_link_libraries(StudioForgeLinkVirtualDeviceTransportTests PRIVATE StudioForgeLinkVirtualDeviceTransport)
    add_test(NAME StudioForgeLinkVirtualDeviceTransportTests COMMAND StudioForgeLinkVirtualDeviceTransportTests)
    add_executable(StudioForgeLinkVirtualInputFormatTests tests/VirtualInputFormatTests.cpp)
    target_link_libraries(StudioForgeLinkVirtualInputFormatTests PRIVATE StudioForgeLinkVirtualDeviceTransport)
    add_test(NAME StudioForgeLinkVirtualInputFormatTests COMMAND StudioForgeLinkVirtualInputFormatTests)
    # Tests use assert deliberately; release builds must not silently turn all
    # test conditions into no-ops via the parent application's NDEBUG flag.
    foreach(link_test StudioForgeLinkSmokeTest StudioForgeLinkRoutingTests
                      StudioForgeLinkVirtualDeviceTransportTests StudioForgeLinkVirtualInputFormatTests)
        if (MSVC)
            target_compile_options(${link_test} PRIVATE /UNDEBUG)
        else()
            target_compile_options(${link_test} PRIVATE -UNDEBUG)
        endif()
    endforeach()
    if (APPLE)
        target_compile_options(StudioForgeLinkHalFoundationTests PRIVATE -UNDEBUG)
        target_compile_options(StudioForgeLinkHalLoopbackTests PRIVATE -UNDEBUG)
    endif()
endif()
