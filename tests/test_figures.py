from patterns.notice_relevance import check_rewrite

ORIG = "Pay $1,284.50 by November 15, 2026 at 12 Elm Road. A 1.5% penalty applies. Homeowners only."
KEEP = ("$1,284.50", "November 15, 2026", "12 Elm Road", "Homeowners only")


def test_faithful_rewrite_passes():
    rw = "You must pay $1,284.50 by November 15, 2026. Go to 12 Elm Road. You pay 1.5% more if late. Homeowners only."
    assert check_rewrite(ORIG, rw, KEEP).ok


def test_changed_date_is_rejected():
    rw = "You must pay $1,284.50 by November 25, 2026. Go to 12 Elm Road. 1.5% penalty. Homeowners only."
    r = check_rewrite(ORIG, rw, KEEP)
    assert not r.ok
    assert "november 15, 2026" in r.missing and "november 25, 2026" in r.extra


def test_changed_month_same_day_is_rejected():
    rw = "Pay $1,284.50 by December 15, 2026 at 12 Elm Road. 1.5% penalty. Homeowners only."
    assert not check_rewrite(ORIG, rw, KEEP).ok


def test_changed_amount_is_rejected():
    rw = "Pay $1,248.50 by November 15, 2026 at 12 Elm Road. 1.5% penalty. Homeowners only."
    assert not check_rewrite(ORIG, rw, KEEP).ok


def test_dropped_eligibility_rule_is_rejected():
    rw = "Pay $1,284.50 by November 15, 2026 at 12 Elm Road. 1.5% penalty."
    r = check_rewrite(ORIG, rw, KEEP)
    assert not r.ok and r.missing_phrases == ["Homeowners only"]


def test_invented_figure_is_rejected():
    rw = ORIG + " Call 555-0100."
    assert not check_rewrite(ORIG, rw, KEEP).ok
