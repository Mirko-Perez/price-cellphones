from pricecomp.scrapers.personal import _extract

HTML = '{"products":[]},"pagination":{"pageNumber":1,"totalPages":9},"products":[{"name":"A","price":10}]'


def test_extract_disambiguates_repeated_key():
    assert _extract(HTML, "pagination")["totalPages"] == 9
    assert _extract(HTML, "products") == []
    assert _extract(HTML, "products", after="pagination") == [{"name": "A", "price": 10}]
