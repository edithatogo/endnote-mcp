"""Portable adapters never imply native application execution."""
from pathlib import Path
import pytest
from endnote_mcp.word import tools
from endnote_mcp.config import Config


def test_status_without_configuration():
    result = tools.get_word_endnote_status()
    assert result['status'] == 'unqualified'
    assert result['native_backend_shipped'] is False
    assert result['native_update_available'] is False


def test_prepare_disabled(tmp_path):
    cfg = Config(tmp_path/'x', tmp_path, tmp_path/'db')
    result = tools.prepare_word_endnote_conversion('a','b','c','0'*64, config=cfg)
    assert result['status'] == 'blocked'
    assert not (tmp_path/'b').exists()


@pytest.mark.parametrize('kind', ['escape', 'symlink', 'existing', 'relative'])
def test_destination_guards(tmp_path, kind):
    root = tmp_path/'work'; root.mkdir()
    source = tmp_path/'source.docx'; source.write_bytes(b'fictional')
    dest = root/'out.docx'
    if kind == 'escape': dest = tmp_path/'outside.docx'
    if kind == 'symlink':
        (root/'link').symlink_to(tmp_path, target_is_directory=True)
        dest = root/'link'/'out.docx'
    if kind == 'existing': dest.write_bytes(b'preserve')
    if kind == 'relative': dest = Path('out.docx')
    cfg = Config(source,tmp_path,tmp_path/'db',native_working_root=root)
    result = tools.prepare_word_endnote_conversion(str(source),str(dest),'absent','0'*64,config=cfg)
    assert result['status'] == 'error'
    assert result['error_code'] == 'invalid_request'


def test_audit_error_does_not_disclose_text():
    result = tools.audit_word_endnote_document('/absent/secret manuscript.docx')
    assert result['status'] == 'error'
    assert 'secret' not in str(result)


def test_core_preparation_and_stale_hash(tmp_path):
    import json
    from test_word_prepare import fixture
    source, digest, plan = fixture(tmp_path)
    root = tmp_path/'working'; root.mkdir()
    plan_path = tmp_path/'plan.json'; plan_path.write_text(json.dumps(plan))
    cfg = Config(source,tmp_path,tmp_path/'db',native_working_root=root)
    dest = root/'quoted café.docx'
    bad = tools.prepare_word_endnote_conversion(str(source),str(dest),str(plan_path),'0'*64,config=cfg)
    assert bad['status'] == 'error' and not dest.exists()
    good = tools.prepare_word_endnote_conversion(str(source),str(dest),str(plan_path),digest,config=cfg)
    assert good['status'] == 'prepared' and good['source_sha256'] == digest
    assert not good['native_fields_created']
    assert good['destination_sha256']
    audit = tools.audit_word_endnote_document(str(dest))
    assert audit['stage'] == 'audited' and audit['docx_sha256'] == good['destination_sha256']


def test_audit_delegates_optional_inputs(tmp_path, monkeypatch):
    import json
    mapping = tmp_path/'map.json'; mapping.write_text(json.dumps({'records':[]}))
    observed = []
    def audit(*args):
        observed.extend(args)
        return {'passed':True,'docx_sha256':'fictional'}
    monkeypatch.setattr(tools,'audit_document',audit)
    result = tools.audit_word_endnote_document(str(tmp_path/'x.docx'), [[7]], str(mapping), 'author-date')
    assert observed[1:] == [[[7]], {'records':[]}, 'author-date']
    assert result['status'] == 'passed'


def test_timeout_is_not_completion(tmp_path, monkeypatch):
    def timeout(*args): raise TimeoutError('private text')
    monkeypatch.setattr(tools,'audit_document',timeout)
    result = tools.audit_word_endnote_document(str(tmp_path/'x.docx'))
    assert result['status'] == 'error'
    assert 'private text' not in str(result)


def test_config_requires_absolute_root_and_records_native_request(tmp_path, monkeypatch):
    import yaml
    path = tmp_path/'cfg.yaml'
    raw = {'endnote_xml':'x','pdf_dir':str(tmp_path),'native_word_enabled':True,
           'native_working_root':'relative'}
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError): Config.load(path)
    raw['native_working_root'] = str(tmp_path)
    path.write_text(yaml.safe_dump(raw))
    cfg = Config.load(path)
    assert cfg.native_word_enabled is True
    assert cfg.native_working_root == tmp_path
    monkeypatch.setenv("ENDNOTE_MCP_CONFIG", str(path))
    status = tools.get_word_endnote_status()
    assert status["native_word_requested"] is True
    assert status["native_word_effective"] is False
