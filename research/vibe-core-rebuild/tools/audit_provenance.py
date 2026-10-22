"""Record evidence for THIS non-installed build. Does not promote anything."""
import hashlib
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
origin=Path('/Users/hiimdrdey/code/daw/autotune/VibeAutotune')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
frozen=['PluginEditor.cpp','PluginEditor.h','AnalogHardwareButton.cpp',
        'AnalogHardwareButton.h','AnalogRotaryControl.cpp','AnalogRotaryControl.h','NotePolicy.h']
for name in frozen:
    assert sha(root/'VibeAutotune'/name)==sha(origin/name), f'Frozen file mismatch: {name}'
for p in (root/'VibeAutotune/Assets').glob('*'):
    if p.is_file():assert sha(p)==sha(origin/'Assets'/p.name),f'Asset mismatch: {p.name}'
subprocess.run(['python3',str(root/'tools/import_frozen_contract.py'),'--check'],check=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(root/'build/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3')],check=True)
assert sha(root/'results/final-host/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav')==sha(root/'results/v2-host/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav')
assert sha(root/'results/final-trace/vibe.wav')==sha(root/'results/v1-notrace/vibe.wav')
forbidden=['CausalTDPSOLARenderer','SignalsmithPitchRenderer','BufferedSpectralPitchRenderer',
           'EventOwnedSpectralFrameQueue','LiveControlPipeline','PitchDecomposer']
for p in (root/'VibeAutotune').glob('*'):
    if p.suffix in ['.cpp','.h']:
        for token in forbidden:assert token not in p.read_text(),f'Legacy reference {token}: {p}'
sources={str(p.relative_to(root)):sha(p) for directory in ['VibeAutotune','tests','tools']
         for p in (root/directory).rglob('*') if p.is_file() and p.suffix in ['.cpp','.h','.py','.png']}
sources['CMakeLists.txt']=sha(root/'CMakeLists.txt')
products={str(p.relative_to(root)):sha(p) for p in [
    root/'build/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3/Contents/MacOS/VibeAutotune',
    root/'build/VibeAutotune_artefacts/Release/AU/VibeAutotune.component/Contents/MacOS/VibeAutotune',
    root/'build/StudioForgeReferenceRunner']}
record={'status':'NOT PROMOTED / canonical source not writable', 'frozen_ui_and_policy':'verified',
        'final_host_audio':'identical to measured v2', 'final_trace_audio':'identical to trace-disabled baseline',
        'sources_sha256':sources,'products_sha256':products,
        'host_source_sha256':{str(p):sha(p) for p in Path('/Users/hiimdrdey/code/daw/Source').rglob('*')
                              if p.is_file() and p.suffix in ['.cpp','.h','.mm']}}
(root/'results/provenance.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS: frozen UI/policy; no legacy renderer references; exact final host/trace audio; hashes recorded. NOT installed.')
