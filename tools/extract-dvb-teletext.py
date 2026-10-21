#!/usr/bin/env python3
"""Extract bit-correct raw T42 packets from one DVB teletext PID (EN 300 472).

No decoder dependency. Preserve every valid 0x02/0x03 data unit, including
enhancements; T42 retains packet order but does not retain PES timestamps.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

REVERSE = bytes(int(f'{n:08b}'[::-1], 2) for n in range(256))


def extract(source, target, pid):
    if not 0 <= pid < 8191:
        raise ValueError('PID must be between 0 and 8190')
    stats = Counter()
    source_hash, output_hash = hashlib.sha256(), hashlib.sha256()
    pending = None
    previous = None

    def consume(pes):
        if len(pes) < 9 or pes[:4] != b'\0\0\1\xbd' or pes[6] & 0xc0 != 0x80 or pes[6] & 0x30:
            stats['invalid_pes'] += 1
            return
        offset = 9 + pes[8]
        if offset >= len(pes) or not 0x10 <= pes[offset] <= 0x1f:
            stats['invalid_pes'] += 1
            return
        stats['pes_packets'] += 1
        offset += 1
        while offset < len(pes):
            if offset + 2 > len(pes):
                stats['invalid_units'] += 1
                break
            kind, length = pes[offset:offset + 2]
            offset += 2
            if offset + length > len(pes):
                stats['invalid_units'] += 1
                break
            unit = pes[offset:offset + length]
            offset += length
            if kind == 0xff:
                stats['stuffing_units'] += 1
            elif kind in (2, 3):
                if length != 44 or unit[1] != 0xe4:
                    stats['invalid_units'] += 1
                    continue
                packet = unit[2:].translate(REVERSE)
                target.write(packet)
                output_hash.update(packet)
                stats['teletext_packets'] += 1
            else:
                stats['other_units'] += 1

    while True:
        packet = source.read(188)
        if not packet:
            break
        source_hash.update(packet)
        stats['source_bytes'] += len(packet)
        if len(packet) != 188 or packet[0] != 0x47:
            raise ValueError('Expected aligned 188-byte MPEG-TS packets')
        if ((packet[1] & 0x1f) << 8 | packet[2]) != pid:
            continue
        stats['pid_ts_packets'] += 1
        afc = (packet[3] >> 4) & 3
        offset = 4
        if afc & 2:
            offset = 5 + packet[4]
            if offset > 188:
                stats['transport_errors'] += 1
                pending = previous = None
                continue
            if packet[4] and packet[5] & 0x80:
                stats['discontinuities'] += 1
                pending = previous = None
        if not afc or packet[1] & 0x80 or packet[3] & 0xc0:
            stats['transport_errors'] += 1
            pending = previous = None
            continue
        if not afc & 1 or offset == 188:
            continue
        cc = packet[3] & 15
        if previous is not None:
            if packet == previous:
                stats['duplicate_ts_packets'] += 1
                continue
            if cc != ((previous[3] & 15) + 1) % 16:
                stats['continuity_errors'] += 1
                pending = None
        previous = packet
        if packet[1] & 0x40:
            if pending:
                stats['truncated_pes'] += 1
            pending = bytearray()
        if pending is None:
            continue
        pending.extend(packet[offset:])
        if len(pending) < 6:
            continue
        length = int.from_bytes(pending[4:6], 'big')
        if not length or pending[:4] != b'\0\0\1\xbd':
            stats['invalid_pes'] += 1
            pending = None
        elif len(pending) >= length + 6:
            consume(pending[:length + 6])
            pending = None
    if pending:
        stats['truncated_pes'] += 1
    return {**dict(stats), 'pid': pid, 'source_sha256': source_hash.hexdigest(),
            't42_sha256': output_hash.hexdigest(), 'timing_preserved': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = args.report or args.output.with_suffix('.json')
    paths = [args.source.resolve(), args.output.resolve(), report.resolve()]
    if len(set(paths)) != 3 or args.output.exists() or report.exists():
        parser.error('Use distinct source/output/report paths; outputs must not already exist')
    created = False
    try:
        with args.source.open('rb') as source, args.output.open('xb') as target:
            created = True
            result = extract(source, target, args.pid)
        if not result.get('teletext_packets'):
            raise ValueError('No valid teletext data units found on the requested PID')
    except Exception:
        if created:
            args.output.unlink(missing_ok=True)
        raise
    with report.open('x') as output:
        output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
