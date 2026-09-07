from types import SimpleNamespace
import pytest
from app.services import local_ai

@pytest.mark.asyncio
async def test_cpu_runtime_can_be_ready_without_vlm(monkeypatch, tmp_path):
    emb=tmp_path/'emb'; emb.mkdir(); (emb/'x').write_text('x')
    rer=tmp_path/'rer'; rer.mkdir(); (rer/'x').write_text('x')
    cfg=SimpleNamespace(
        inference_runtime='cpu', air_gapped_mode=True,
        llm_base_url='http://model-server:8000/v1', llm_model='mgc-local-cpu', llm_api_key='k',
        vlm_base_url='', vlm_model='', vlm_api_key='', embedding_model=str(emb), reranker_model=str(rer), reranker_enabled=True,
        local_inference_allowed_host_set={'model-server','localhost','127.0.0.1'}
    )
    monkeypatch.setattr(local_ai,'get_settings',lambda:cfg)
    async def fake_server(base, model, key):
        if not base: return {'configured':False,'reachable':False,'expected_model':model}
        return {'configured':True,'reachable':True,'expected_model':model,'models':[model],'expected_model_present':True}
    monkeypatch.setattr(local_ai,'_server_state',fake_server)
    status=await local_ai.local_ai_status()
    assert status['inference_runtime']=='cpu'
    assert status['ready'] is True
    assert status['vlm']['configured'] is False
