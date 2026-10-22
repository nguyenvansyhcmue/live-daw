"""Mechanical copy of StudioForge calibration service, with sharp-safe labels.
The canonical DAW source is read-only in this session; this build uses its
unchanged AudioEngine, PluginHostService and model implementation directly.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=Path('/Users/hiimdrdey/code/daw/Source/Services/StudioForgeCalibrationRunner.cpp').read_text()
source=source.replace('#include "StudioForgeCalibrationRunner.h"','#include "Services/StudioForgeCalibrationRunner.h"')
source=source.replace('#include "../','#include "')
anchor='if (juce::CharacterFunctions::isLetterOrDigit(character)) result += character;'
assert source.count(anchor)==1
source=source.replace(anchor,'if (juce::CharacterFunctions::isLetterOrDigit(character) || character == \'#\') result += character;')
anchor='    // AU instances do not reliably inherit the runner environment.'
assert source.count(anchor)==1
source=source.replace(anchor,'''    std::cerr << "VERIFIED_SETTINGS voice=" << effect.getParameterText("Input Type")
              << " key=" << effect.getParameterText("Key")
              << " scale=" << effect.getParameterText("Scale")
              << " retune=" << effect.getParameterText("Retune Speed") << '\\n';

'''+anchor)
dest=root/'tools/host/StudioForgeCalibrationRunner.cpp'
dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(source)
print(dest)
