"""Bounded offline validation. Original runner is preserved, not executed."""
import argparse, ast, hashlib, importlib.util, json, os
from pathlib import Path
import shlex, shutil, socket, stat, subprocess, sys, tempfile, unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[1]
STAGE = ROOT / '.sciv-stage-20261012'
GEN = ROOT / '.codex/sciv-deps/gerador'
GOV = ROOT / '.codex/sciv-deps/governanca'
PY = ROOT.parent / '.venvs/sciv-issue5/Scripts/python.exe'
GIT = shutil.which('git')
EXPECTED = {'gerador': '260365c810449c91b1759ee6cf0506b09e571a1a',
            'governanca': '88fa8d60abbbf5a068a027aae0803dc6d45494d8'}
SUITES = {
    'generator': (GEN / 'tools', ['test_sciv_bootstrap',
                                 'test_project_creation_gate',
                                 'test_validate_execution_action_plan']),
    'runtime': (GOV / 'runtime', ['test_sciv_essential', 'test_sciv_per_project']),
    'pep-offline': (GOV / 'tools', ['test_r2_pep_offline']),
}
EXCLUDED = {'test_site_cli_pass_and_fail_exit_codes',
            'test_cli_recovery_across_actual_python_processes'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def clean_path(path, within):
    path = Path(os.path.abspath(path))
    if not path.is_relative_to(within):
        raise PermissionError('OUTSIDE_VALIDATION_STAGE')
    for candidate in [path, *path.parents]:
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise PermissionError('REPARSE_OR_SYMLINK')
    return path

def query(repo, *args):
    result = subprocess.run([GIT, '-c', f'safe.directory={repo.as_posix()}',
                             '-C', str(repo), *args], capture_output=True,
                            timeout=30, check=True)
    return result.stdout

def snapshot():
    result = {}
    for label, repo in [('project', ROOT), ('gerador', GEN), ('governanca', GOV)]:
        result[label + ':HEAD'] = query(repo, 'rev-parse', 'HEAD').decode().strip()
        result[label + ':index'] = sha(query(repo, 'ls-files', '--stage', '-z'))
        for raw in query(repo, 'ls-files', '-z').decode().split('\0'):
            if raw:
                path = repo / raw
                result[label + ':' + raw] = sha(path.read_bytes()) if path.is_file() else None
    return result

def preflight():
    clean_path(STAGE / 'security-preflight-r03.json', STAGE)
    if query(ROOT, 'rev-parse', 'HEAD').decode().strip() != '189763dc611b2eb5817773330c7e9d66a2576a3a':
        raise RuntimeError('PROJECT_HEAD_CHANGED')
    if query(ROOT, 'diff', '--name-only', 'HEAD') or query(ROOT, 'diff', '--cached', '--name-only'):
        raise RuntimeError('CANONICAL_CHANGES')
    for name, repo in [('gerador', GEN), ('governanca', GOV)]:
        if query(repo, 'rev-parse', 'HEAD').decode().strip() != EXPECTED[name]:
            raise RuntimeError('DEPENDENCY_HEAD_CHANGED')
        if query(repo, 'status', '--porcelain'):
            raise RuntimeError('DEPENDENCY_NOT_CLEAN')
    # Parse all Python sources in the selected dependency surfaces without importing.
    sources = [Path(__file__), ROOT / '.codex/sciv_delivery.py']
    sources += list((GEN / 'tools').glob('*.py'))
    sources += list((GOV / 'runtime').glob('*.py'))
    sources += [GOV / 'tools' / (name + '.py') for name in
                ['check_runtime_dependencies', 'test_r2_pep_offline', 'test_r2_policy_engine']]
    hashes = {}
    for source in sources:
        data = source.read_bytes()
        ast.parse(data, filename=str(source))
        hashes[source.relative_to(ROOT).as_posix()] = sha(data)
    result = {'status': 'STATIC_PREFLIGHT_PASS', 'sources_parsed': len(hashes),
              'source_sha256': hashes, 'dependency_heads': EXPECTED,
              'selected_suites': list(SUITES),
              'excluded_methods': sorted(EXCLUDED),
              'legacy_git_fixture_suite': 'NOT_EXECUTED_NO_COMMITS_ENVELOPE',
              'canonical_snapshot_sha256': sha(json.dumps(snapshot(), sort_keys=True).encode()),
              'scope': 'CODEX_CHECKS_NOT_INDEPENDENT_ASSURANCE'}
    destination = STAGE / 'security-preflight-r03.json'
    with destination.open('xb') as stream:
        stream.write((json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, indent=2))

def install_guard(scratch):
    scratch = clean_path(scratch, STAGE)
    tempfile.tempdir = str(scratch)
    def path_check(value):
        if isinstance(value, int):
            raise PermissionError('UNTRACKED_FD_EFFECT')
        return clean_path(os.fsdecode(value), scratch)
    def audit(event, args):
        if event.startswith('socket.') or event in ('os.system', 'os.exec', 'os.posix_spawn',
                                                    'ctypes.dlopen', 'ctypes.dlsym'):
            # Python/native imports may require ctypes; none are needed by this envelope.
            raise PermissionError('OFFLINE_EFFECT_DENIED:' + event)
        if event == 'open':
            path, mode, flags = args
            if isinstance(path, int):
                return  # Existing temporary descriptors originate from checked os.open.
            if (mode and any(c in mode for c in 'wax+')) or flags & (
                    os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                path_check(path)
        elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.utime'):
            path_check(args[0])
        elif event in ('os.rename', 'os.link'):
            path_check(args[0]); path_check(args[1])
        elif event == 'os.symlink':
            path_check(args[0]); path_check(args[1])
        elif event == 'subprocess.Popen':
            executable, command, cwd, env = args
            if isinstance(command, str) and os.name == 'nt':
                command = [word.strip('"') for word in shlex.split(command, posix=False)]
            if not isinstance(command, (list, tuple)) or not command:
                raise PermissionError('SHELL_OR_UNKNOWN_SUBPROCESS')
            if Path(str(executable or command[0])).name.lower() not in ('git', 'git.exe'):
                raise PermissionError('CHILD_PROCESS_DENIED')
            words = list(command[1:])
            if words[:1] == ['-c']:
                if not words[1].startswith('safe.directory='):
                    raise PermissionError('GIT_CONFIG_DENIED')
                words = words[2:]
            if len(words) < 3 or words[0] != '-C':
                raise PermissionError('GIT_SCOPE_REQUIRED')
            repo = Path(words[1]).absolute()
            if repo not in (GEN, GOV) and not repo.is_relative_to(scratch):
                raise PermissionError('GIT_REPOSITORY_DENIED')
            if words[2] not in ('show', 'log', 'rev-parse'):
                raise PermissionError('GIT_MUTATION_DENIED')
    sys.addaudithook(audit)

def load_file(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

def worker(name, scratch):
    install_guard(Path(scratch))
    # Prove denial before importing any selected test module.
    denied = 0
    for action in [lambda: (ROOT / 'CANONICAL_WRITE_PROBE').write_bytes(b'forbidden'),
                   lambda: socket.getaddrinfo('example.invalid', 443),
                   lambda: subprocess.run([GIT, '-C', str(GEN), 'commit', '-m', 'forbidden'])]:
        try:
            action()
        except PermissionError:
            denied += 1
    if denied != 3:
        raise RuntimeError('ENFORCEMENT_NEGATIVE_CHECK_FAILED')
    if name == 'dependencies':
        checker = load_file(GOV / 'tools/check_runtime_dependencies.py', 'pin_check')
        result = checker.check(GOV / 'runtime/requirements-m2.txt')
        print(json.dumps(result, indent=2))
        return 0 if result['conformant'] else 2
    if name == 'local-preparation':
        module = load_file(ROOT / '.codex/sciv_delivery.py', 'local_delivery_tests')
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(module.Tests)
    else:
        directory, modules = SUITES[name]
        sys.path[:0] = [str(directory), str(GOV / 'runtime'), str(GOV / 'tools')]
        suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
    selected = unittest.TestSuite(t for t in flatten(suite)
                                 if t.id().split('.')[-1] not in EXCLUDED)
    result = unittest.TextTestRunner(verbosity=2).run(selected)
    print(json.dumps({'tests_run': result.testsRun, 'failures': len(result.failures),
                      'errors': len(result.errors), 'skips': len(result.skipped),
                      'negative_effect_checks_denied': denied}))
    return 0 if result.wasSuccessful() else 1

def run(token):
    pin = STAGE / 'security-preflight-r03.json'
    if sha(pin.read_bytes()) != token:
        raise RuntimeError('PREFLIGHT_TOKEN_MISMATCH')
    report = json.loads(pin.read_bytes())
    for relative, expected in report['source_sha256'].items():
        if sha((ROOT / relative).read_bytes()) != expected:
            raise RuntimeError('VALIDATED_SOURCE_CHANGED:' + relative)
    before = snapshot()
    if sha(json.dumps(before, sort_keys=True).encode()) != report['canonical_snapshot_sha256']:
        raise RuntimeError('CANONICAL_OR_DEPENDENCY_SNAPSHOT_CHANGED')
    destination = clean_path(STAGE / 'results-guarded-r01', STAGE)
    destination.mkdir(exist_ok=False)
    env = {k: v for k, v in os.environ.items() if k.upper() in
           ('SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'COMSPEC')}
    env.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', GIT_OPTIONAL_LOCKS='0',
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    summary = []
    for name in ['dependencies', 'local-preparation', *SUITES]:
        scratch = destination / (name + '-scratch')
        scratch.mkdir()
        process = subprocess.run([str(PY), '-B', str(Path(__file__)), '--worker', name,
                                  '--scratch', str(scratch)], cwd=ROOT, env=env,
                                 capture_output=True, encoding='utf-8', timeout=120)
        output = process.stdout + process.stderr
        with (destination / (name + '.log')).open('x', encoding='utf-8') as stream:
            stream.write(output)
        summary.append({'suite': name, 'exit_code': process.returncode})
        print(json.dumps(summary[-1]), flush=True)
    unchanged = snapshot() == before
    summary.append({'canonical_and_dependency_bytes_and_index_unchanged': unchanged})
    with (destination / 'summary.json').open('x', encoding='utf-8') as stream:
        json.dump(summary, stream, indent=2)
    if not unchanged:
        raise RuntimeError('POST_RUN_SNAPSHOT_CHANGED')
    return 0 if all(item.get('exit_code', 0) == 0 for item in summary) else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--run', metavar='PREFLIGHT_SHA256')
    parser.add_argument('--worker')
    parser.add_argument('--scratch')
    args = parser.parse_args()
    if args.preflight:
        preflight()
    elif args.worker:
        sys.exit(worker(args.worker, args.scratch))
    elif args.run:
        sys.exit(run(args.run))
    else:
        parser.error('explicit mode required')
