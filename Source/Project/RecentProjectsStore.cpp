#include "RecentProjectsStore.h"

#include <algorithm>

RecentProjectsStore::RecentProjectsStore()
    : storage(defaultStorageFile()), projectsFolder(defaultProjectsDirectory()) {}

RecentProjectsStore::RecentProjectsStore(juce::File storageFile, juce::File projectsDirectory)
    : storage(std::move(storageFile)), projectsFolder(std::move(projectsDirectory)) {}

juce::File RecentProjectsStore::defaultStorageFile()
{
    return juce::File::getSpecialLocation(juce::File::userApplicationDataDirectory)
        .getChildFile("StudioForge").getChildFile("recent-projects.txt");
}

juce::File RecentProjectsStore::defaultProjectsDirectory()
{
    return juce::File::getSpecialLocation(juce::File::userDocumentsDirectory)
        .getChildFile("StudioForge Projects");
}

juce::StringArray RecentProjectsStore::load() const
{
    juce::StringArray entries;
    if (storage.existsAsFile())
        for (const auto& line : juce::StringArray::fromLines(storage.loadFileAsString()))
        {
            const auto path = line.trim();
            const auto file = juce::File(path);
            if (path.isNotEmpty() && file.existsAsFile() && file.hasFileExtension("studioforge")
                && ! entries.contains(path, true))
                entries.add(path);
            if (entries.size() == maximumEntries) break;
        }

    // History is backed by the standard project folder as well as the MRU
    // list. A project remains discoverable after preferences are reset or the
    // recent-projects file is lost.
    if (entries.size() < maximumEntries && projectsFolder.isDirectory())
    {
        juce::Array<juce::File> discovered;
        projectsFolder.findChildFiles(discovered, juce::File::findFiles, false, "*.studioforge");
        std::sort(discovered.begin(), discovered.end(), [] (const juce::File& left, const juce::File& right)
        {
            return left.getLastModificationTime() > right.getLastModificationTime();
        });
        for (const auto& file : discovered)
        {
            const auto path = file.getFullPathName();
            if (! entries.contains(path, true)) entries.add(path);
            if (entries.size() == maximumEntries) break;
        }
    }
    return entries;
}

void RecentProjectsStore::add(const juce::File& projectFile) const
{
    if (! projectFile.existsAsFile() || ! projectFile.hasFileExtension("studioforge")) return;
    auto entries = load();
    entries.removeString(projectFile.getFullPathName(), true);
    entries.insert(0, projectFile.getFullPathName());
    while (entries.size() > maximumEntries) entries.remove(entries.size() - 1);
    writeEntries(entries);
}

void RecentProjectsStore::clear() const
{
    writeEntries({});
}

bool RecentProjectsStore::writeEntries(const juce::StringArray& entries) const
{
    const auto directory = storage.getParentDirectory();
    if (! directory.exists() && ! directory.createDirectory())
        return false;

    const auto temporary = storage.getSiblingFile(storage.getFileName() + ".tmp");
    temporary.deleteFile();
    if (! temporary.replaceWithText(entries.joinIntoString("\n")))
    {
        temporary.deleteFile();
        return false;
    }

    const auto committed = storage.existsAsFile() ? temporary.replaceFileIn(storage)
                                                  : temporary.moveFileTo(storage);
    if (! committed)
        temporary.deleteFile();
    return committed;
}
