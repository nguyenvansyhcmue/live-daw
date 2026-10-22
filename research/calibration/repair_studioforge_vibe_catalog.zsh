#!/bin/zsh
# Remove only stale VibeAutotune entries from StudioForge's plug-in catalog.
# On next launch the host scans the VST3 shipped in its current app bundle.
set -euo pipefail

CATALOG="$HOME/Library/StudioForge/PluginCatalog.xml"
STAMP=$(date +%Y%m%d-%H%M%S)

[[ -f "$CATALOG" ]] || { print 'No StudioForge plug-in catalog exists yet; nothing to repair.'; exit 0; }

BACKUP="${CATALOG}.before-current-vibe-$STAMP"
cp -p "$CATALOG" "$BACKUP"

python3 - "$CATALOG" <<'PY'
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
tree = ET.parse(path)
root = tree.getroot()
removed = 0
# KnownPluginList XML is normally flat, but older StudioForge releases wrote
# nested containers.  Remove matching children from every parent, not only the
# document root, otherwise stale Vibe entries survive and retain the same UID.
for parent in root.iter():
    for element in list(parent):
        name = ''.join(ch for ch in element.attrib.get('name', '').lower() if ch.isalnum())
        if name == 'vibeautotune':
            parent.remove(element)
            removed += 1
tree.write(path, encoding='UTF-8', xml_declaration=True)
print(f'Removed {removed} stale VibeAutotune catalog entry(s).')
PY

print "Catalog backup retained: $BACKUP"
print 'Next StudioForge launch will discover the bundled current VST3.'
