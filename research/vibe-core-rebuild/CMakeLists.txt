cmake_minimum_required(VERSION 3.22)
project(VibeAutotuneRebuild VERSION 1.0.8 LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(VIBE_JUCE_SOURCE_DIR "/Users/hiimdrdey/code/daw/build-macos-arm64/_deps/juce-src" CACHE PATH "Pinned local JUCE used by StudioForge")
add_subdirectory("${VIBE_JUCE_SOURCE_DIR}" JUCE_SDK)
juce_add_plugin(VibeAutotune COMPANY_NAME "VibeAudio" PLUGIN_MANUFACTURER_CODE VbAu PLUGIN_CODE Atun FORMATS VST3 AU PRODUCT_NAME "VibeAutotune" COPY_PLUGIN_AFTER_BUILD FALSE)
juce_add_binary_data(VibeAutotuneUIAssets NAMESPACE VibeAutotuneBinaryData HEADER_NAME VibeAutotuneBinaryData.h SOURCES
    VibeAutotune/Assets/ui_02_black_glass_frame_exact.png
    VibeAutotune/Assets/ui_knob_face_neutral_v1-square.png
    VibeAutotune/Assets/ui_knob_assembly_neutral_v2.png
    VibeAutotune/Assets/ui_champagne_brushed_neutral_v1.png)
target_sources(VibeAutotune PRIVATE VibeAutotune/PluginProcessor.cpp VibeAutotune/FrozenContract.cpp
    VibeAutotune/PluginEditor.cpp VibeAutotune/AnalogHardwareButton.cpp VibeAutotune/AnalogRotaryControl.cpp)
target_compile_definitions(VibeAutotune PUBLIC JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_VST3_CAN_REPLACE_VST2=0)
target_link_libraries(VibeAutotune PRIVATE VibeAutotuneUIAssets juce::juce_audio_utils juce::juce_audio_processors juce::juce_dsp)
juce_generate_juce_header(VibeAutotune)
enable_testing()
add_executable(VibeCoreTests tests/CoreTests.cpp)
target_include_directories(VibeCoreTests PRIVATE VibeAutotune)
add_test(NAME Core COMMAND VibeCoreTests)
add_executable(VibeContractTests tests/ContractTests.cpp)
target_include_directories(VibeContractTests PRIVATE VibeAutotune)
target_link_libraries(VibeContractTests PRIVATE VibeAutotune juce::juce_audio_utils)
add_test(NAME Contract COMMAND VibeContractTests)
add_executable(VibeRenderTrace tools/RenderTrace.cpp)
target_include_directories(VibeRenderTrace PRIVATE VibeAutotune)
target_link_libraries(VibeRenderTrace PRIVATE VibeAutotune juce::juce_audio_utils)

# Same StudioForge audio graph; only enum verification and provenance logging
# are repaired in the local service copy. No DAW app is built or installed.
set(SF_SOURCE "/Users/hiimdrdey/code/daw/Source")
add_executable(StudioForgeReferenceRunner tools/ReferenceRunner.cpp tools/host/StudioForgeCalibrationRunner.cpp)
foreach(source
    Control/LiveBridgeController.cpp Core/Automation/AutomationLane.cpp AudioEngine/AudioEngine.cpp AudioEngine/AudioDiagnosticTracer.cpp
    AudioEngine/CoreAudioInputProbe.cpp AudioEngine/LiveKeyDetector.cpp AudioEngine/AudioGraph.cpp
    Models/TrackDataModel.cpp Project/ProjectSerializer.cpp Project/ProjectTemplates.cpp
    Project/ProjectTemplateStore.cpp Project/ProjectAlternativeStore.cpp Project/ProjectBackupStore.cpp
    Project/RecentProjectsStore.cpp Project/AutosaveService.cpp Media/MediaReloadService.cpp
    Media/AudioMediaPool.cpp Media/WaveformThumbnailCache.cpp Media/Waveform/WaveformCacheStore.cpp
    Recording/RecordingSession.cpp Control/ControlRoutingProfile.cpp Control/PluginSemanticMapper.cpp
    Control/PerformanceMacroService.cpp Control/PerformanceSurfaceProtocol.cpp Control/PerformanceSurfaceBridge.cpp
    Control/StudioForgeControlBridge.cpp Control/VibeAutotuneAdapter.cpp Control/PitchCorrectionIntegrationService.cpp
    Midi/MidiCore.cpp Midi/MidiFileImporter.cpp Midi/MidiTransposeProcessor.cpp Plugins/PluginHostService.cpp)
    target_sources(StudioForgeReferenceRunner PRIVATE "${SF_SOURCE}/${source}")
endforeach()
target_include_directories(StudioForgeReferenceRunner PRIVATE "${SF_SOURCE}")
target_compile_definitions(StudioForgeReferenceRunner PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0
    JUCE_PLUGINHOST_VST3=1 JUCE_PLUGINHOST_AU=1 STUDIOFORGE_DISABLE_AUTOMATIC_PLUGIN_SCAN=1
    STUDIOFORGE_VST3_PROBE_PATH="/Users/hiimdrdey/code/daw/build-macos-arm64/StudioForgeVst3Probe")
target_link_libraries(StudioForgeReferenceRunner PRIVATE juce::juce_audio_utils "-framework CoreAudioKit")
