#pragma once

#include <vector>

#include <juce_gui_basics/juce_gui_basics.h>

#include "../Models/TrackDataModel.h"
#include "../AudioEngine/AudioEngine.h"
#include "ArrangeWindow.h"
#include "AudioPeakMeter.h"
#include "ControlBar.h"
#include "../Control/LiveBridgeController.h"
#include "MixerPane.h"
#include "PianoRoll.h"
#include "InspectorPane.h"
#include "AssetBrowserPane.h"
#include "StartupWorkflowPane.h"
#include "Theme/StudioForgeLookAndFeel.h"
#include "../Plugins/PluginHostService.h"
#include "../Project/ProjectTemplates.h"
#include "../Services/TuneAiAnalysisService.h"
#include "../Control/StudioForgeControlBridge.h"
#include "../Control/PerformanceMacroService.h"
#include "../Control/PerformanceSurfaceBridge.h"
#include "../Control/PitchCorrectionIntegrationService.h"
#include "../Core/WorkspaceModeController.h"

// A deliberately narrow, always-on-top splitter used between workspace
// panes.  The cursor, hover light and double-click reset make resizing
// discoverable without adding permanent visual noise to the console.
class WorkspacePaneResizeHandle final : public juce::Component
{
public:
    enum class Orientation { vertical, horizontal };

    explicit WorkspacePaneResizeHandle(Orientation handleOrientation)
        : orientation(handleOrientation)
    {
        setAlwaysOnTop(true);
        setMouseCursor(orientation == Orientation::vertical ? juce::MouseCursor::LeftRightResizeCursor
                                                             : juce::MouseCursor::UpDownResizeCursor);
    }

    void paint(juce::Graphics& g) override
    {
        const auto active = hovering || dragging;
        g.setColour((active ? juce::Colour(0xff41bedb) : juce::Colour(0xff59646a))
                        .withAlpha(active ? 0.68f : 0.12f));
        if (orientation == Orientation::vertical)
        {
            g.fillRect(static_cast<float>(getWidth()) * 0.5f - (active ? 1.0f : 0.5f), 0.0f,
                       active ? 2.0f : 1.0f, static_cast<float>(getHeight()));
            if (active)
                for (auto y = 12.0f; y < static_cast<float>(getHeight()); y += 28.0f)
                    g.fillRoundedRectangle(static_cast<float>(getWidth()) * 0.5f - 1.5f, y, 3.0f, 10.0f, 1.5f);
        }
        else
        {
            g.fillRect(0.0f, static_cast<float>(getHeight()) * 0.5f - (active ? 1.0f : 0.5f),
                       static_cast<float>(getWidth()), active ? 2.0f : 1.0f);
        }
    }

    void mouseEnter(const juce::MouseEvent&) override { hovering = true; repaint(); }
    void mouseExit(const juce::MouseEvent&) override { hovering = false; if (! dragging) repaint(); }
    void mouseDown(const juce::MouseEvent&) override { dragging = true; repaint(); }
    void mouseDrag(const juce::MouseEvent& event) override
    {
        if (onDragDelta != nullptr)
            onDragDelta(orientation == Orientation::vertical ? juce::roundToInt(event.getDistanceFromDragStartX())
                                                              : juce::roundToInt(event.getDistanceFromDragStartY()));
    }
    void mouseUp(const juce::MouseEvent&) override { dragging = false; repaint(); }
    void mouseDoubleClick(const juce::MouseEvent&) override { if (onReset != nullptr) onReset(); }

    std::function<void(int)> onDragDelta;
    std::function<void()> onReset;

private:
    Orientation orientation;
    bool hovering = false;
    bool dragging = false;
};

class MainComponent final : public juce::Component, private juce::Timer
{
public:
    MainComponent();
    ~MainComponent() override;

    void paint(juce::Graphics& g) override;
    void resized() override;
    bool keyPressed(const juce::KeyPress& key) override;
    bool handleGlobalKeyPress(const juce::KeyPress& key);

