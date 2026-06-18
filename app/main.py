from __future__ import annotations

import argparse
import time
from pathlib import Path

from .config import load_config
from .history import load_state, save_state
from .scanner import iter_recent_files, iter_candidate_files
from .renamer import build_plan, apply_plan
from .style_detector import detect_styles
from .notifier import notify_rename_result


def main():
    parser = argparse.ArgumentParser(description='Media renamer for 115open/最近接收')
    sub = parser.add_subparsers(dest='command', required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--config', default='/app/config/config.yaml')
    common.add_argument('--recent-hours', type=int, default=None)
    common.add_argument('--limit', type=int, default=0)

    p_plan = sub.add_parser('plan', parents=[common], help='Only print plans, do not save state')

    p_scan = sub.add_parser('scan', parents=[common], help='Scan and rename recent files')
    p_scan.add_argument('--dry-run', action='store_true', help='Preview only')
    p_scan.add_argument('--apply', action='store_true', help='Actually rename files')

    p_watch = sub.add_parser('watch', parents=[common], help='Continuously watch and auto-rename stable new files')
    p_watch.add_argument('--interval', type=int, default=60)
    p_watch.add_argument('--stable-seconds', type=int, default=120)
    p_watch.add_argument('--dry-run', action='store_true')
    p_watch.add_argument('--apply', action='store_true')

    args = parser.parse_args()
    config = load_config(args.config)
    media_roots = [Path(p) for p in config.get('media_roots', [config.get('media_root')]) if p]
    recent_hours = args.recent_hours or config.get('recent_hours_default', 24)

    if args.command == 'plan':
        do_plan(media_roots, recent_hours, config, limit=args.limit)
        return
    if args.command == 'scan':
        dry_run = not args.apply
        do_scan(media_roots, recent_hours, config, dry_run=dry_run, limit=args.limit)
        return
    if args.command == 'watch':
        dry_run = not args.apply
        do_watch(media_roots, config, interval=args.interval, stable_seconds=args.stable_seconds, dry_run=dry_run)


def do_plan(media_roots: list[Path], recent_hours: int, config: dict, limit: int = 0):
    count = 0
    for media_root in media_roots:
        style = detect_styles(media_root, config)
        for path in iter_recent_files(str(media_root), recent_hours, config):
            plan = build_plan(path, media_root, config, style)
            if not plan:
                continue
            src, dst = plan
            print(f'{src} -> {dst}')
            count += 1
            if limit and count >= limit:
                return


def do_scan(media_roots: list[Path], recent_hours: int, config: dict, dry_run: bool, limit: int = 0):
    state_path = config['state_file']
    state = load_state(state_path)
    handled = state.setdefault('handled', {})
    planned = state.setdefault('planned', {})

    changed = False
    count = 0
    for media_root in media_roots:
        style = detect_styles(media_root, config)
        for path in iter_recent_files(str(media_root), recent_hours, config):
            key = str(path)
            try:
                mtime = int(path.stat().st_mtime)
            except FileNotFoundError:
                continue
            if not dry_run and handled.get(key) == mtime:
                continue
            plan = build_plan(path, media_root, config, style)
            if not plan:
                if not dry_run:
                    handled[key] = mtime
                    changed = True
                continue
            src, dst = plan
            result = apply_plan(src, dst, dry_run, config['log_file'], media_roots)
            print(f'[{result}] {src} -> {dst}')
            if dry_run:
                planned[str(src)] = str(dst)
            else:
                handled[str(dst if result == 'moved' else src)] = mtime
                if result == 'exists':
                    handled[key] = mtime
                elif key in handled and str(dst) != key:
                    del handled[key]
                if result in {'moved', 'dedup-replaced', 'dedup-deleted'}:
                    notify_rename_result(config, result, src, dst)
            changed = True
            count += 1
            if limit and count >= limit:
                if changed and not dry_run:
                    save_state(state_path, state)
                return
    if changed and not dry_run:
        save_state(state_path, state)


def do_watch(media_roots: list[Path], config: dict, interval: int, stable_seconds: int, dry_run: bool):
    state_path = config['state_file']
    state = load_state(state_path)
    handled = state.setdefault('handled', {})
    observed = {}

    while True:
        now = time.time()
        for media_root in media_roots:
            style = detect_styles(media_root, config)
            for path in iter_candidate_files(str(media_root), config):
                p = str(path)
                try:
                    st = path.stat()
                except FileNotFoundError:
                    continue
                sig = (st.st_size, int(st.st_mtime))
                prev = observed.get(p)
                if prev is None or prev['sig'] != sig:
                    observed[p] = {'sig': sig, 'first_seen': now, 'last_change': now}
                    continue
                if now - prev['last_change'] < stable_seconds:
                    continue
                if not dry_run and handled.get(p) == sig[1]:
                    continue
                plan = build_plan(path, media_root, config, style)
                if not plan:
                    if not dry_run:
                        handled[p] = sig[1]
                        save_state(state_path, state)
                    continue
                src, dst = plan
                result = apply_plan(src, dst, dry_run, config['log_file'], media_roots)
                print(f'[{result}] {src} -> {dst}', flush=True)
                if not dry_run:
                    handled[str(dst if result == 'moved' else src)] = sig[1]
                    if result == 'exists':
                        handled[p] = sig[1]
                    elif p in handled and str(dst) != p:
                        del handled[p]
                    if result in {'moved', 'dedup-replaced', 'dedup-deleted'}:
                        notify_rename_result(config, result, src, dst)
                    save_state(state_path, state)
        time.sleep(interval)


if __name__ == '__main__':
    main()
