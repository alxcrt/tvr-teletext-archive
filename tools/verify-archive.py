#!/usr/bin/env python3
"""Verify the published hashes, byte-exact page selections and TS extraction."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import struct

root=Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[1]).resolve()
def safe(path):
    result=(root/path).resolve()
    if not result.is_relative_to(root):raise ValueError('Path escapes archive: '+str(path))
    return result
checked=0
for line in (root/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split('  ',1);path=safe(name)
    with path.open('rb') as handle:actual=hashlib.file_digest(handle,'sha256').hexdigest()
    if actual!=expected:raise ValueError('Hash mismatch: '+name)
    checked+=1
spec=importlib.util.spec_from_file_location('extract',root/'tools/extract-dvb-teletext.py')
extract=importlib.util.module_from_spec(spec);spec.loader.exec_module(extract)
recordings=pages=0
for metadata in sorted((root/'recordings').glob('*/metadata.json')):
    data=json.loads(metadata.read_text());folder=metadata.parent
    raw=(folder/(data['archive_id']+'.t42')).read_bytes()
    assert len(raw)==data['bytes'] and len(raw)%42==0
    for versions in data['pages'].values():
        for version in versions.values():
            original=b''.join(raw[i*42:(i+1)*42] for i in version['packet_indices'])
            assert original==(folder/version['file']).read_bytes(),version['file'];pages+=1
    if (folder/'broadcast.ts').exists():
        output=io.BytesIO()
        with (folder/'broadcast.ts').open('rb') as source:report=extract.extract(source,output,117)
        assert output.getvalue()==raw,(data['archive_id'],'TS extraction differs')
        if 'source_index' in data:
            index=(folder/data['source_index']['file']).read_bytes()
            assert len(index)%8==0 and len(index)//8==(folder/'broadcast.ts').stat().st_size//188
            positions=[n[0] for n in struct.iter_unpack('<Q',index)]
            assert all(a<b for a,b in zip(positions,positions[1:])),data['archive_id']
    recordings+=1
print(json.dumps(dict(files_verified=checked,recordings=recordings,original_page_selections=pages,all_checks_passed=True),indent=2))
