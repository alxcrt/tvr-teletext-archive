#!/usr/bin/env python3
"""Optional independent validation using a separately installed vhs-teletext tree.

Run with that project's supported NumPy <2 dependency. Its source is not bundled.
"""
import argparse
import json
from pathlib import Path
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--upstream',type=Path,required=True)
parser.add_argument('--archive',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
sys.path.insert(0,str(args.upstream.resolve()))
import numpy as np
from teletext.packet import Packet
from teletext.subpage import Subpage
import subprocess

revision=subprocess.check_output(['git','-C',str(args.upstream),'rev-parse','HEAD'],text=True).strip()
results=[]
for metadata in sorted(args.archive.glob('*/metadata.json')):
    data=json.loads(metadata.read_text())
    for key,versions in data['pages'].items():
        for v in versions.values():
            raw=(metadata.parent/v['file']).read_bytes()
            packets=[Packet(np.frombuffer(raw[i:i+42],dtype=np.uint8).copy(),number=i//42) for i in range(0,len(raw),42)]
            page=Subpage.from_packets(packets)
            assert page.addr.lower().replace(':','-')==key, (page.addr,key)
            checksum=int(page.checksum)
            assert checksum==v['calculated_crc'] or v['calculated_crc'] is None, (key,checksum,v['calculated_crc'])
            results.append(dict(recording=data['archive_id'],page=key,file=v['file'],
                independent_calculated_crc=checksum,expected_crc=v['expected_crc'],
                matches_broadcast_crc=None if v['expected_crc'] is None else checksum==v['expected_crc']))
report=dict(tool='ali1234/vhs-teletext',revision=revision,numpy_version=np.__version__,
            checked_files=len(results),crc_present=sum(r['expected_crc'] is not None for r in results),
            crc_matches=sum(r['matches_broadcast_crc'] is True for r in results),
            all_index_and_crc_calculations_agree=True,results=results)
args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))
