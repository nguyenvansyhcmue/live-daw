#include "PerformanceSurfaceBridge.h"

#include <memory>

#if JUCE_MAC || JUCE_LINUX
 #include <cerrno>
 #include <cstring>
 #include <arpa/inet.h>
 #include <netinet/in.h>
 #include <sys/select.h>
 #include <sys/socket.h>
 #include <sys/un.h>
 #include <sys/stat.h>
 #include <unistd.h>
#endif

namespace
{
constexpr auto configurationFileName = "studioforge-performance-surface.json";

juce::File bridgeDirectory()
{
   #if JUCE_MAC || JUCE_LINUX
    // The companion panel is a separate Python process.  Python's
    // tempfile.gettempdir() may resolve to a per-process /var/folders path,
    // while JUCE can resolve its temporary directory differently.  Publishing
    // the discovery file in /tmp gives both processes one stable local-only
    // rendezvous point; the random token and 0600 permissions still make the
    // active session private to this user.
    return juce::File("/tmp");
   #else
    return juce::File::getSpecialLocation(juce::File::tempDirectory);
   #endif
}

juce::String errorPayload(const juce::String& message)
{
    auto root = juce::var(new juce::DynamicObject());
    root.getDynamicObject()->setProperty("ok", false);
    root.getDynamicObject()->setProperty("error", message);
    return juce::JSON::toString(root, true);
}
}

PerformanceSurfaceBridge::PerformanceSurfaceBridge(TrackDataModel& model, PerformanceMacroService& macroService,
                                                   AudioEngine* engine,
                                                   PitchCorrectionIntegrationService* pitchCorrectionIn)
    : juce::Thread("StudioForge Performance Surface"), dataModel(model), macros(macroService), audioEngine(engine),
      pitchCorrection(pitchCorrectionIn),
      sessionToken(juce::Uuid().toString().replaceCharacters("-", ""))
{
}

PerformanceSurfaceBridge::~PerformanceSurfaceBridge()
{
    stop();
}

juce::File PerformanceSurfaceBridge::getConfigurationFile() const
{
    return bridgeDirectory().getChildFile(configurationFileName);
}

juce::Result PerformanceSurfaceBridge::start()
{
    if (accepting.load(std::memory_order_acquire))
        return juce::Result::ok();

   #if JUCE_MAC || JUCE_LINUX
    // macOS gives applications a long per-user temporary directory under
    // /var/folders.  Adding the random session token to that path can exceed
    // sockaddr_un::sun_path (104 bytes), which makes bind() fail silently from
    // the companion UI's perspective.  Keep the socket itself in /tmp where
    // its path is short; the random token plus owner-only permissions keep it
    // session-private.  The configuration file remains in the per-user temp
    // directory that the companion already reads.
    const auto socketDirectory = juce::File("/tmp");
    socketPath = socketDirectory.getChildFile("studioforge-performance-" + sessionToken + ".socket")
                     .getFullPathName();
    if (socketPath.getNumBytesAsUTF8() >= static_cast<int>(sizeof(sockaddr_un::sun_path)))
        return juce::Result::fail("Performance surface socket path is too long");

    ::unlink(socketPath.toRawUTF8());
    listeningSocket = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (listeningSocket < 0)
        return juce::Result::fail("Cannot create local performance-surface socket");

    sockaddr_un address {};
    address.sun_family = AF_UNIX;
    std::strncpy(address.sun_path, socketPath.toRawUTF8(), sizeof(address.sun_path) - 1);
    if (::bind(listeningSocket, reinterpret_cast<const sockaddr*>(&address), sizeof(address)) != 0
        || ::listen(listeningSocket, 4) != 0)
    {
        const auto error = juce::String(std::strerror(errno));
        ::close(listeningSocket);
        listeningSocket = -1;
        ::unlink(socketPath.toRawUTF8());
        return juce::Result::fail("Cannot listen for Tune-AI: " + error);
    }
    ::chmod(socketPath.toRawUTF8(), S_IRUSR | S_IWUSR);

    // Some packaged/macOS-hosted Python processes are permitted to connect to
    // localhost but are denied AF_UNIX despite running as the same user.  A
    // random, loopback-only port is an authenticated fallback, not a network
    // service: the 0600 discovery file and per-session token gate every call.
    loopbackListeningSocket = ::socket(AF_INET, SOCK_STREAM, 0);
    if (loopbackListeningSocket >= 0)
    {
        sockaddr_in loopbackAddress {};
        loopbackAddress.sin_family = AF_INET;
        loopbackAddress.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        loopbackAddress.sin_port = 0;
        if (::bind(loopbackListeningSocket, reinterpret_cast<const sockaddr*>(&loopbackAddress), sizeof(loopbackAddress)) == 0
            && ::listen(loopbackListeningSocket, 4) == 0)
        {
            socklen_t addressLength = sizeof(loopbackAddress);
            if (::getsockname(loopbackListeningSocket, reinterpret_cast<sockaddr*>(&loopbackAddress), &addressLength) == 0)
                loopbackPort = static_cast<int>(ntohs(loopbackAddress.sin_port));
        }
        if (loopbackPort == 0)
        {
            ::close(loopbackListeningSocket);
            loopbackListeningSocket = -1;
        }
    }
    accepting.store(true, std::memory_order_release);
    if (const auto result = writeConfiguration(); result.failed())
    {
        stop();
        return result;
    }
    startThread(juce::Thread::Priority::normal);
    return juce::Result::ok();
   #else
    return juce::Result::fail("Performance surface transport requires a platform local IPC implementation");
   #endif
}

