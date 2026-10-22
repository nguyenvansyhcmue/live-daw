#include <CoreAudio/AudioServerPlugIn.h>

#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <unistd.h>

// Intentionally a read-only diagnostic. It neither installs, restarts
// coreaudiod, alters the default device nor requests elevated privileges.
int main()
{
    namespace fs = std::filesystem;
    const fs::path installDirectory { "/Library/Audio/Plug-Ins/HAL" };
    const char* configuredBundle = std::getenv("STUDIOFORGE_LINK_HAL_BUNDLE");
#ifdef STUDIOFORGE_LINK_HAL_DEFAULT_BUNDLE
    const fs::path defaultBundle { STUDIOFORGE_LINK_HAL_DEFAULT_BUNDLE };
#endif

    std::cout << "StudioForge Link macOS HAL preflight\n";
    std::cout << "AudioServerPlugIn SDK header: available\n";
    std::cout << "HAL install directory: " << installDirectory << " ("
              << (fs::is_directory(installDirectory) ? "present" : "missing") << ")\n";
    std::cout << "Current process can install there: "
              << (::access(installDirectory.c_str(), W_OK) == 0 ? "yes" : "no") << "\n";

    const fs::path bundle = configuredBundle != nullptr && *configuredBundle != '\0'
        ? fs::path { configuredBundle }
#ifdef STUDIOFORGE_LINK_HAL_DEFAULT_BUNDLE
        : defaultBundle;
#else
        : fs::path {};
#endif
    if (bundle.empty())
    {
        std::cout << "Driver bundle: not supplied (set STUDIOFORGE_LINK_HAL_BUNDLE to inspect one)\n";
        std::cout << "Result: BLOCKED — no candidate bundle was available for preflight.\n";
        return 0;
    }
    const auto info = bundle / "Contents/Info.plist";
    const auto executable = bundle / "Contents/MacOS/StudioForgeLinkHAL";
    std::cout << "Driver bundle: " << bundle << " (" << (fs::is_directory(bundle) ? "present" : "missing") << ")\n";
    std::cout << "Info.plist: " << (fs::is_regular_file(info) ? "present" : "missing") << "\n";
    std::cout << "Executable: " << (fs::is_regular_file(executable) ? "present" : "missing") << "\n";
    std::cout << "Result: "
              << ((fs::is_directory(bundle) && fs::is_regular_file(info) && fs::is_regular_file(executable))
                    ? "bundle shape present; signing and external-app PCM verification still required."
                    : "BLOCKED — bundle is not installable." ) << "\n";
}
