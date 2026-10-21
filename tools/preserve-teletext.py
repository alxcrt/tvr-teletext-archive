#!/usr/bin/env python3
"""Inventory original T42 transmissions without rewriting or squashing packets.

Derived page files each contain one observed transmission. Rows from different
cycles are never merged. Full raw streams retain repetitions, orphans and unknown
enhancements. All decisions are reproducible from packet offsets and hashes.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import zlib

H = [0x15,0x02,0x49,0x5e,0x64,0x73,0x38,0x2f,0xd0,0xc7,0x8c,0x9b,0xa1,0xb6,0xfd,0xea]
HAMMING = []
for value in range(256):
    matches = [(i, (value^code).bit_count()) for i, code in enumerate(H) if (value^code).bit_count() <= 1]
    HAMMING.append(matches[0] if len(matches) == 1 else (-1, -1))


def digest(raw): return hashlib.sha256(raw).hexdigest()
def text(raw): return ''.join(chr(c&127) for c in raw)


def page_crc(header, rows):
    """ETSI page CRC, including odd-parity bytes and blank untransmitted rows."""
    crc = 0
    for byte in header[10:34]+b''.join(rows.get(y, b' '*40) for y in range(1,26)):
        for i in range(7,-1,-1):
            bit = ((byte>>i)^(crc>>6)^(crc>>8)^(crc>>11)^(crc>>15))&1
            crc = ((crc&0x7fff)<<1)|bit
    return crc


def inspect(raw):
    if not raw or len(raw)%42:
        raise ValueError('Expected nonempty, aligned 42-byte T42 packets')
    stats = Counter(); packet_types = Counter(); languages = Counter()
    bad_addresses=[]; bad_headers=[]; bad_display=[]
    active = {}; pages = defaultdict(dict); events = []; global_indices = []
    def finish(magazine, reason='next-header'):
        cycle = active.pop(magazine, None)
        if not cycle: return
        if not cycle['rows']:
            stats['header_only_cycles'] += 1; return
        stats['data_cycles'] += 1
        rows = cycle['rows']; indices = cycle['indices']; first = cycle['first_packet']
        head = raw[first*42:(first+1)*42]
        # Ignore the changing clock; preserve all other header/address/control
        # bytes and the last observed packet for every associated row/designation.
        associated = cycle['packets']
        signature = digest(head[:34]+b''.join(associated[k] for k in sorted(associated)))
        key = cycle['number']+'-'+format(cycle['subpage'], '04x')
        candidate = dict(content_sha256=signature, first_header=cycle['header'], last_header=cycle['header'],
                         observations=1, first_packet=first, last_packet=indices[-1],
                         packet_indices=indices, row_numbers=sorted(rows),
                         national_option=cycle['national_option'], header_flags=cycle['flags'],
                         parity_errors=cycle['parity_errors'],
                         address_corrections=cycle['address_corrections'],
                         header_corrections=cycle['header_corrections'],
                         extension_packets=cycle['extensions'],
                         closed_by=reason,
                         expected_crc=None, calculated_crc=None, crc_status='not-present')
        links = associated.get((27,0))
        if links:
            expected = int.from_bytes(links[40:42], 'big'); calculated = page_crc(head, rows)
            candidate.update(expected_crc=expected, calculated_crc=calculated,
                             crc_status='match' if expected==calculated else 'mismatch-or-unreceived-row25')
            if expected != calculated and reason == 'end-of-stream':
                candidate['crc_status'] = 'mismatch-at-capture-cutoff'
        candidate['model'] = dict(id=key, number=cycle['number'], subpage=cycle['subpage'],
            wireSubpage=cycle['subpage'], romanian=False,
            rows=['P'+cycle['number'].upper()+'    '+text(head[10:])]+[text(rows.get(y,b' '*40)) for y in range(1,25)])
        previous = pages[key].get(signature)
        score = (len(rows), int(candidate['crc_status']=='match'), -cycle['parity_errors'], -cycle['address_corrections'])
        if previous:
            previous['observations'] += 1; previous['last_header'] = cycle['header']; previous['last_seen_packet'] = first
            if score >= previous['_score']:
                first_header, last_header, observations = previous['first_header'], previous['last_header'], previous['observations']
                previous.update(candidate, first_header=first_header, last_header=last_header, observations=observations)
                previous['_score'] = score
        else:
            candidate['_score'] = score; candidate['last_seen_packet'] = first; pages[key][signature] = candidate
    for index in range(len(raw)//42):
        p = raw[index*42:(index+1)*42]
        a, ac = HAMMING[p[0]]; b, bc = HAMMING[p[1]]
        if a<0 or b<0:
            stats['uncorrectable_addresses'] += 1; bad_addresses.append(index); continue
        correction = ac+bc; stats['corrected_address_bits'] += correction
        address = a|(b<<4); mag = (address&7) or 8; row = address>>3
        packet_types[str(row)] += 1
        if row == 0:
            decoded = [HAMMING[x] for x in p[2:10]]
            if any(n<0 for n,_ in decoded):
                finish(mag); stats['uncorrectable_headers'] += 1; bad_headers.append(index); continue
            n = [v for v,_ in decoded]; hc = sum(c for _,c in decoded)
            stats['corrected_header_bits'] += hc
            if n[7]&1:
                for active_mag in list(active): finish(active_mag)
            else: finish(mag)
            number = f'{mag:x}{n[1]:x}{n[0]:x}'; sub = n[2]|((n[3]&7)<<4)|(n[4]<<8)|((n[5]&3)<<12)
            header = text(p[10:]); languages[str(n[7]>>1)] += 1
            header_parity = sum(byte.bit_count()%2 != 1 for byte in p[10:])
            stats['header_parity_errors'] += header_parity
            events.append(dict(packet=index,number=number,subpage=f'{sub:04x}',header=header,
                               clock=header[-8:],national_option=n[7]>>1,serial=n[7]&1,
                               address_corrected_bits=correction,header_corrected_bits=hc))
            if number[1:] == 'ff':
                stats['filler_headers'] += 1; continue
            active[mag] = dict(number=number, subpage=sub, first_packet=index, indices=[index],
                               rows={},packets={},extensions=Counter(),header=header,
                               national_option=n[7]>>1,
                               flags=dict(erase=bool(n[3]&8),newsflash=bool(n[5]&4),subtitle=bool(n[5]&8),
                                          suppress_header=bool(n[6]&1),update=bool(n[6]&2),
                                          interrupted=bool(n[6]&4),inhibit=bool(n[6]&8),serial=bool(n[7]&1)),
                               parity_errors=header_parity,address_corrections=correction,header_corrections=hc)
        elif 1<=row<=28 and mag in active:
            cycle = active[mag]; cycle['indices'].append(index); cycle['address_corrections'] += correction
            designation = HAMMING[p[2]][0] if row>=26 else -1
            cycle['packets'][row,designation] = p
            if row<=25:
                cycle['rows'][row] = p[2:]
                errors = sum(byte.bit_count()%2 != 1 for byte in p[2:])
                cycle['parity_errors'] += errors; stats['display_parity_errors'] += errors
                if errors: bad_display.append(dict(packet=index,parity_errors=errors))
            else: cycle['extensions'][str(row)] += 1
        else:
            stats['unassociated_or_service_packets'] += 1; global_indices.append(index)
    for mag in list(active): finish(mag, 'end-of-stream')
    # Select the most complete observed content, then latest occurrence. This
    # deliberately avoids synthesizing a page from multiple reception cycles.
    selected = {}
    for key, versions in pages.items():
        selected[key] = max(versions.values(), key=lambda v:(v['_score'],v['last_seen_packet']))['content_sha256']
        for version in versions.values(): version.pop('_score',None)
    return dict(packets=len(raw)//42,bytes=len(raw),sha256=digest(raw),crc32=f'{zlib.crc32(raw):08X}',
                statistics=dict(stats),packet_types=dict(packet_types),national_options=dict(languages),
                page_numbers=sorted({key.split('-')[0] for key in pages}),
                announced_page_subpages=sorted({h['number']+'-'+h['subpage'] for h in events if h['number'][1:]!='ff'}),
                page_subpages=len(pages),content_versions=sum(len(v) for v in pages.values()),
                uncorrectable_address_packet_indices=bad_addresses,
                uncorrectable_header_packet_indices=bad_headers,display_parity_error_packets=bad_display,
                pages=dict(pages),selected=selected,headers=events,unassociated_packet_indices=global_indices)


def write_archive(source, output, *, source_ts=None, receipt=None, service_metadata=None, source_index=None, contributor='alxcrt'):
    raw = source.read_bytes(); result = inspect(raw)
    clocks = [h['header'] for h in result['headers']]
    pattern = re.compile(r'(\d{2})\s+([A-Za-z]{3})\s+(\d{4})\s+(\d{2}):(\d{2}):(\d{2})$')
    months = {m:i for i,m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(),1)}
    months.update(Ian=1,Mai=5,Iun=6,Iul=7,Noi=11)
    def stamp(header):
        match = pattern.search(header)
        if not match or match[2] not in months: return 'undated'
        day, month, year, hour, minute, second = match.groups()
        return f'{year}{months[month]:02d}{day}-{hour}{minute}{second}'
    first = stamp(clocks[0]) if clocks else 'undated'; last = stamp(clocks[-1]) if clocks else 'undated'
    name = f'TVR-{first}--{last}-{result["crc32"]}'
    folder = output/name; folder.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(source,folder/(name+'.t42'))
    if source_ts: shutil.copyfile(source_ts,folder/'broadcast.ts')
    if receipt: shutil.copyfile(receipt,folder/'capture-receipt.json')
    if service_metadata: shutil.copyfile(service_metadata,folder/'services.json')
    if source_index: shutil.copyfile(source_index,folder/'source-ts-index.u64le')
    writer = io.StringIO(); headers = result.pop('headers')
    if headers:
        escaped = [dict(h,header=json.dumps(h['header'],ensure_ascii=True)) for h in headers]
        csv_writer = csv.DictWriter(writer,fieldnames=list(escaped[0])); csv_writer.writeheader(); csv_writer.writerows(escaped)
    (folder/'headers.csv').write_text(writer.getvalue())
    models = []; index = []
    for key, versions in sorted(result['pages'].items()):
        for signature, version in versions.items():
            def clock_name(header):
                clock=re.sub('[^0-9]','',header[-8:])
                return clock if len(clock)==6 else 'undated'
            status=version['crc_status']
            suffix='-nocrc' if status=='not-present' else '-partial' if status=='mismatch-at-capture-cutoff' else '-crc-mismatch' if status!='match' else ''
            relative = f'pages/P{key}-{clock_name(version["first_header"])}-{clock_name(version["last_header"])}-{signature[:12]}{suffix}.t42'
            dest = folder/relative; dest.parent.mkdir(exist_ok=True)
            packet_bytes = b''.join(raw[i*42:(i+1)*42] for i in version['packet_indices'])
            dest.write_bytes(packet_bytes)
            version.update(file=relative,file_sha256=digest(packet_bytes),file_bytes=len(packet_bytes))
            model = version.pop('model')
            model.update(file=relative,source_sha256=version['file_sha256'],content_sha256=signature,
                         first_header=version['first_header'],last_header=version['last_header'],
                         observations=version['observations'],receivedRows=version['row_numbers'],
                         crc_status=version['crc_status'],selected=result['selected'][key]==signature,
                         title=f'TVR {model["number"]} / {model["subpage"]:04x}')
            models.append(model)
            index.append(dict(page=key,file=relative,first_header=version['first_header'],last_header=version['last_header'],
                              observations=version['observations'],rows=version['row_numbers'],crc_status=version['crc_status']))
    result.update(format_version=1,archive_id=name,contributor=contributor,broadcaster='TVR',country='RO',
                  reception_city='Iași',reception_region='Romania',timezone='Europe/Bucharest',
                  receiver='Hauppauge WinTV-soloHD (2040:8268), included antenna',
                  transport=dict(system='DVB-T2',frequency_hz=650000000,bandwidth_hz=8000000,teletext_pid=117,
                                 transmitter='Not independently identified'),
                  first_header=clocks[0] if clocks else None,last_header=clocks[-1] if clocks else None,
                  authenticity='Original directly received DVB teletext packets; no image reconstruction.',
                  completeness='Observed sample only; absence does not establish nonexistence of a page.',
                  transformations=['DVB PES/data-unit wrappers removed and byte bit order normalized for raw T42.',
                                   'Raw T42 is unchanged after extraction; repeats, enhancements and orphans retained.',
                                   'Per-version files select original packets from a single transmission; no row merging.',
                                   'Header/address Hamming correction is used only for indexing, never to rewrite stored packets.',
                                   'JSON/HTML previews strip parity and approximate Level 1 rendering.'],
                  rights='Broadcast content belongs to TVR and other respective rightsholders; no broadcast-content licence is granted.')
    if source_ts:
        result['source_ts'] = dict(file='broadcast.ts',bytes=source_ts.stat().st_size,sha256=digest(source_ts.read_bytes()),
                                  scope='Selected original TS packets. Audio/video and PCR streams may be omitted; consult capture receipt.')
    if source_index:
        result['source_index'] = dict(file='source-ts-index.u64le',bytes=source_index.stat().st_size,
                                     sha256=digest(source_index.read_bytes()),format='uint64 little-endian, zero-based original multiplex TS packet positions')
    (folder/'metadata.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (folder/'pages.json').write_text(json.dumps(models,ensure_ascii=False,indent=2)+'\n')
    notes = f'''# TVR teletext preservation recording\n\nRecorded by @{contributor} in Iași, Romania. Direct DVB-T2 reception, 650 MHz,\n8 MHz bandwidth, teletext PID 117, using a WinTV-soloHD and its included antenna.\nThe received transmitter was not independently identified.\n\n- First observed header: `{repr(result['first_header'])}`.\n- Last observed header: `{repr(result['last_header'])}`.\n- Broadcast clock timezone: Europe/Bucharest; raw header text is retained in headers.csv.\n- Raw stream: {result['packets']:,} packets, {result['bytes']:,} bytes.\n- File CRC32: `{result['crc32']}`; SHA-256: `{result['sha256']}`.\n- Observed page numbers: {len(result['page_numbers'])}; page/subpage pairs: {result['page_subpages']}; content versions: {result['content_versions']}.\n\nThis is a bounded recording, with no claim of complete service coverage. Full raw\nT42 preserves repetitions, unknown enhancements, orphan packets and original bytes.\nPer-page versions select one actual transmission; packet indices in metadata.json\nmap every selected packet back to the untouched stream. No row merging, voting,\nmanual correction or image reconstruction is applied to these archival files.\n\n`crc_status` distinguishes an exact page-CRC match, absent CRC and a mismatch\nthat can also reflect an unreceived row 25. File CRC32/SHA-256 verify file integrity,\nnot broadcast-page CRC or authenticity. Display-row presence is reported, not guessed.\nHost timing and capture limits, where available, are in capture-receipt.json.\nRaw T42 has no PES timestamps or playback pacing; retain broadcast.ts. A filtered\nTS retains PES timestamps but is not a playable audio/video multiplex.\n\nBroadcast material belongs to TVR and other respective rightsholders. This is an\nindependent preservation archive; no affiliation or broadcast-content licence is implied.\nSee the repository README, format documentation and tool licences for reuse limits.\n'''
    (folder/'notes.md').write_text(notes)
    return dict(id=name,path=name,first_header=result['first_header'],last_header=result['last_header'],
                packets=result['packets'],bytes=result['bytes'],sha256=result['sha256'],
                page_numbers=len(result['page_numbers']),page_subpages=result['page_subpages'],
                content_versions=result['content_versions'],pages_index='pages.json')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-ts',type=Path); parser.add_argument('--receipt',type=Path)
    parser.add_argument('--services',type=Path)
    parser.add_argument('--source-index',type=Path)
    args=parser.parse_args()
    print(json.dumps(write_archive(args.source,args.output,source_ts=args.source_ts,receipt=args.receipt,service_metadata=args.services,source_index=args.source_index),indent=2))


if __name__=='__main__': main()
