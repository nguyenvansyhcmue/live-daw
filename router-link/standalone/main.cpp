#include <iostream>
#include <sstream>
#include <string>

#if STUDIOFORGE_LINK_MACOS
#include "platform/macos/NativeAudio.h"
int main()
{
    using namespace studioforge::link;
    NativeAudio audio; std::string line, error;
    std::cout << "Commands: list, start <device-id>, volume <0..1>, status, stop, quit\n"
                 "Same-device duplex only. Use headphones to prevent feedback.\n";
    while (std::cout << "> " && std::getline(std::cin, line))
    {
        std::istringstream command(line); std::string action; command >> action;
        if (action == "quit") break;
        if (action == "list")
        {
            const auto devices = enumerateDevices(error);
            if (! error.empty()) std::cout << error << '\n';
            else if (devices.empty()) std::cout << "No Core Audio devices visible to this process.\n";
            for (const auto& d : devices)
                std::cout << d.id << " | " << d.name << " | UID " << d.uid << " | input " << d.inputs
                          << " | output " << d.outputs << " | " << (d.alive ? "available" : "offline") << '\n';
        }
        else if (action == "start")
        {
            AudioDeviceID id = 0;
            if (!(command >> id)) std::cout << "Usage: start <device-id>\n";
            else if (! audio.start(id, 0.0f, error)) std::cout << error << '\n';
            else std::cout << "Start requested; volume is 0 for safety. Check status before raising volume.\n";
        }
        else if (action == "volume")
        {
            float gain;
            if (!(command >> gain)) std::cout << "Usage: volume <0..1>\n";
            else if (! audio.setGain(gain, error)) std::cout << error << '\n';
        }
        else if (action == "status") std::cout << audio.status() << '\n';
        else if (action == "stop") { audio.stop(); std::cout << "Stopped.\n"; }
        else std::cout << "Unknown command.\n";
    }
    audio.stop(); return 0;
}
#else
int main() { std::cerr << "Native audio backend is not implemented for this platform.\n"; return 1; }
#endif