    juce::Result saveProject(const juce::File& file);
    juce::Result saveProjectCopy(const juce::File& file) const;
    juce::Result saveProjectTemplate(const juce::File& file) const;
    juce::Result loadProject(const juce::File& file, juce::StringArray* missingMediaReferences = nullptr);
    juce::Result createNewProject();
    juce::Result createProjectFromTemplate(ProjectTemplate projectTemplate);
    bool isProjectDirty() const noexcept;
    void markProjectSaved() noexcept;
    void markProjectRecovered() noexcept;
    bool undoEdit();
    bool redoEdit();
    void requestRecordToggle();
    void setInspectorPanelVisible(bool visible);
    void setBrowserPanelVisible(bool visible);
    void setMixerPanelVisible(bool visible);
    bool addTrackFromCommand(TrackType type = TrackType::audio);
    void importAudioFile(const juce::File& file);
    juce::Result importMidiFile(const juce::File& file);
    void requestProjectBounce();
    void requestProjectExport();
    void requestStemExport();
    void requestSelectedTrackExport();
    void requestMidiExport();
    void requestTuneAiUrlAnalysis();
    void setWorkspaceTrackHeight(int height);
    // Deterministic support entry point. It is deliberately invoked only by
    // the explicit command-line switch, never by ordinary launch.
    void startAutomatedVibeTrace();

    bool isInspectorPanelVisible() const noexcept { return panelLayout.inspector; }
    bool isBrowserPanelVisible() const noexcept { return panelLayout.browser; }
    bool isMixerPanelVisible() const noexcept { return panelLayout.mixer; }
    bool isStartupWorkflowVisible() const noexcept { return startupWorkflow.isVisible(); }
    void showWorkspace() noexcept { startupWorkflow.setVisible(false); resized(); }
    void showInitialTrackCreation();
    void setRecentProjects(juce::StringArray paths) { startupWorkflow.setRecentProjects(std::move(paths)); }
    void setRevealProjectsFolderHandler(std::function<void()> handler)
    {
        startupWorkflow.onRevealProjectsFolder = std::move(handler);
    }
    void setProjectHistoryRefreshHandler(std::function<void()> handler)
    {
        startupWorkflow.onHistoryRefreshRequested = std::move(handler);
    }
    std::function<void()> onOpenProjectRequested;
    std::function<void(const juce::File&)> onOpenRecentProjectRequested;
    std::function<void()> onAudioDeviceSettingsRequested;

    TrackDataModel& getTrackDataModel() noexcept { return trackDataModel; }
    AudioEngine& getAudioEngine() noexcept { return audioEngine; }
    LiveBridgeController& getLiveBridgeController() noexcept { return liveBridgeController; }
    PerformanceMacroService& getPerformanceMacros() noexcept { return performanceMacros; }

private:
    void selectTrack(int trackIndex);
    void applyWorkspaceMode(const WorkspaceProfile& profile);
    int getSelectedTrackIndex() const noexcept;
    void configureTrackCreationDialog();
    void enableAvailablePerformanceInputs();
    void repairAudioTrackInputAssignments();
    void selectAudioInputChannel(int oneBasedChannel);
    void selectAudioOutputChannel(int oneBasedChannel);
    void handleSpaceTransport();
    void toggleRecording();
    void startRecordingNow(int trackIndex, const juce::File& destination,
                           double timelineStartSample = -1.0);
    void startAudioRecordingsNow(const std::vector<AudioEngine::AudioRecordingTarget>& targets,
                                 double timelineStartSample = -1.0);
    void showRecordingFailure(const juce::Result& result) const;
    juce::String applyTuneAiKey(const MusicalKey&, bool mic1, bool mic2);
    void consumeTuneAiKeyBridge();
    void beginBeatKeyLearning(int trackIndex);
    void requestWorkspaceMode(WorkspaceMode mode);
    struct PanelLayoutState
    {
        bool inspector = false;
        bool browser = false;
        bool mixer = false;
        bool pianoRoll = false;
    };
    void applyPanelLayout(PanelLayoutState next, bool updateStudioSnapshot);
    void setWorkspacePanelsVisible(bool inspector, bool browser, bool mixer, bool pianoRoll);
    void setPianoRollPanelVisible(bool visible);
    void timerCallback() override;
    void refreshLiveBridgeUi();
    juce::File createRecordingDestination() const;
    void requestOfflineRender(const juce::String& chooserTitle, const juce::String& errorTitle);

