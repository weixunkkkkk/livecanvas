#!/usr/bin/env python3
"""Scan every decoded frame for abrupt changes; optionally guard a known-static ROI.

Requires only Python standard library, ffmpeg and ffprobe. Flagged frames need
visual review. Legitimate cuts may be declared with --allow-cut-frame. This is
not a photosensitivity assessment or a substitute for watching the video.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path


def difference_series(path, crop=None):
    filters = []
    if crop:
        x, y, width, height = crop
        filters.append(f'crop={width}:{height}:{x}:{y}')
    filters.extend(['scale=360:-2', 'format=yuv420p', 'tblend=all_mode=difference',
                    'signalstats', 'metadata=mode=print:key=lavfi.signalstats.YAVG:file=-'])
    result = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-v', 'warning',
                             '-i', str(path), '-an', '-vf', ','.join(filters),
                             '-f', 'null', '-'], text=True, capture_output=True, check=True)
    values = [float(value) for value in re.findall(r'lavfi\.signalstats\.YAVG=([\d.eE+-]+)', result.stdout)]
    if not values:
        raise ValueError('ffmpeg did not return frame-difference metrics')
    return values


def parse_region(value):
    try:
        values = tuple(int(part) for part in value.split(','))
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Use x,y,width,height in original video pixels') from exc
    if len(values) != 4 or min(values[:2]) < 0 or min(values[2:]) <= 0:
        raise argparse.ArgumentTypeError('Use non-negative x,y and positive width,height')
    return values


def analyze(path, max_delta=12.0, static_region=None, max_static_delta=0.5, allowed_cuts=()):
    path = Path(path).resolve()
    result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                             '-count_frames', '-show_entries',
                             'stream=width,height,nb_read_frames,avg_frame_rate',
                             '-of', 'json', str(path)], text=True, capture_output=True, check=True)
    streams = json.loads(result.stdout).get('streams', [])
    if not streams:
        raise ValueError('No video stream')
    stream = streams[0]
    frame_count = int(stream.get('nb_read_frames', 0))
    if frame_count < 2:
        raise ValueError('At least two decoded frames are required')
    if static_region:
        x, y, width, height = static_region
        if x + width > stream['width'] or y + height > stream['height']:
            raise ValueError('Static region exceeds video dimensions')
    allowed = set(allowed_cuts)
    if any(frame <= 0 or frame >= frame_count for frame in allowed):
        raise ValueError('Cut frame must identify the new frame in an adjacent-frame pair')
    global_delta = difference_series(path)
    static_delta = difference_series(path, static_region) if static_region else None
    if len(global_delta) != frame_count - 1 or (static_delta is not None and len(static_delta) != frame_count - 1):
        raise ValueError('Decoded frame count and difference count do not agree')
    flags = []
    for index, value in enumerate(global_delta, 1):
        if index in allowed:
            continue
        reasons = []
        if value > max_delta:
            reasons.append('large_full_frame_change')
        if static_delta is not None and static_delta[index - 1] > max_static_delta:
            reasons.append('known_static_region_changed')
        if reasons:
            flags.append({'frame': index, 'previousFrame': index - 1, 'reasons': reasons,
                          'meanLumaDifference': value,
                          'staticMeanLumaDifference': static_delta[index - 1] if static_delta else None})
    return {'video': str(path), 'status': 'passed' if not flags else 'review_required',
            'decodedFrames': frame_count, 'adjacentPairsChecked': len(global_delta),
            'stream': stream, 'metric': 'adjacent mean absolute luma difference, 0..255, scaled width 360',
            'thresholds': {'fullFrame': max_delta, 'staticRegion': max_static_delta},
            'staticRegion': static_region, 'allowedCutFrames': sorted(allowed),
            'maxFullFrameDifference': max(global_delta),
            'maxStaticRegionDifference': max(static_delta) if static_delta else None,
            'flaggedFrames': flags, 'frameDifferences': global_delta,
            'staticFrameDifferences': static_delta,
            'scope': 'decoded-file anomaly screening; playback and visual review still required'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--static-region', type=parse_region,
                        help='Known visually constant region: x,y,width,height')
    parser.add_argument('--max-delta', type=float, default=12.0)
    parser.add_argument('--max-static-delta', type=float, default=0.5)
    parser.add_argument('--allow-cut-frame', type=int, action='append', default=[])
    args = parser.parse_args()
    if args.max_delta <= 0 or args.max_static_delta <= 0:
        parser.error('Thresholds must be positive')
    try:
        report = analyze(args.video, args.max_delta, args.static_region,
                         args.max_static_delta, args.allow_cut_frame)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f'Frame scan failed: {exc}\n')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['status', 'decodedFrames', 'adjacentPairsChecked',
                                                'maxFullFrameDifference', 'maxStaticRegionDifference',
                                                'flaggedFrames']}, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
