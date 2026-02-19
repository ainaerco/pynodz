from nodeUtils import (
    normalizeName,
    incrementName,
    listRemove,
    mergeDicts,
    sample,
)


class TestNormalizeName:
    def test_empty_string(self):
        assert normalizeName("") == ""

    def test_no_separators(self):
        assert normalizeName("foo") == "foo"

    def test_single_underscore_and_upper(self):
        assert normalizeName("a_b") == "aB"

    def test_multiple_separators_collapsed(self):
        assert normalizeName("a   b") == "aB"
        assert normalizeName("a---b") == "aB"
        assert normalizeName("a___b") == "aB"

    def test_trailing_underscores_stripped(self):
        assert normalizeName("foo__") == "foo"

    def test_leading_underscore_uppercases_next(self):
        # "_a_b_" -> rstrip -> "_a_b"; after _ the next letter is uppercased and consumed
        assert normalizeName("_a_b_") == "AB"

    def test_mixed_separators(self):
        assert normalizeName("foo bar-baz") == "fooBarBaz"


class TestIncrementName:
    def test_first_use(self):
        dic = {}
        assert incrementName("foo", dic) == "foo0"
        assert dic == {"foo": 0}

    def test_second_use(self):
        dic = {"foo": 0}
        assert incrementName("foo", dic) == "foo1"
        assert dic == {"foo": 1}

    def test_name_with_existing_number_suffix(self):
        dic = {}
        assert incrementName("bar42", dic) == "bar0"
        assert dic == {"bar": 0}


class TestListRemove:
    def test_remove_present_item(self):
        lst = [1, 2, 3]
        listRemove(lst, 2)
        assert lst == [1, 3]

    def test_remove_first(self):
        lst = [1, 2, 3]
        listRemove(lst, 1)
        assert lst == [2, 3]

    def test_remove_last(self):
        lst = [1, 2, 3]
        listRemove(lst, 3)
        assert lst == [1, 2]

    def test_item_missing_idempotent(self):
        lst = [1, 2, 3]
        listRemove(lst, 99)
        assert lst == [1, 2, 3]

    def test_remove_only_occurrence(self):
        lst = ["a", "b", "a"]
        listRemove(lst, "a")
        assert lst == ["b", "a"]


class TestMergeDicts:
    def test_shallow_merge(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 20, "c": 3}
        assert dict(mergeDicts(d1, d2)) == {"a": 1, "b": 20, "c": 3}

    def test_second_wins_on_conflict(self):
        d1 = {"x": 1}
        d2 = {"x": 2}
        assert dict(mergeDicts(d1, d2)) == {"x": 2}

    def test_nested_merge(self):
        d1 = {"a": {"b": 1, "c": 2}}
        d2 = {"a": {"c": 20, "d": 4}}
        assert dict(mergeDicts(d1, d2)) == {"a": {"b": 1, "c": 20, "d": 4}}

    def test_empty_dicts(self):
        assert dict(mergeDicts({}, {})) == {}


class TestSample:
    def test_sample_k_equals_n(self):
        data = [1, 2, 3, 4, 5]
        result = sample(iter(data), 5)
        assert len(result) == 5
        assert set(result) == set(data)

    def test_sample_k_less_than_n(self):
        data = list(range(20))
        result = sample(iter(data), 3)
        assert len(result) == 3
        assert all(x in data for x in result)

    def test_sample_returns_k_elements(self):
        data = list(range(100))
        result = sample(iter(data), 10)
        assert len(result) == 10