void PerformanceSurfaceBridge::stop()
{
    accepting.store(false, std::memory_order_release);
   #if JUCE_MAC || JUCE_LINUX
    if (listeningSocket >= 0)
    {
        ::shutdown(listeningSocket, SHUT_RDWR);
        ::close(listeningSocket);
        listeningSocket = -1;
    }
    if (loopbackListeningSocket >= 0)
    {
        ::shutdown(loopbackListeningSocket, SHUT_RDWR);
        ::close(loopbackListeningSocket);
        loopbackListeningSocket = -1;
        loopbackPort = 0;
    }
   #endif
    signalThreadShouldExit();
    stopThread(1000);
   #if JUCE_MAC || JUCE_LINUX
    if (socketPath.isNotEmpty()) ::unlink(socketPath.toRawUTF8());
   #endif
    getConfigurationFile().deleteFile();
}

juce::Result PerformanceSurfaceBridge::writeConfiguration() const
{
    auto root = juce::var(new juce::DynamicObject());
    auto* object = root.getDynamicObject();
    object->setProperty("schema", 1);
    object->setProperty("transport", "unix");
    object->setProperty("socketPath", socketPath);
    if (loopbackPort > 0)
        object->setProperty("loopbackPort", loopbackPort);
    object->setProperty("token", sessionToken);
    const auto file = getConfigurationFile();
    const auto temporary = file.getSiblingFile(file.getFileName() + ".tmp");
    if (! temporary.replaceWithText(juce::JSON::toString(root, false)))
        return juce::Result::fail("Cannot publish performance-surface configuration");
   #if JUCE_MAC || JUCE_LINUX
    ::chmod(temporary.getFullPathName().toRawUTF8(), S_IRUSR | S_IWUSR);
   #endif
    if (file.existsAsFile() ? ! temporary.replaceFileIn(file) : ! temporary.moveFileTo(file))
        return juce::Result::fail("Cannot activate performance-surface configuration");
    return juce::Result::ok();
}

juce::String PerformanceSurfaceBridge::dispatchOnMessageThread(const juce::String& request)
{
    struct PendingRequest
    {
        juce::String request;
        juce::String response;
        juce::WaitableEvent complete;
    };
    auto pending = std::make_shared<PendingRequest>();
    pending->request = request;
    juce::MessageManager::callAsync([this, pending]
    {
        PerformanceSurfaceProtocol protocol(dataModel, macros, sessionToken, audioEngine, pitchCorrection);
        pending->response = protocol.handleCommand(pending->request);
        pending->complete.signal();
    });
    return pending->complete.wait(1500) ? pending->response
                                        : errorPayload("StudioForge did not respond to the control-surface request");
}

void PerformanceSurfaceBridge::run()
{
   #if JUCE_MAC || JUCE_LINUX
    while (! threadShouldExit() && accepting.load(std::memory_order_acquire))
    {
        if (listeningSocket < 0) break;
        fd_set readable;
        FD_ZERO(&readable);
        FD_SET(listeningSocket, &readable);
        auto highestSocket = listeningSocket;
        if (loopbackListeningSocket >= 0)
        {
            FD_SET(loopbackListeningSocket, &readable);
            highestSocket = juce::jmax(highestSocket, loopbackListeningSocket);
        }
        timeval timeout { 0, 200000 };
        if (::select(highestSocket + 1, &readable, nullptr, nullptr, &timeout) <= 0)
            continue;

        const auto server = FD_ISSET(listeningSocket, &readable) ? listeningSocket : loopbackListeningSocket;
        const auto client = server >= 0 ? ::accept(server, nullptr, nullptr) : -1;
        if (client < 0) continue;
        char buffer[65537] {};
        const auto bytes = ::recv(client, buffer, 65536, 0);
        if (bytes > 0)
        {
            auto request = juce::String::fromUTF8(buffer, static_cast<int>(bytes)).upToFirstOccurrenceOf("\n", false, false);
            const auto response = dispatchOnMessageThread(request) + "\n";
            ::send(client, response.toRawUTF8(), static_cast<size_t>(response.getNumBytesAsUTF8()), 0);
        }
        ::shutdown(client, SHUT_RDWR);
        ::close(client);
    }
   #endif
}