    StudioForgeLookAndFeel lookAndFeel;
    TrackDataModel trackDataModel;
    AudioEngine audioEngine { &trackDataModel };
    NativeLiveBridgeEndpointProvider liveBridgeEndpointProvider;
    AudioEngineLiveBridgeOutputPort liveBridgeOutputPort { audioEngine };
    LiveBridgeController liveBridgeController { liveBridgeEndpointProvider, liveBridgeOutputPort };
    StudioForgeControlBridge controlBridge { trackDataModel };
    PluginHostService pluginHost;
    PitchCorrectionIntegrationService pitchCorrection { trackDataModel, pluginHost, controlBridge };
    PerformanceMacroService performanceMacros { trackDataModel, &audioEngine };
    PerformanceSurfaceBridge performanceSurfaceBridge { trackDataModel, performanceMacros, &audioEngine,
                                                         &pitchCorrection };
    TuneAiAnalysisService tuneAiAnalysis;
    ControlBar controlBar { &trackDataModel, &audioEngine };
    ArrangeWindow arrangeWindow { &trackDataModel, &audioEngine };
    InspectorPane inspectorPane { trackDataModel, audioEngine, pluginHost };
    AssetBrowserPane assetBrowser;
    MixerPane mixerPane { &trackDataModel, &audioEngine, &pluginHost };
    PianoRoll pianoRoll { &trackDataModel };
    StartupWorkflowPane startupWorkflow;
    WorkspacePaneResizeHandle inspectorResizeHandle { WorkspacePaneResizeHandle::Orientation::vertical };
    WorkspacePaneResizeHandle browserResizeHandle { WorkspacePaneResizeHandle::Orientation::vertical };
    std::unique_ptr<juce::FileChooser> bounceFileChooser;
    uint64_t savedProjectRevision = 0;
    bool recoveredProjectNeedsSave = false;
    bool countInEnabled = false;
    int countInBars = 1;
    bool recordingCountdownActive = false;
    // A startup choice is a track-source preference, never an instruction to
    // disable the remaining physical inputs of the Core Audio device.
    int preferredStartupInputChannel = 0;
    int pendingRecordingTrack = -1;
    double pendingRecordingStartSample = 0.0;
    double pendingRecordingTimelineStartSample = 0.0;
    bool rewindCountInAtCompletion = false;
    juce::File pendingRecordingDestination;
    std::vector<AudioEngine::AudioRecordingTarget> pendingAudioRecordingTargets;
    double recordingPunchStopSample = -1.0;
    TrackId selectedTrackId;
    enum class AutoKeyState : uint8_t { idle, learning, locked };
    AutoKeyState autoKeyState = AutoKeyState::idle;
    uint64_t appliedLiveKeyRevision = 0;
    double consumedTuneAiKeyPublishedAt = 0.0;
    PitchCorrectionIntegrationService::Status pitchCorrectionStatus;
    int pitchCorrectionSetupTicks = 0;
    int midiDeviceRefreshTicks = 0;
    WorkspaceMode workspaceMode = WorkspaceMode::studio;
    std::unique_ptr<WorkspaceModeController> workspaceModeController;
    // This is the single source of truth for dock visibility. Components are
    // projections of this value; reading their incidental visible flags while
    // workspace transitions are in progress caused stale View-menu ticks.
    PanelLayoutState panelLayout { true, false, false, false };
    PanelLayoutState studioPanelLayout { true, false, false, false };
    bool suppressWorkspaceModeCallback = false;
    bool automatedVibeTraceStarted = false;
    int studioTrackHeight = 72;
    int inspectorWidth = 280;
    int browserWidth = 250;
};
