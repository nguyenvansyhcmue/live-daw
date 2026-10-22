#!/bin/zsh
# Upgrade the offline calibration runner from a Hook-2-only fixed profile.
set -euo pipefail

daw_root="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
source="$daw_root/Source/Services/StudioForgeCalibrationRunner.cpp"
build="${STUDIOFORGE_CALIBRATION_BUILD:-$daw_root/build-macos-arm64}"
[[ -f "$source" ]] || { print -u2 "Missing calibration runner: $source"; exit 66; }

python3 - "$source" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
marker = 'STUDIOFORGE_CALIBRATION_KEY_AWARE_PROFILE'
normalization_marker = 'STUDIOFORGE_CALIBRATION_ENUM_NORMALIZATION'
if marker in text:
    if normalization_marker in text:
        print('Key-aware calibration profile and enum normalization already applied.')
        raise SystemExit(0)
    old_matches = '''    const auto matches = [] (const juce::String& actual, const juce::String& candidate)
    {
        if (actual.trim().equalsIgnoreCase(candidate.trim())) return true;
        return (candidate.equalsIgnoreCase("Alto") || candidate.equalsIgnoreCase("Minor"))
            && actual.containsIgnoreCase(candidate);
    };
'''
    new_matches = '''    // STUDIOFORGE_CALIBRATION_ENUM_NORMALIZATION
    // Host enum labels can differ only in punctuation: Artist uses
    // "Alto-Tenor" while another host may display "Alto/Tenor". Compare
    // canonical alphanumeric labels after setting/probing, never by index.
    const auto enumLabel = [] (juce::String text)
    {
        text = text.trim().toLowerCase();
        juce::String result;
        for (auto character : text)
            if (juce::CharacterFunctions::isLetterOrDigit(character)) result += character;
        return result;
    };
    const auto matches = [&enumLabel] (const juce::String& actual, const juce::String& candidate)
    {
        const auto normalizedActual = enumLabel(actual);
        const auto normalizedCandidate = enumLabel(candidate);
        if (normalizedActual == normalizedCandidate) return true;
        return (normalizedCandidate == "alto" || normalizedCandidate == "minor")
            && normalizedActual.contains(normalizedCandidate);
    };
'''
    if old_matches not in text:
        raise SystemExit('Runner enum matcher anchor changed; no files were modified. Inspect StudioForgeCalibrationRunner.cpp before retrying.')
    path.write_text(text.replace(old_matches, new_matches))
    print('Applied calibration enum-label normalization.')
    raise SystemExit(0)

old = '''    if (effect.getName().containsIgnoreCase("Auto-Tune Artist"))
    {
        // Artist's enums do not parse display strings. These normalized
        // indices are the fixed Alto / F# / Natural Minor reference preset.
        if (! effect.setParameterValue("Input Type", 1.0f / 4.0f)
            || ! effect.setParameterValue("Key", 6.0f / 11.0f)
            || ! effect.setParameterValue("Scale", 1.0f / 27.0f))
            return juce::Result::fail("Auto-Tune Artist does not expose its expected key controls");
    }
    else if (! textValue({ "Input Type", "Voice", "inputType" }, "Alto")
             || ! textValue({ "Key", "key" }, "F#")
             || ! textValue({ "Scale", "scale" }, "Natural Minor"))
    {
        return juce::Result::fail("VibeAutotune could not lock Alto / F# / Natural Minor");
    }
'''

new = '''    // STUDIOFORGE_CALIBRATION_KEY_AWARE_PROFILE
    // Resolve enum labels from the hosted plug-in during offline setup. Artist
    // can reject text enum setters, so its finite normalised domain is probed
    // and every result is verified through the displayed parameter text.
    const auto environmentOr = [] (const char* name, const char* fallback)
    {
        if (const auto* value = std::getenv(name); value != nullptr && *value != '\\0')
            return juce::String(value);
        return juce::String(fallback);
    };
    const auto voice = environmentOr("STUDIOFORGE_CALIBRATION_VOICE", "Alto");
    const auto key = environmentOr("STUDIOFORGE_CALIBRATION_KEY", "F#");
    const auto scale = environmentOr("STUDIOFORGE_CALIBRATION_SCALE", "Natural Minor");
    const auto matches = [] (const juce::String& actual, const juce::String& candidate)
    {
        if (actual.trim().equalsIgnoreCase(candidate.trim())) return true;
        return (candidate.equalsIgnoreCase("Alto") || candidate.equalsIgnoreCase("Minor"))
            && actual.containsIgnoreCase(candidate);
    };
    const auto enumValue = [&effect, &matches] (std::initializer_list<const char*> names,
                                                 std::initializer_list<juce::String> candidates)
    {
        for (const auto* name : names)
        {
            for (const auto& candidate : candidates)
                if (effect.setParameterText(name, candidate) && matches(effect.getParameterText(name), candidate))
                    return true;
            // Runs before offline rendering, never on an audio callback.
            for (int step = 0; step <= 1024; ++step)
            {
                if (! effect.setParameterValue(name, static_cast<float>(step) / 1024.0f)) break;
                const auto observed = effect.getParameterText(name);
                for (const auto& candidate : candidates)
                    if (matches(observed, candidate)) return true;
            }
        }
        return false;
    };
    const auto scaleWasSet = scale.equalsIgnoreCase("Natural Minor")
        ? enumValue({ "Scale", "scale" }, { "Natural Minor", "Minor" })
        : enumValue({ "Scale", "scale" }, { scale });
    if (! enumValue({ "Input Type", "Voice", "inputType" }, { voice })
        || ! enumValue({ "Key", "key" }, { key })
        || ! scaleWasSet)
        return juce::Result::fail("Plug-in cannot lock requested Voice/Key/Scale: " + voice + " / " + key + " / " + scale);
'''

if old not in text:
    raise SystemExit('Runner source anchor changed; no files were modified. Inspect StudioForgeCalibrationRunner.cpp before retrying.')
backup = path.with_suffix(path.suffix + '.pre-gtsinger-key-aware')
if not backup.exists(): backup.write_text(text)
path.write_text(text.replace(old, new))
print(f'Applied key-aware setup profile. Backup: {backup}')
PY

cmake --build "$build" --target StudioForgeCalibrationRunner --parallel 4
print 'PASS: runner accepts STUDIOFORGE_CALIBRATION_VOICE/KEY/SCALE per clip.'
