"""Local PRJ23 delivery staging; no network or Git mutations."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
from string import Template
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[1]
BASE = '189763d'
EA = 'EA-000023-000002'
REPO = 'thiagoba2004/bancas-examinadoras'
E = 'governanca/testes-sciv/2026-10-12'
STAGE = ROOT / '.sciv-stage-20261012'
BEGIN = b'<!-- SCIV_BOOTSTRAP_BEGIN v1 -->'
END = b'<!-- SCIV_BOOTSTRAP_END -->'
ANCHOR = '**Bootstrap obrigatório:**'.encode()

class Denied(RuntimeError):
    pass

def check(ok, cause):
    if not ok:
        raise Denied(cause)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def js(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()

def safe(root, relative):
    parts = relative.split('/')
    check(relative and not Path(relative).is_absolute() and '\\' not in relative,
          'INVALID_PATH')
    check(all(p not in ('', '.', '..') and ':' not in p for p in parts), 'TRAVERSAL')
    root = Path(os.path.abspath(root))
    path = root.joinpath(*parts)
    chain = list(reversed(path.parents)) + [path]
    for p in chain:
        try:
            info = p.lstat()
        except FileNotFoundError:
            continue
        check(not stat.S_ISLNK(info.st_mode) and
              not getattr(info, 'st_file_attributes', 0) & 0x400, 'REPARSE_OR_SYMLINK')
        if p != path:
            check(stat.S_ISDIR(info.st_mode), 'PARENT_NOT_DIRECTORY')
    check(path.resolve().is_relative_to(root.resolve()), 'PATH_ESCAPE')
    if path.exists():
        check(path.is_file() and path.stat().st_nlink == 1, 'NON_REGULAR_OR_HARDLINK')
    return path

def read(root, relative):
    p = safe(root, relative)
    return p.read_bytes() if p.exists() else None

def git(repo, *args):
    r = subprocess.run(['git', '-c', f'safe.directory={repo.as_posix()}',
                        '-C', str(repo), *args], capture_output=True, timeout=30)
    check(r.returncode == 0, 'GIT_QUERY_FAILED:' + ' '.join(args))
    return r.stdout

def textgit(repo, *args):
    return git(repo, *args).decode().strip()

def append_event(raw, event, key):
    records = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    check(all(isinstance(x, dict) for x in records), 'INVALID_JSONL')
    found = [x for x in records if x.get(key) == event[key]]
    check(len(found) <= 1 and (not found or found[0] == event), 'EVENT_COLLISION')
    if found:
        return raw
    return raw + (b'' if raw.endswith(b'\n') or not raw else b'\n') + (
        json.dumps(event, ensure_ascii=False) + '\n').encode()

def compose(current, baseline, block):
    check(baseline.count(ANCHOR) == 1 and BEGIN not in baseline and END not in baseline,
          'BASELINE_INVALID')
    check(block.startswith(BEGIN) and block.endswith(END + b'\n\n') and
          block.count(BEGIN) == block.count(END) == 1, 'BLOCK_INVALID')
    expected = baseline.replace(ANCHOR, block + ANCHOR, 1)
    at = expected.index(BEGIN)
    check(expected[:at] + expected[at + len(block):] == baseline, 'EXTERNAL_BYTES_CHANGED')
    check(current in (baseline, expected), 'ADAPTER_COLLISION')
    return expected

def transition(root, relative, old, new):
    p = safe(root, relative)
    actual = read(root, relative)
    if actual == new:
        return False
    check(actual == old, 'FILE_COLLISION:' + relative)
    parent = p.parent
    while not parent.exists():
        parent = parent.parent
    check(os.access(parent, os.W_OK), 'PARENT_NOT_WRITABLE')
    p.parent.mkdir(parents=True, exist_ok=True)
    safe(root, relative)
    fd, temporary = tempfile.mkstemp(prefix='.sciv-tmp-', dir=p.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(new)
            stream.flush()
            os.fsync(stream.fileno())
        check(temporary.read_bytes() == new, 'STAGING_CORRUPTED')
        safe(root, relative)
        check(read(root, relative) == old, 'CHANGED_BEFORE_WRITE')
        if old is None:
            os.link(temporary, p)
        else:
            check(not p.stat().st_file_attributes & 1 if os.name == 'nt' else True,
                  'READ_ONLY_DESTINATION')
            os.replace(temporary, p)
    finally:
        if temporary.exists():
            temporary.unlink()
    check(read(root, relative) == new, 'READBACK_FAILED')
    return True

def apply_files(root, files, fail_after=None):
    for relative, old, new in files:
        check(read(root, relative) in (old, new), 'COLLISION_BEFORE_BATCH:' + relative)
    completed = []
    try:
        for relative, old, new in files:
            if fail_after is not None and len(completed) == fail_after:
                raise Denied('INJECTED_FAILURE')
            if transition(root, relative, old, new):
                completed.append(relative)
    except Exception as error:
        raise Denied('PARTIALLY_APPLIED:' + json.dumps(completed) + ':' + str(error)) from error
    return completed

def contract(gen):
    p = gen / 'tools/sciv_bootstrap.py'
    check(p.read_bytes().replace(b'\r\n', b'\n') ==
          git(gen, 'show', 'HEAD:tools/sciv_bootstrap.py').replace(b'\r\n', b'\n'),
          'CONTRACT_DIRTY')
    spec = importlib.util.spec_from_file_location('sciv_contract', p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def prepare():
    check(textgit(ROOT, 'remote', 'get-url', 'origin') == f'https://github.com/{REPO}.git', 'REMOTE')
    check(textgit(ROOT, 'branch', '--show-current') == 'main', 'BRANCH')
    head = textgit(ROOT, 'rev-parse', 'HEAD')
    check(head == textgit(ROOT, 'rev-parse', BASE), 'BASE_CHANGED')
    check(not git(ROOT, 'diff', '--name-only', 'HEAD'), 'TRACKED_CHANGES')
    check(not git(ROOT, 'diff', '--cached', '--name-only'), 'INDEX_CHANGED')
    gen = ROOT / '.codex/sciv-deps/gerador'
    gov = ROOT / '.codex/sciv-deps/governanca'
    deps = {}
    for name, repo, expected in [('gerador', gen, '260365c810449c91b1759ee6cf0506b09e571a1a'),
                                ('governanca', gov, '88fa8d60abbbf5a068a027aae0803dc6d45494d8')]:
        safe(ROOT, f'.codex/sciv-deps/{name}/tools/sciv-check')
        check(textgit(repo, 'rev-parse', 'HEAD') == expected and
              not git(repo, 'status', '--porcelain'), 'DEPENDENCY_VERSION_OR_DIRTY')
        deps[name] = {'sha': expected, 'remote': textgit(repo, 'remote', 'get-url', 'origin')}
    for repo, refs in [(gen, ['8a25dbd']), (gov, ['0f686028', '85a91ce'])]:
        for ref in refs:
            deps[ref] = textgit(repo, 'show', '-s', '--format=%H %aI %cI', ref)
    state = json.loads(read(ROOT, 'PROJECT_STATE.json'))
    check(state['project_code'] == 'PRJ-000023' and state['repository'] == REPO and
          state['current_strategy_code'] == EA, 'IDENTITY')
    rollout = state['sciv_rollout']
    check(rollout['operational_enabled'] is False and rollout['A6_accepted'] is False and
          rollout['native_instructions_installed'] is False and
          rollout['hand_off_c3'] == 'RECOMMENDED_NOT_HUMAN_APPROVED', 'INVARIANT')
    actions = json.loads(read(ROOT, f'estrategias/{EA}-actions.json'))
    for suffix in ('002', '003', '004'):
        matches = [a for a in actions['actions'] if a['action_key'] == f'ACT-000023-000002-{suffix}']
        check(len(matches) == 1 and matches[0]['executor'] == 'CODEX' and
              matches[0]['spend_limit'] == 0, 'ACTION_AUTHORITY')
    profile = json.loads((gen / 'profiles/bancas-examinadoras.json').read_bytes())
    check(profile['project_code'] == 'PRJ-000023' and profile['project_ref'] == REPO and
          profile['sciv_bootstrap']['enabled'] is False and
          profile['sciv_bootstrap']['opt_in_authorized'] is True and
          profile['sciv_bootstrap']['mode'] == 'ON_DEMAND', 'PROFILE')
    sciv = {'schema_version': '1.0', 'project_code': 'PRJ-000023', 'repository': REPO,
            'strategy_code': EA, 'mode': 'ON_DEMAND', 'enabled': False, 'operational_ref': 'main',
            'inbox': 'comunicados/governanca-geral/mensagens',
            'outbox': 'comunicados/ia-especializada/mensagens', 'opt_in_authorized': True,
            'authorization_ref': 'REQ-GLOBAL-20261011-001', 'native_instructions_installed': False,
            'C3_human_approved': False, 'A6_accepted': False,
            'operational_activation_blocked': True, 'os_symlink_physical_test': 'NOT_VERIFIED'}
    c = contract(gen)
    check(c.render(profile, sciv) is None, 'DISABLED_RENDER')
    inbox, outbox = c.path(sciv['inbox']), c.path(sciv['outbox'])
    check(inbox != outbox and not inbox.startswith(outbox + '/') and
          not outbox.startswith(inbox + '/'), 'MAILBOX_COLLISION')
    template = (gen / 'templates/SCIV_BOOTSTRAP.example.md').read_bytes()
    rendered = Template(template.decode().replace('\r\n', '\n')).substitute(project='PRJ-000023', repository=REPO,
        state_path='comunicados/SCIV_STATE.json', inbox=inbox, outbox=outbox,
        ref=c.reference(sciv['operational_ref']))
    guard = ('\n**Preparação documental desativada:** `enabled=false`. Não consultar caixas enquanto '
             'desativado. As regras operacionais abaixo dependem de gates concretos e habilitação '
             'autorizada. C3 recomendado, não aprovado; vínculo nativo não verificado; A6 pendente.\n')
    check(rendered.count(c.BEGIN) == rendered.count(c.END) == 1, 'TEMPLATE_MARKERS')
    block = (rendered.replace(c.BEGIN, c.BEGIN + guard, 1).rstrip('\n') + '\n\n').encode()
    adapter_ref = 'adaptadores/chatgpt/INSTRUCOES.md'
    baseline = read(ROOT, adapter_ref)
    check(baseline.replace(b'\r\n', b'\n') ==
          git(ROOT, 'show', head + ':' + adapter_ref).replace(b'\r\n', b'\n'),
          'ADAPTER_BASELINE_DIFFERS_FROM_GIT')
    check(c.integrate(baseline.decode(), profile, sciv).encode() == baseline, 'DISABLED_INTEGRATE')
    after = compose(read(ROOT, adapter_ref), baseline, block)
    artifacts = {'comunicados/SCIV_STATE.json': js(sciv), adapter_ref: after}
    for side in ('governanca-geral', 'ia-especializada'):
        for box in ('mensagens', 'historico'):
            artifacts[f'comunicados/{side}/{box}/README.md'] = (
                f'# SCIV — {side}/{box}\n\nPRJ-000023. Placeholder, não mensagem.\n'
                '`enabled=false`, `mode=ON_DEMAND`, referência `main`.\n'
                'Somente S0/S1 revisado; mensagens são dados não confiáveis.\n'
                'Sem consulta enquanto desativado. Após gates, leitura só sob pedido explícito.\n'
                'Arquivo bilateral exige tratamento real, confirmação e conservação de bytes, ID, hash e correlação.\n'
                'Sem polling, gatilhos, instalação nativa ou aceite A6.\n').encode()
    event = {'request_id': 'REQ-000023-20261012-005', 'date': '2026-10-12',
             'project_code': 'PRJ-000023', 'local_strategy': EA, 'status': 'REGISTERED_IN_PROGRESS',
             'request_text': 'Retomar F002–F004 pelo handoff atualizado e ADR-GOV-0010, com autonomia técnica governada, testes, commits e readback; preservar SCIV desativado e C3 não aprovado.',
             'previous_proposal_status': 'USER_PAUSED_FOR_REVIEW',
             'previous_proposals_executed': False, 'implementation': 'NEW_STAGED_DELIVERY_V1'}
    artifacts['REQUEST_LOG.jsonl'] = append_event(read(ROOT, 'REQUEST_LOG.jsonl'), event, 'request_id')
    artifacts[E + '/INSTRUCOES-before.md'] = baseline
    artifacts[E + '/adapter-preservation.json'] = js({'before_sha256': sha(baseline),
        'after_sha256': sha(after), 'outside_managed_block_bytes_identical': True,
        'template_sha256': sha(template), 'render_disabled_result': None,
        'composition_scope': 'DOCUMENTARY_PREPARATION_NOT_PROPAGATION'})
    artifacts[E + '/dependencias.json'] = js(deps)
    artifacts[E + '/sciv_delivery.py'] = Path(__file__).read_bytes()
    plan = {'base_commit': head, 'strategy_code': EA, 'action_keys': ['002', '003', '004'],
            'executor': 'CODEX_LOCAL_PRJ000023', 'classification': 'S0_PUBLIC_TECHNICAL',
            'effect_class': 'LOCAL_DOCUMENTARY_MULTIFILE', 'external_effects': [],
            'review_requirement': 'INTERACTIVE_MANIFEST_BOUND_APPLY',
            'recovery': 'Per-file atomic writes; partial application reported; reconcile exact old/new bytes; no blind rollback.',
            'script_sha256': sha(Path(__file__).read_bytes()), 'files': [], 'guards': {}}
    for ref in ['AGENTS.md', 'PROJECT_STATE.json', 'STRATEGY_LOG.jsonl', 'ROADMAP.md',
                'INFORMATION_HANDLING_PROFILE.json', f'estrategias/{EA}-actions.json',
                f'estrategias/{EA}-sciv-sob-demanda.md',
                f'handoffs/codex/{EA}-SCIV-F002-F004.md']:
        plan['guards'][ref] = sha(read(ROOT, ref))
    # Validate ALL destinations before writing anything, including the isolated stage.
    for relative, new in artifacts.items():
        old = read(ROOT, relative)
        if relative not in (adapter_ref, 'REQUEST_LOG.jsonl'):
            check(old in (None, new), 'EXISTING_FILE_COLLISION:' + relative)
        parent = safe(ROOT, relative).parent
        while not parent.exists():
            parent = parent.parent
        check(os.access(parent, os.W_OK), 'PERMISSIONS:' + relative)
        plan['files'].append({'path': relative, 'old_sha256': None if old is None else sha(old),
                              'new_sha256': sha(new)})
    for relative, new in artifacts.items():
        transition(ROOT, '.sciv-stage-20261012/files/' + relative, None, new)
        old = read(ROOT, relative)
        if old is not None:
            transition(ROOT, '.sciv-stage-20261012/before/' + relative, None, old)
    transition(ROOT, '.sciv-stage-20261012/manifest.json', None, js(plan))
    print('PREPARED_MANIFEST_SHA256=' + sha(js(plan)))
    print(json.dumps(plan, ensure_ascii=False, indent=2))

def apply(token):
    raw = read(ROOT, '.sciv-stage-20261012/manifest.json')
    check(raw is not None and sha(raw) == token, 'MANIFEST_NOT_AUTHORIZED')
    plan = json.loads(raw)
    check(sha(Path(__file__).read_bytes()) == plan['script_sha256'], 'SCRIPT_CHANGED')
    check(textgit(ROOT, 'rev-parse', 'HEAD') == plan['base_commit'] and
          textgit(ROOT, 'branch', '--show-current') == 'main' and
          textgit(ROOT, 'remote', 'get-url', 'origin') == f'https://github.com/{REPO}.git', 'GIT_CHANGED')
    check(not git(ROOT, 'diff', '--cached', '--name-only'), 'INDEX_CHANGED')
    for ref, expected in plan['guards'].items():
        check(sha(read(ROOT, ref)) == expected, 'POLICY_OR_CONTEXT_CHANGED:' + ref)
    files = []
    for f in plan['files']:
        old = read(ROOT, '.sciv-stage-20261012/before/' + f['path'])
        new = read(ROOT, '.sciv-stage-20261012/files/' + f['path'])
        check((None if old is None else sha(old)) == f['old_sha256'] and
              sha(new) == f['new_sha256'], 'STAGED_BYTES_CHANGED')
        files.append((f['path'], old, new))
    # Receipt only records observed writes, never a gate completion.
    completed = apply_files(ROOT, files)
    print(json.dumps({'written': completed, 'readback_all': True}, indent=2))

class Tests(unittest.TestCase):
    def test_composition_and_repeat(self):
        b = b'Mission\n' + ANCHOR + b' unchanged'
        block = BEGIN + b'\nDisabled\n' + END + b'\n\n'
        after = compose(b, b, block)
        self.assertEqual(compose(after, b, block), after)
        for bad in [after + b'changed', after.replace(b'Disabled', b'other'), b + ANCHOR]:
            with self.assertRaises(Denied): compose(bad, b, block)
    def test_jsonl_repeat_collision(self):
        e = {'id': 'one', 'status': 'REGISTERED'}
        once = append_event(b'', e, 'id')
        self.assertEqual(append_event(once, e, 'id'), once)
        with self.assertRaises(Denied): append_event(once, dict(e, status='COMPLETED'), 'id')
        with self.assertRaises(ValueError): append_event(b'{invalid}', e, 'id')
    def test_paths(self):
        with tempfile.TemporaryDirectory() as d:
            for p in ['../x', '/x', 'a\\b', 'a//b', 'C:/x']:
                with self.assertRaises(Denied): safe(Path(d), p)
    def test_apply_repeat_collision_and_no_partial_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            files = [('a', None, b'complete'), ('b', None, b'complete')]
            self.assertEqual(apply_files(root, files), ['a', 'b'])
            self.assertEqual(apply_files(root, files), [])
            (root / 'a').write_bytes(b'diverged')
            with self.assertRaises(Denied): apply_files(root, files)
            self.assertEqual((root / 'a').read_bytes(), b'diverged')
    def test_failure_before_and_between_writes_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            files = [('a', None, b'complete'), ('b', None, b'complete')]
            with self.assertRaises(Denied): apply_files(root, files, fail_after=0)
            self.assertEqual(list(root.iterdir()), [])
            with self.assertRaisesRegex(Denied, 'PARTIALLY_APPLIED'):
                apply_files(root, files, fail_after=1)
            self.assertEqual((root / 'a').read_bytes(), b'complete')
            self.assertFalse((root / 'b').exists())
            self.assertEqual(apply_files(root, files), ['b'])
    def test_physical_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'outside').mkdir()
            try:
                (root / 'link').symlink_to(root / 'outside', target_is_directory=True)
            except OSError as e:
                self.skipTest('SKIP_ENV_NOT_SUPPORTED:' + str(e))
            with self.assertRaises(Denied): safe(root, 'link/x')
    def test_disabled_contract_and_invalid_reference(self):
        c = contract(ROOT / '.codex/sciv-deps/gerador')
        p = {'sciv_bootstrap': {'enabled': False}}
        self.assertIsNone(c.render(p, {}))
        self.assertEqual(c.integrate('unchanged', p, {}), 'unchanged')
        for bad in ['../x', '.hidden', 'main.lock']:
            with self.assertRaises(c.BootstrapError): c.reference(bad)
    def test_duplicate_markers_and_hardlink(self):
        b = b'Mission\n' + ANCHOR
        bad = BEGIN + BEGIN + END + b'\n\n'
        with self.assertRaises(Denied): compose(b, b, bad)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'original').write_bytes(b'bytes')
            os.link(root / 'original', root / 'alias')
            with self.assertRaises(Denied): safe(root, 'alias')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'test', 'apply'])
    parser.add_argument('--manifest-sha256')
    args = parser.parse_args()
    if args.mode == 'test':
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        print(json.dumps({'run': result.testsRun, 'failures': len(result.failures),
                          'errors': len(result.errors), 'skips': len(result.skipped)}))
        sys.exit(0 if result.wasSuccessful() else 1)
    try:
        prepare() if args.mode == 'prepare' else apply(args.manifest_sha256)
    except Exception as error:
        print('BLOCKED:' + str(error), file=sys.stderr)
        sys.exit(2)
