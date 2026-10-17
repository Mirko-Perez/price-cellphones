from pricecomp.normalization.matcher import offer_matches, parse_phone


def test_parse_ram_storage():
    p = parse_phone("Samsung Galaxy S24 8/256GB")
    assert (p.brand, p.ram_gb, p.storage_gb) == ("samsung", 8, 256)
    assert p.model == "Galaxy S24"


def test_parse_storage_only_and_iphone():
    p = parse_phone("iPhone 15 128 GB")
    assert p.brand == "apple" and p.storage_gb == 128 and p.model == "iPhone 15"


def test_offer_matching():
    phone = parse_phone("Samsung Galaxy S24 256GB")
    assert offer_matches(phone, "Samsung Galaxy S24 256 GB Dual Sim 5G")
    assert not offer_matches(phone, "Samsung Galaxy S24 Ultra 256GB")
    assert not offer_matches(phone, "Samsung Galaxy S24 128GB")
    assert not offer_matches(phone, "Samsung Galaxy S23 256GB")


def test_parse_supplier_names():
    p = parse_phone("SAMSUNG S25FE (8/256GB)")
    assert (p.brand, p.model, p.ram_gb, p.storage_gb) == ("samsung", "S25 FE", 8, 256)
    p = parse_phone("SAMSUNG A07 (4/64GB) (NACIONAL)")
    assert p.model == "A07" and p.storage_gb == 64
    assert offer_matches(parse_phone("SAMSUNG S25FE (8/256GB)"), "SAMSUNG Galaxy S25 FE 256 GB")
