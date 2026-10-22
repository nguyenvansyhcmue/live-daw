#pragma once

#include <juce_core/juce_core.h>

class RecentProjectsStore final
{
public:
    RecentProjectsStore();
    explicit RecentProjectsStore(juce::File storageFile, juce::File projectsDirectory = {});

    juce::StringArray load() const;
    void add(const juce::File& projectFile) const;
    void clear() const;

    static juce::File defaultStorageFile();
    static juce::File defaultProjectsDirectory();
    juce::File getProjectsDirectory() const { return projectsFolder; }

private:
    bool writeEntries(const juce::StringArray& entries) const;

    juce::File storage;
    juce::File projectsFolder;
    static constexpr int maximumEntries = 12;
};
