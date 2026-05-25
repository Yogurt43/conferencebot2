import config


def test_price_constants_exist():
    assert hasattr(config, 'PRICE_WITH_HOUSING')
    assert hasattr(config, 'PRICE_WITHOUT_HOUSING')


def test_price_values():
    assert config.PRICE_WITH_HOUSING == 175
    assert config.PRICE_WITHOUT_HOUSING == 100


def test_prices_are_integers():
    assert isinstance(config.PRICE_WITH_HOUSING, int)
    assert isinstance(config.PRICE_WITHOUT_HOUSING, int)
