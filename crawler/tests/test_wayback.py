from afterlife.wayback import changed

URL = "https://straight2spam.xyz/"


def test_a_repurposed_home_page_is_spotted():
    then = ("20200101000000", "Straight2Spam - disposable email")
    assert changed(then, "A pollinator garden blog", URL)


def test_a_home_page_that_kept_its_name_is_fine():
    then = ("20200101000000", "FreedomBox Private Cloud Server")
    assert not changed(
        then, "Overview | FreedomBox Private Cloud Server", "https://freedombox.org/"
    )


def test_no_capture_or_no_title_means_no_verdict():
    assert not changed(None, "Anything", URL)
    assert not changed(("20200101000000", ""), "Anything", URL)
    assert not changed(("20200101000000", "Something"), "", URL)
