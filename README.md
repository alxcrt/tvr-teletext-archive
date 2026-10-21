# TVR Teletext Archive · Romania

Original Romanian TVR teletext recordings, preserved as raw T42 packets with
reception notes, service descriptors, transport sources, checksums and observed
page versions. Recorded in Iași by [@alxcrt](https://github.com/alxcrt), using a
Hauppauge WinTV-soloHD and its included antenna on DVB-T2 channel 43 / 650 MHz.
The exact transmitter was not independently identified.

**[Browse the recorded pages](https://alxcrt.github.io/tvr-teletext-archive/)** ·
**[Download preservation bundles](https://github.com/alxcrt/tvr-teletext-archive/releases)** ·
[Machine-readable catalogue](catalog.json) · [Verify file hashes](SHA256SUMS)

These are original directly received broadcast packets. They include original
parity, repetition and enhancement data. This collection contains no generated
Antena pages or restorations inferred from screenshots. It is a set of bounded
recordings with gaps, not a continuous feed or a claim of complete service coverage.

## Recordings

Times in recording names come from the on-air headers in Europe/Bucharest.
Full dates on both ends handle midnight explicitly. Host UTC receipts are kept
separately. Counts include partial observed versions; see each recording's notes.

| Recording / notes | Packets | Page numbers | Page/subpage pairs | Observed versions |
|---|---:|---:|---:|---:|
| [TVR-20261021-223622--20261021-223642-1CFA0CE6](recordings/TVR-20261021-223622--20261021-223642-1CFA0CE6/notes.md) | 9,000 | 46 | 71 | 72 |
| [TVR-20261021-231028--20261021-231327-4DED57B3](recordings/TVR-20261021-231028--20261021-231327-4DED57B3/notes.md) | 81,000 | 46 | 73 | 74 |
| [TVR-20261021-234519--20261022-000019-0C46F8C1](recordings/TVR-20261021-234519--20261022-000019-0C46F8C1/notes.md) | 404,982 | 46 | 73 | 147 |

The scanned multiplex associates the same teletext PID **117 / 0x75** with 11 TVR
services: TVR 1, TVR 2, TVR 3, TVR Cluj, TVR Craiova, TVR Iasi, TVR Timisoara,
TVR Tg Mures, TVR INFO, TVR Cultural and TVR SPORT. These are references to one
shared stream, not 11 independently captured archives. `services.json` preserves
the original scan's program/stream metadata, including the `Rum` language tag.

## What is preserved

- Untouched T42 streams after documented DVB wrapper/bit-order extraction.
- Selected original transport packets, retaining PES timestamp data and available
  service tables; audio/video and their PCR streams are omitted.
- Capture UTC receipts, on-air header inventory, receiver/frequency/PID, original
  multiplex packet positions where available, file SHA-256 and filename CRC32.
- Individual observed page/subpage/content versions, raw packet offsets, header
  flags, national-option bits, row presence, enhancements and error statistics.
- Broadcast page-CRC results, explicitly separate from file checksums. Truncated
  and unchecksummed versions remain labelled; no silent repairs or row voting.
- Native-data browser, PNG previews for every observed version, and reproducible
  extraction, indexing, verification and rendering tools.

See [formats and methods](FORMATS.md) and each recording's `notes.md`,
`metadata.json`, `headers.csv`, `pages.json`, capture receipt and extraction report.
The full T42 is authoritative; a preview can omit unsupported enhancements or
approximate the decoder's font/character set. Empty cells may be unreceived.

To browse offline, extract a release and run:

```sh
python3 -m http.server 8768 --bind 127.0.0.1
```

Then open http://127.0.0.1:8768/. For validation:

```sh
python3 tools/verify-archive.py .
```

## Validation

All 293 per-recording page-version files reproduce exactly from the original
packet offsets. T42 extraction reproduces exactly from each retained TS source.
The [independent vhs-teletext check](independent-validation.json) agrees on all
293 addresses and page-CRC calculations: 209 match a transmitted CRC, 81 have
no transmitted CRC, and three partial transmissions end at a recording cutoff.
Versions can recur between recordings; these are not 293 independent page numbers.

## Provenance and community references

The archive follows the useful distinctions in
[teletext-restoration](https://github.com/teletext-restoration/teletext-restoration):
raw streams, dated recovery notes, per-page files, observation times and separate
checksum/uncertainty labels. This is direct digital reception, so no VHS recovery
or manual restoration was needed. Optional independent checks use
[ali1234/vhs-teletext](https://github.com/ali1234/vhs-teletext), revision
`f470629a3d5d3b0a577153832505e187beeb7204`, with its supported dependencies.

Useful related collections are the [Teletext Archaeologist Archive](https://www.teletextarchive.com/),
[Alistair Buxton's recovered teletext](https://al.zerostem.io/~al/teletext/), and
[the teletext-restoration repository](https://github.com/teletext-restoration/teletext-restoration).
This archive is independent of those projects and of TVR.

## Rights and contributions

Broadcast text, logos, programmes and other content remain the property of TVR
and their respective rightsholders. No licence to the broadcast content is
claimed or granted by this repository. The archive is preserved for research,
interoperability and historical interest, with source attribution retained.
There is no broadcaster endorsement or affiliation.

Original archive tools/viewer code: [MIT](LICENSE-CODE). Bedstead bitmap source:
[CC0, with its original dedication and attribution](fonts/README.md). These code
licences do not cover the recordings. Archive metadata and documentation may be
reused with attribution to @alxcrt and a link to the specific recording, preserving
its reception/quality limitations; no rights in quoted broadcast material transfer.

Contributions should include the original stream, country/service, reception date
and timezone, source/receiver details, file hashes, extraction method and honest
coverage/error notes. Keep raw bytes intact; submit any restorations separately
with a change log. Don't relabel screenshot reconstructions as broadcast captures.
Do not include credentials, host identifiers or private network details.
