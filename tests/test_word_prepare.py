import hashlib
from zipfile import ZipFile
import pytest
from endnote_mcp.word.prepare import prepare_conversion

def fixture(tmp_path):
    source=tmp_path/'source.docx'
    with ZipFile(source,'w') as z:
        z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Example [1].</w:t></w:r></w:p><w:p><w:r><w:t>Literal reference</w:t></w:r></w:p></w:body></w:document>')
        z.writestr('word/comments.xml',b'fictional comments')
        z.writestr('word/_rels/document.xml.rels',b'fictional relationships')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    plan={'source_sha256':digest,'citations':[{'paragraph_index':0,'run_index':0,'original_text':'[1]','temporary_token':'{Example, 2020 #7}','database_id':'fictional','native_record_id':7}], 'bibliography_paragraphs':[{'paragraph_index':1,'original_text':'Literal reference','remove':True}]}
    return source,digest,plan

def test_preserve_package_and_source(tmp_path):
    s,h,p=fixture(tmp_path);d=tmp_path/'new.docx'
    r=prepare_conversion(s,d,p,h)
    assert r['stage']=='prepared' and not r['native_fields_created']
    assert hashlib.sha256(s.read_bytes()).hexdigest()==h
    with ZipFile(s) as a,ZipFile(d) as b:
        for n in a.namelist():
            if n!='word/document.xml': assert a.read(n)==b.read(n)
        assert b'{Example, 2020 #7}' in b.read('word/document.xml')
        assert b'Literal reference' not in b.read('word/document.xml')

@pytest.mark.parametrize('failure',['existing','hash','duplicate','missing','revision','overlap'])
def test_rejections(tmp_path,failure):
    s,h,p=fixture(tmp_path);d=tmp_path/'new.docx'
    if failure=='existing': d.write_bytes(b'keep')
    if failure=='hash': h='0'*64
    if failure=='duplicate': p['citations']*=2
    if failure=='missing': p['citations'][0]['original_text']='absent'
    if failure in ('revision','overlap'):
        with ZipFile(s) as z: parts={n:z.read(n) for n in z.namelist()}
        old=b'<w:t>Example [1].</w:t>'
        new=b'<w:ins>'+old+b'</w:ins>' if failure=='revision' else b'<w:fldChar w:fldCharType="begin"/>'+old+b'<w:fldChar w:fldCharType="end"/>'
        parts['word/document.xml']=parts['word/document.xml'].replace(old,new)
        with ZipFile(s,'w') as z:
            for n,v in parts.items(): z.writestr(n,v)
        h=hashlib.sha256(s.read_bytes()).hexdigest();p['source_sha256']=h
    with pytest.raises(ValueError): prepare_conversion(s,d,p,h)
    if failure!='existing': assert not d.exists()

def test_preserve_unedited_table_and_fields(tmp_path):
    s,h,p=fixture(tmp_path)
    with ZipFile(s) as z: parts={n:z.read(n) for n in z.namelist()}
    extra=b'<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table stays</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:p><w:r><w:fldChar w:fldCharType="begin"/><w:instrText> REF bookmark </w:instrText><w:fldChar w:fldCharType="separate"/><w:t>9</w:t><w:fldChar w:fldCharType="end"/></w:r></w:p>'
    parts['word/document.xml']=parts['word/document.xml'].replace(b'</w:body>',extra+b'</w:body>')
    with ZipFile(s,'w') as z:
        for n,v in parts.items(): z.writestr(n,v)
    h=hashlib.sha256(s.read_bytes()).hexdigest();p['source_sha256']=h
    d=tmp_path/'new.docx';prepare_conversion(s,d,p,h)
    with ZipFile(d) as z:
        assert extra in z.read('word/document.xml')

@pytest.mark.parametrize('change',['ambiguous','unauthorized_bib','wrong_bib','bad_index','symlink'])
def test_more_preflight_guards(tmp_path,change):
    s,h,p=fixture(tmp_path);d=tmp_path/'new.docx'
    if change=='ambiguous':
        with ZipFile(s) as z: parts={n:z.read(n) for n in z.namelist()}
        parts['word/document.xml']=parts['word/document.xml'].replace(b'Example [1].',b'Example [1] [1].')
        with ZipFile(s,'w') as z:
            for n,v in parts.items(): z.writestr(n,v)
        h=hashlib.sha256(s.read_bytes()).hexdigest();p['source_sha256']=h
    if change=='unauthorized_bib': p['bibliography_paragraphs'][0]['remove']=False
    if change=='wrong_bib': p['bibliography_paragraphs'][0]['original_text']='Wrong'
    if change=='bad_index': p['citations'][0]['run_index']=-1
    if change=='symlink': d.symlink_to(s)
    with pytest.raises(ValueError): prepare_conversion(s,d,p,h)
    assert hashlib.sha256(s.read_bytes()).hexdigest()==h

