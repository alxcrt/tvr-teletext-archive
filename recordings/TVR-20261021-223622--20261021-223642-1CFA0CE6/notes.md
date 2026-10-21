# TVR teletext preservation recording

Recorded by @alxcrt in Iași, Romania. Direct DVB-T2 reception, 650 MHz,
8 MHz bandwidth, teletext PID 117, using a WinTV-soloHD and its included antenna.
The received transmitter was not independently identified.

- First observed header: `'TVR\x07506 Mie 21 Oct 2026 22:36:22'`.
- Last observed header: `'TVR\x07111 Mie 21 Oct 2026 22:36:42'`.
- Broadcast clock timezone: Europe/Bucharest; raw header text is retained in headers.csv.
- Raw stream: 9,000 packets, 378,000 bytes.
- File CRC32: `1CFA0CE6`; SHA-256: `b33e9dde633278f76f8b711d69f0fa87ceabbef4222999fa8f116cd173eb7231`.
- Observed page numbers: 46; page/subpage pairs: 71; content versions: 72.

This is a bounded recording, with no claim of complete service coverage. Full raw
T42 preserves repetitions, unknown enhancements, orphan packets and original bytes.
Per-page versions select one actual transmission; packet indices in metadata.json
map every selected packet back to the untouched stream. No row merging, voting,
manual correction or image reconstruction is applied to these archival files.

`crc_status` distinguishes an exact page-CRC match, absent CRC and a mismatch
that can also reflect an unreceived row 25. File CRC32/SHA-256 verify file integrity,
not broadcast-page CRC or authenticity. Display-row presence is reported, not guessed.
Host timing and capture limits, where available, are in capture-receipt.json.
Raw T42 has no PES timestamps or playback pacing; retain broadcast.ts. A filtered
TS retains PES timestamps but is not a playable audio/video multiplex.

Broadcast material belongs to TVR and other respective rightsholders. This is an
independent preservation archive; no affiliation or broadcast-content licence is implied.
See the repository README, format documentation and tool licences for reuse limits.
