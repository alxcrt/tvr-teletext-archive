# Formats and preservation decisions

## Three distinct layers

- `broadcast.ts`: selected, unchanged 188-byte MPEG transport packets. The
  receipt identifies which PIDs were kept. These are not complete playable TV
  multiplexes; audio/video and their PCR streams are omitted. PES timestamps
  remain. For captures with a source-index sidecar, original multiplex packet
  positions can also be reconstructed.
- `TVR-<first local date/time>--<last local date/time>-<CRC32>.t42`: original
  teletext packets, 42 bytes each, in received order after DVB extraction.
  There are no embedded timestamps, container headers or clock-run-in/framing
  bytes. Repetitions, unknown enhancements, parity bits and orphan packets remain.
- `pages/P<magazine/page>-<native subcode>-<first/last clock>-<content hash>.t42`: packets selected
  from one actual transmission of that page version. Their source packet indices
  are recorded. These are never composed from rows of different cycles.

The filename times come from first/last observed broadcast headers in
Europe/Bucharest. Cross-midnight dates are included explicitly. They are separate
from host UTC times in capture receipts, which may include tuning overhead.
An unknown/unparsed date is explicitly `undated`, never filled from a guess.

## Checksums and versions

File SHA-256 and filename CRC32 cover actual file bytes. Page CRC is the
broadcast checksum in X/27/0 and has a separate status. A missing page CRC,
unreceived display row or partial capture is never called repaired/complete.
Metadata records original header control flags, national-option bits, parity
errors, correctable/uncorrectable Hamming addresses, packet-type counts,
enhancements, row presence, observation counts and source packet offsets.

Content-version fingerprints exclude only the final eight header clock bytes,
then compare the remaining header and last observed packet per row/designation.
This preserves other header changes, controls and enhancements. A partial
transmission is retained as its own observed variant. The default preview selects
the most complete version, preferring a matching broadcast CRC at equal row
coverage, then the latest observation, using one real
transmission. It does not imply the page is the latest editorial update.

`headers.csv` inventories all decodable headers, including filler/header-only
cycles; its header text uses JSON escaping for control characters. `pages.json`
and PNGs are derived conveniences. The transport source preserves the received
DVB bytes; the source T42 is the portable teletext master for the documented
extraction. Only complete PES packets are extracted. Data in an incomplete
initial/final PES remains in the transport source; extraction reports record
discarded cutoffs. Per-page filename suffixes `-nocrc`, `-partial` and
`-crc-mismatch` retain the quality distinction when a file is copied separately.
Hamming correction is used for indexing only; stored packet bytes are unchanged.

## Reproduction

Python 3 standard library extracts and inventories packets:

```sh
python3 tools/extract-dvb-teletext.py recording/broadcast.ts --pid 117 --output /tmp/example.t42
python3 tools/preserve-teletext.py /tmp/example.t42 --output /tmp/new-archive
python3 tools/verify-archive.py .
node tools/render-pages.mjs recordings
```

`tools/capture-preservation.py` is an optional bounded Linux recorder requiring
existing DVB tuner access and `dvbv5-zap`. It changes no persistent configuration.
For recordings made with that tool it preserves teletext, PAT, NIT, SDT, TDT/TOT and
PAT-discovered PMT packets, plus a uint64 little-endian original packet-index
sidecar. Earlier recordings have explicitly smaller scopes.

Optional independent decoding is checked with the separately obtained
`ali1234/vhs-teletext` tree and its supported NumPy <2 dependency:

```sh
python3 tools/verify-preservation-upstream.py --upstream /path/to/vhs-teletext \
  --archive recordings --output independent-validation.json
```

The static reader is a bounded Level 1 preview. It does not implement general
X/26, DRCS or Level 2.5. Font and national-character rendering can differ from
a TV receiver. The observed national-option bits are kept verbatim; they do not
prove which character set the broadcaster intended. Raw enhancement and
service-context packets remain available for better future decoders.

Standards: [ETSI EN 300 472](https://www.etsi.org/deliver/etsi_en/300400_300499/300472/01.04.01_60/en_300472v010401p.pdf)
for DVB carriage, and [ETSI EN 300 706](https://www.etsi.org/deliver/etsi_en/300700_300799/300706/01.02.01_60/en_300706v010201p.pdf)
for teletext packets, coding and presentation.

Release ZIP member timestamps are fixed for reproducibility. Use the recording receipts and on-air header inventory for actual source times, rather than extracted file mtimes.

Public capture logs retain tuning measurements; recorder-local filesystem path prefixes are removed from public copies. The unredacted originals remain protected separately.
