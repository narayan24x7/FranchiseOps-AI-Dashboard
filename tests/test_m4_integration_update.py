from pathlib import Path
import pandas as pd
import pytest
from src.milestone4.notebook_preparation import clean_and_validate


def test_notebook_cleaning_and_missing_m4_are_visible(tmp_path):
    path = tmp_path / 'input.xlsx'
    pd.DataFrame({'Outlet_ID':[' A ', ' A '], 'SKU_ID':['S', 'S'],
                  'Campaign_ID':['C', 'C'], 'Month':['2026-01', '2026-01'],
                  'Orders':[4, 4], 'Conversion_Rate_%':[50, 50]}).to_excel(path, index=False)
    data, checks = clean_and_validate(path, require_m4=False)
    assert len(data) == 1
    assert data.iloc[0].Outlet_ID == 'A'
    assert any(c['Status']=='Warning' and 'required columns' in c['Check'] for c in checks)
    _, strict = clean_and_validate(path, require_m4=True)
    assert any(c['Status']=='Failed' and 'required columns' in c['Check'] for c in strict)


def test_notebook_rejects_blank_ids_and_invalid_months(tmp_path):
    path = tmp_path / 'input.xlsx'
    pd.DataFrame({'Outlet_ID':[' '], 'SKU_ID':['S'], 'Campaign_ID':['C'],
                  'Month':['bad'], 'Orders':[-1]}).to_excel(path, index=False)
    _, checks = clean_and_validate(path, require_m4=False)
    failed = [c['Check'] for c in checks if c['Status']=='Failed']
    assert any('Outlet_ID complete' in c for c in failed)
    assert any('valid months' in c for c in failed)
    assert any('Orders nonnegative' in c for c in failed)


def test_orchestrator_persists_fresh_outputs_before_intelligence(tmp_path, monkeypatch):
    import src.orchestrator.orchestrator as module
    import intelligence.franchise_intelligence as adapter
    expected = pd.DataFrame({'Outlet_ID':['CURRENT']})
    monkeypatch.setattr(module, 'PROCESSED_DIR', tmp_path)
    for name in ['load_inventory_data', 'load_data', 'run_audit']:
        monkeypatch.setattr(module, name, lambda: expected.copy())
    for name in ['build_inventory_agent_output', 'build_marketing_agent_output']:
        monkeypatch.setattr(module, name, lambda data: data)
    calls = []
    monkeypatch.setattr(adapter, 'prepare_engine_inputs', lambda audit: calls.append('prepared'))
    def build():
        assert calls == ['prepared']
        for name in ['inventory', 'marketing']:
            assert pd.read_csv(tmp_path / f'{name}_agent_output.csv').Outlet_ID.tolist()==['CURRENT']
        expected.to_csv(tmp_path / 'intelligence_output.csv', index=False)
    monkeypatch.setattr(module, 'build_intelligence', build)
    result = module.AgentOrchestrator().run()
    assert set(result)=={'Inventory Agent','Marketing Agent','Audit Agent','Franchise Intelligence Engine'}
    assert result['Franchise Intelligence Engine'].Outlet_ID.tolist()==['CURRENT']
