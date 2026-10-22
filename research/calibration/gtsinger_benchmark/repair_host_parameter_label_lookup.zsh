#!/bin/zsh
# Restore deterministic display-name lookup for hosted plug-in parameters.
# Needed by the offline runner and by host automation adapters that address
# parameters using their user-visible names rather than vendor IDs.
set -euo pipefail

daw_root="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
host_source="$daw_root/Source/Plugins/PluginHostService.cpp"
native_source="$daw_root/Source/Plugins/NativeVibeAutotuneProcessor.cpp"
build="${STUDIOFORGE_CALIBRATION_BUILD:-$daw_root/build-macos-arm64}"

[[ -f "$host_source" && -f "$native_source" ]] || {
  print -u2 'Missing PluginHostService.cpp or NativeVibeAutotuneProcessor.cpp.'; exit 66
}

python3 - "$host_source" "$native_source" <<'PY'
from pathlib import Path
import sys

marker = 'STUDIOFORGE_PARAMETER_DISPLAY_NAME_LOOKUP'

def patch(path: Path) -> bool:
    text = path.read_text()
    if marker in text:
        print(f'Already applied: {path.name}')
        return False
    needle = '''        for (auto* parameter : instance->getParameters())
        {
            if (const auto* withId = dynamic_cast<const juce::AudioProcessorParameterWithID*>(parameter); withId != nullptr)
                if (withId->getParameterID() == identifier)
                    return parameter;
        }
        return nullptr;
'''
    if 'NativeVibeAutotuneProcessor' in path.name:
        needle = '''    for (auto* parameter : processor->getParameters())
    {
        if (const auto* identified = dynamic_cast<const juce::AudioProcessorParameterWithID*>(parameter); identified != nullptr)
            if (identified->getParameterID() == identifier)
                return parameter;
    }
    return nullptr;
'''
        replacement = '''    for (auto* parameter : processor->getParameters())
    {
        if (const auto* identified = dynamic_cast<const juce::AudioProcessorParameterWithID*>(parameter); identified != nullptr)
            if (identified->getParameterID() == identifier)
                return parameter;
        // STUDIOFORGE_PARAMETER_DISPLAY_NAME_LOOKUP
        // Automation and offline rendering may address a parameter by its
        // public label. IDs remain preferred; this is an exact fallback.
        if (parameter != nullptr && parameter->getName(128).equalsIgnoreCase(identifier))
            return parameter;
    }
    return nullptr;
'''
    else:
        replacement = '''        for (auto* parameter : instance->getParameters())
        {
            if (const auto* withId = dynamic_cast<const juce::AudioProcessorParameterWithID*>(parameter); withId != nullptr)
                if (withId->getParameterID() == identifier)
                    return parameter;
            // STUDIOFORGE_PARAMETER_DISPLAY_NAME_LOOKUP
            // Automation and offline rendering may address a parameter by its
            // public label. IDs remain preferred; this is an exact fallback.
            if (parameter != nullptr && parameter->getName(128).equalsIgnoreCase(identifier))
                return parameter;
        }
        return nullptr;
'''
    if needle not in text:
        raise SystemExit(f'Anchor changed in {path}; no files were modified.')
    path.write_text(text.replace(needle, replacement))
    print(f'Applied display-name fallback: {path.name}')
    return True

changed = any(patch(Path(item)) for item in sys.argv[1:])
if not changed:
    print('Display-name lookup already present.')
PY

cmake --build "$build" --target StudioForgeCalibrationRunner --parallel 4
print 'PASS: calibration runner rebuilt with ID-first, display-name fallback lookup.'
