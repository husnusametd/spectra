"""Bu geçici test dosyası, pytest koleksiyon hatasını (exit code 5: no tests ran) engeller.
Gerçek birim testleri eklendikçe bu dosya kaldırılacaktır."""


def test_ci_smoke():
    """Basit smoke test; her zaman geçer."""
    assert True