def rewrite_source(source, plan, old, new):
    with ZipFile(source) as z: parts={n:z.read(n) for n in z.namelist()}
    parts['word/document.xml']=parts['word/document.xml'].replace(old,new)
    with ZipFile(source,'w') as z:
        for n,v in parts.items(): z.writestr(n,v)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    plan['source_sha256']=digest
    return digest

@pytest.mark.parametrize('same_record',[True,False])
def test_distinct_spans_and_repeated_authentic_token(tmp_path,same_record):
    s,h,p=fixture(tmp_path); d=tmp_path/'new.docx'
    h=rewrite_source(s,p,b'Example [1].',b'First [1], then [2].')
    second=dict(p['citations'][0],original_text='[2]')
    if not same_record:
        second.update(native_record_id=8,temporary_token='{Other, 2021 #8}')
    p['citations'].append(second)
    receipt=prepare_conversion(s,d,p,h)
    assert receipt['database_id']=='fictional'
    assert receipt['citation_bindings']==[{'database_id':c['database_id'],'native_record_id':c['native_record_id'],'temporary_token':c['temporary_token'],'paragraph_index':0,'run_index':0} for c in p['citations']]
    with ZipFile(d) as z:
        xml=z.read('word/document.xml').decode()
        assert 'First '+p['citations'][0]['temporary_token']+', then '+second['temporary_token']+'.' in xml

@pytest.mark.parametrize('record',[7,8])
def test_mixed_library_rejected(tmp_path,record):
    s,h,p=fixture(tmp_path); d=tmp_path/'new.docx'
    h=rewrite_source(s,p,b'Example [1].',b'First [1], then [2].')
    p['citations'].append(dict(p['citations'][0],original_text='[2]',database_id='other',native_record_id=record,temporary_token='{Other, 2021 #'+str(record)+'}'))
    with pytest.raises(ValueError,match='database'): prepare_conversion(s,d,p,h)
    assert not d.exists()

@pytest.mark.parametrize('fragment',[
    '<w:fldChar w:fldCharType="separate"/>',
    '<w:fldChar w:fldCharType="unknown"/>',
    '<w:fldChar w:fldCharType="begin"/><w:fldChar w:fldCharType="separate"/><w:fldChar w:fldCharType="separate"/><w:fldChar w:fldCharType="end"/>',
    '<w:instrText>ORPHAN</w:instrText>',
    '<w:fldData>ORPHAN</w:fldData>',
    '<w:fldChar w:fldCharType="begin"/><w:fldChar w:fldCharType="separate"/><w:instrText>LATE</w:instrText><w:fldChar w:fldCharType="end"/>',
    '<w:fldChar w:fldCharType="begin"/><w:instrText> ADDIN EN.JS.CITE </w:instrText><w:fldChar w:fldCharType="end"/>',
])
def test_all_malformed_field_phases_rejected(tmp_path,fragment):
    s,h,p=fixture(tmp_path); d=tmp_path/'new.docx'
    h=rewrite_source(s,p,b'</w:body>',('<w:p><w:r>'+fragment+'</w:r></w:p></w:body>').encode())
    with pytest.raises(ValueError): prepare_conversion(s,d,p,h)
    assert not d.exists()

def test_overlapping_spans_rejected(tmp_path):
    s,h,p=fixture(tmp_path);d=tmp_path/'new.docx'
    p['citations'].append(dict(p['citations'][0],original_text='Example [1]'))
    with pytest.raises(ValueError,match='overlap'): prepare_conversion(s,d,p,h)
    assert not d.exists()

def test_repeated_authentic_token_in_separate_paragraphs(tmp_path):
    s,h,p=fixture(tmp_path);d=tmp_path/'new.docx'
    h=rewrite_source(s,p,b'Literal reference',b'Again [1].')
    p['bibliography_paragraphs']=[]
    p['citations'].append(dict(p['citations'][0],paragraph_index=1))
    receipt=prepare_conversion(s,d,p,h)
    assert receipt['citation_count']==2
    with ZipFile(d) as z:
        assert z.read('word/document.xml').count(b'{Example, 2020 #7}')==2

def test_generic_code_only_field_preserved(tmp_path):
    s,h,p=fixture(tmp_path);d=tmp_path/'new.docx'
    fragment=b'<w:p><w:r><w:fldChar w:fldCharType="begin"/><w:instrText> DATE </w:instrText><w:fldChar w:fldCharType="end"/></w:r></w:p>'
    h=rewrite_source(s,p,b'</w:body>',fragment+b'</w:body>')
    prepare_conversion(s,d,p,h)
    with ZipFile(d) as z: assert fragment in z.read('word/document.xml')

def test_endnote_code_only_field_rejected(tmp_path):
    s,h,p=fixture(tmp_path);d=tmp_path/'new.docx'
    fragment=b'<w:p><w:r><w:fldChar w:fldCharType="begin"/><w:instrText> ADDIN EN.JS.CITE </w:instrText><w:fldChar w:fldCharType="end"/></w:r></w:p>'
    h=rewrite_source(s,p,b'</w:body>',fragment+b'</w:body>')
    with pytest.raises(ValueError,match='separator'): prepare_conversion(s,d,p,h)
    assert not d.exists()
