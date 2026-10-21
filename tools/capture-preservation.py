#!/usr/bin/env python3
"""Bounded Linux DVB recording: retain teletext, service tables and source indices.

No persistent configuration changes. Requires dvbv5-zap and existing tuner access.
The received selected TS packets are unchanged; video/audio/PCR streams are omitted.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time


def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channels', type=Path, required=True)
    parser.add_argument('--service', default='TVR 1')
    parser.add_argument('--pid', type=int, default=117)
    parser.add_argument('--adapter', type=int, default=0)
    parser.add_argument('--seconds', type=int, default=900)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600 or not 0 <= args.pid < 8191:
        parser.error('Use 1–3600 seconds and a valid PID')
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    argv = ['dvbv5-zap', '-a', str(args.adapter), '-c', str(args.channels), '-C', 'RO',
            '-P', '-r', '-o', '-', '-t', str(args.seconds), args.service]
    receipt = dict(status='running', started_utc=utc(), requested_seconds=args.seconds,
                   service=args.service, teletext_pid=args.pid,
                   selected_pids=[0,16,17,20,args.pid],
                   notes=['Teletext plus PAT/NIT/SDT/TDT/TOT and PAT-discovered PMT packets.',
                          'Audio/video and their PCR streams omitted; not a playable TV multiplex.',
                          'Source index sidecar is unsigned 64-bit little-endian, zero-based TS packet indices.',
                          'No source timing is synthesized. Filtered TS preserves original PES timestamps.'])
    receipt_path = args.output/'receipt.json'
    receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt), flush=True)
    selected = set(receipt['selected_pids']); count = saved = sync_errors = 0
    source_hash = hashlib.sha256(); output_hash = hashlib.sha256()
    started = time.monotonic(); buffer = b''
    with (args.output/'capture.log').open('wb') as log, \
         (args.output/'broadcast.ts').open('xb') as output, \
         (args.output/'source-ts-index.u64le').open('xb') as indices:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=log)
        try:
            while True:
                block = process.stdout.read(188*1024)
                if not block:
                    break
                source_hash.update(block); buffer += block
                boundary = len(buffer)//188*188
                for offset in range(0, boundary, 188):
                    p = buffer[offset:offset+188]
                    if p[0] != 0x47:
                        sync_errors += 1
                        raise ValueError('Lost aligned MPEG-TS framing')
                    pid = ((p[1]&31)<<8)|p[2]
                    # PAT sections here are small; only use complete sections.
                    if pid == 0 and p[1]&64 and not p[1]&128:
                        afc = (p[3]>>4)&3; start = 4
                        if afc&2: start = 5+p[4]
                        if afc&1 and start < 187:
                            start += 1+p[start]
                            if start+8 < 188 and p[start] == 0:
                                end = start+3+((p[start+1]&15)<<8|p[start+2])-4
                                if end <= 188:
                                    for i in range(start+8, end, 4):
                                        if i+4 <= end and p[i:i+2] != b'\0\0':
                                            selected.add(((p[i+2]&31)<<8)|p[i+3])
                    if pid in selected:
                        output.write(p); output_hash.update(p)
                        indices.write(struct.pack('<Q', count)); saved += 1
                    count += 1
                buffer = buffer[boundary:]
                if time.monotonic()-started > args.seconds+30:
                    raise TimeoutError('Capture exceeded its outer time budget')
            exit_code = process.wait(timeout=15)
        except BaseException:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            receipt.update(status='interrupted', ended_utc=utc(), source_packets=count,
                           saved_packets=saved, selected_pids=sorted(selected))
            receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
            raise
    receipt.update(status='complete' if exit_code == 0 and not buffer else 'failed',
                   ended_utc=utc(), elapsed_seconds=round(time.monotonic()-started,3),
                   exit_code=exit_code, source_packets=count, saved_packets=saved,
                   saved_bytes=saved*188, sync_errors=sync_errors, trailing_bytes=len(buffer),
                   selected_pids=sorted(selected), source_mux_sha256=source_hash.hexdigest(),
                   broadcast_sha256=output_hash.hexdigest())
    receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt), flush=True)
    if receipt['status'] != 'complete': raise SystemExit(1)


if __name__ == '__main__':
    main()
