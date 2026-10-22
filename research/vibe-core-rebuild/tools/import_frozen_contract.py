"""One-shot mechanical extraction of ONLY the frozen public/musical contract.

No detector, trajectory, renderer or diagnostic experiment is imported.
Run --check later to prove the imported functions still match their origin.
"""
from pathlib import Path
import hashlib
import json
import sys

root = Path(__file__).resolve().parents[1]
origin = Path('/Users/hiimdrdey/code/daw/autotune/VibeAutotune')
source = (origin / 'PluginProcessor.cpp').read_text()

def block(text, start):
    begin = text.index(start)
    opening = text.index('{', begin)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[begin:end]

table = source[source.index('constexpr std::array<std::array<bool, 12>, 14>'):source.index('\nVibeAutotuneProcessor::VibeAutotuneProcessor()')]
names = ['createParameterLayout', 'isBusesLayoutSupported', 'scaleContainsPitchClass',
         'resetNotePolicyToScale', 'synchroniseNotePolicyToScale', 'makeNotePolicySnapshot',
         'getLatestDetectedNoteName', 'getLatestDetectedMidiNote', 'getLatestTargetMidiNote',
         'getEnabledNoteMask', 'setEnabledNoteMask', 'getBaseScaleMask', 'hasCustomNotePolicy',
         'getNoteRuleForPitchClass', 'getNoteRuleForMidiNote', 'setNoteRuleForPitchClass',
         'setNoteRuleForMidiNote', 'resetNoteRuleForPitchClass', 'resetNoteRuleForMidiNote',
         'resetNotePolicyToCurrentScale', 'getGroupOctaves', 'setGroupOctaves',
         'getBypassParameter', 'getStateInformation', 'setStateInformation',
         'noteNameForMidi', 'calculateInputPitchDisplay', 'setMidiTargetNoteFromUi',
         'getMidiTargetNote', 'createEditor']
functions = []
for name in names:
    position = source.index('VibeAutotuneProcessor::' + name + ' (') if ('VibeAutotuneProcessor::' + name + ' (') in source else source.index('VibeAutotuneProcessor::' + name + '(')
    start = source.rfind('\n', 0, position) + 1
    functions.append(block(source, source[start:source.index('{', position)]))
generated = '#include "PluginProcessor.h"\n#include "PluginEditor.h"\nnamespace {\n' + table + '\n\n' + '\n\n'.join(functions) + '\n'
trajectory = (origin / 'CorrectionTrajectory.h').read_text()
methods = [block(trajectory, '    static int ' + name) for name in ['nearestLegalNote', 'directedLegalNote', 'adjacentLegalNote', 'selectPolicyTarget']]
policy = '#pragma once\n#include "NotePolicy.h"\n#include <cmath>\n#include <limits>\nstruct MusicalPolicy {\n' + '\n'.join(methods) + '\n};\n'
outputs = {'VibeAutotune/FrozenContract.cpp': generated, 'VibeAutotune/MusicalPolicy.h': policy}
for name, content in outputs.items():
    path = root / name
    if '--check' in sys.argv:
        assert path.read_text() == content, 'Frozen contract changed: ' + name
    else:
        assert not path.exists(), 'Refusing to overwrite: ' + name
        path.write_text(content)
print('PASS: frozen Key/Scale/Note Map, parameter declarations, preset and UI contract')
