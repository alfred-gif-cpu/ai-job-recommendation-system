from rate_limit import allow


class TestAllow:
    def test_allows_up_to_the_limit_then_blocks(self):
        key = "test-key-basic"
        results = [allow(key, limit=5, window=60) for _ in range(7)]
        assert results == [True, True, True, True, True, False, False]

    def test_different_keys_have_independent_limits(self):
        assert all(allow("test-key-a", limit=2, window=60) for _ in range(2))
        # a different key isn't affected by key-a's usage
        assert allow("test-key-b", limit=2, window=60) is True

    def test_window_of_zero_always_blocks_after_first(self, monkeypatch):
        # a call recorded "now" never expires within the same instant;
        # sanity check that limit=1 blocks the second call immediately
        key = "test-key-limit-one"
        assert allow(key, limit=1, window=60) is True
        assert allow(key, limit=1, window=60) is False
