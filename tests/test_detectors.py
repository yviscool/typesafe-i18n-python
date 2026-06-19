from typesafe_i18n.detectors import (
    detect_locale,
    init_accept_language_header_detector,
    init_cookie_detector,
    init_env_detector,
    init_query_string_detector,
    navigator_detector,
)


class TestDetectLocale:
    def test_no_detectors(self):
        assert detect_locale("de", ["de", "de-AT", "de-CH"]) == "de"

    def test_empty_detector(self):
        assert detect_locale("de", ["de", "de-AT", "de-CH"], lambda: []) == "de"

    def test_detect_exact_match(self):
        assert detect_locale("de", ["de", "de-AT", "de-CH"], lambda: ["de-AT"]) == "de-AT"

    def test_detect_language_fallback(self):
        assert detect_locale("de", ["de"], lambda: ["de-AT"]) == "de"

    def test_case_insensitive(self):
        assert detect_locale("de", ["de"], lambda: ["EN", "DE"]) == "de"

    def test_case_insensitive_preserves_original(self):
        assert detect_locale("it", ["de", "IT", "it"], lambda: ["en-US", "it"]) == "IT"

    def test_language_split_match(self):
        assert detect_locale("it", ["en", "en-GB", "it"], lambda: ["en-US", "it"]) == "en"

    def test_no_match_returns_fallback(self):
        assert detect_locale("de", ["de", "de-AT", "de-CH"], lambda: ["fr", "en"]) == "de"

    def test_not_first_locale(self):
        assert detect_locale("de", ["de", "de-AT", "de-CH"], lambda: ["fr", "en", "de-CH"]) == "de-CH"

    def test_second_detector(self):
        assert detect_locale("de", ["de"], lambda: ["fr", "en", "de-CH"], lambda: ["de"]) == "de"

    def test_third_detector(self):
        assert detect_locale("de", ["de"], lambda: [], lambda: ["ru"], lambda: ["en-US", "de"]) == "de"


class TestAcceptLanguageHeaderDetector:
    def test_empty(self):
        detector = init_accept_language_header_detector("")
        assert detector() == []

    def test_single_value(self):
        detector = init_accept_language_header_detector("de-CH")
        assert detector() == ["de-CH"]

    def test_multiple_values_with_weight(self):
        detector = init_accept_language_header_detector("de, de-AT;q=0.9, en;q=0.8")
        assert detector() == ["de", "de-AT", "en"]

    def test_multiple_values_without_weight(self):
        detector = init_accept_language_header_detector("en-US,fr-CA")
        assert detector() == ["en-US", "fr-CA"]

    def test_sorted_by_weight(self):
        detector = init_accept_language_header_detector("en;q=0.5, fr;q=0.9, de;q=0.8")
        assert detector() == ["fr", "de", "en"]

    def test_wildcard_filtered(self):
        detector = init_accept_language_header_detector("fr-CH, fr;q=0.9, en;q=0.8, de;q=0.7, *;q=0.5")
        assert detector() == ["fr-CH", "fr", "en", "de"]

    def test_only_wildcard(self):
        detector = init_accept_language_header_detector("*")
        assert detector() == []

    def test_complex_weights(self):
        detector = init_accept_language_header_detector("en-US;q=1.0, en;q=0.8, fr;q=0.7, de;q=0.5")
        assert detector() == ["en-US", "en", "fr", "de"]


class TestCookieDetector:
    def test_empty(self):
        detector = init_cookie_detector("")
        assert detector() == []

    def test_single_value(self):
        detector = init_cookie_detector("lang=de-AT")
        assert detector() == ["de-AT"]

    def test_custom_key(self):
        detector = init_cookie_detector("locale=en-US", key="locale")
        assert detector() == ["en-US"]

    def test_wrong_key(self):
        detector = init_cookie_detector("locale=fr")
        assert detector() == []

    def test_multiple_cookies(self):
        detector = init_cookie_detector("_ga=weTrackYouEverywhere;lang=it")
        assert detector() == ["it"]

    def test_custom_key_with_multiple_cookies(self):
        detector = init_cookie_detector("cookie=test123;user-lang=es", key="user-lang")
        assert detector() == ["es"]

    def test_no_matching_cookie(self):
        detector = init_cookie_detector("cookie1=some-value;cookie2=another-value")
        assert detector() == []


class TestEnvDetector:
    def test_missing_env(self, monkeypatch):
        monkeypatch.delenv("LANG", raising=False)
        detector = init_env_detector("LANG")
        assert detector() == []

    def test_set_env(self, monkeypatch):
        monkeypatch.setenv("LANG", "en_US.UTF-8")
        detector = init_env_detector("LANG")
        assert detector() == ["en_US.UTF-8"]

    def test_custom_key(self, monkeypatch):
        monkeypatch.setenv("MY_LOCALE", "fr-FR")
        detector = init_env_detector("MY_LOCALE")
        assert detector() == ["fr-FR"]


class TestQueryStringDetector:
    def test_empty(self):
        detector = init_query_string_detector("")
        assert detector() == []

    def test_single_value(self):
        detector = init_query_string_detector("?lang=de-AT")
        assert detector() == ["de-AT"]

    def test_custom_key(self):
        detector = init_query_string_detector("?locale=en-US", key="locale")
        assert detector() == ["en-US"]

    def test_wrong_key(self):
        detector = init_query_string_detector("?locale=fr")
        assert detector() == []

    def test_multiple_params(self):
        detector = init_query_string_detector("?id=123&lang=it")
        assert detector() == ["it"]

    def test_custom_key_multiple_params(self):
        detector = init_query_string_detector("?param=test123&user-lang=es", key="user-lang")
        assert detector() == ["es"]

    def test_no_lang_param(self):
        detector = init_query_string_detector("?param-1=some-value&param2=another-value")
        assert detector() == []

    def test_value_with_equals(self):
        detector = init_query_string_detector("?lang=en-US&other=val")
        assert detector() == ["en-US"]


class TestNavigatorDetector:
    def test_empty(self):
        detector = navigator_detector([])
        assert detector() == []

    def test_single_value(self):
        detector = navigator_detector(["de-AT"])
        assert detector() == ["de-AT"]

    def test_multiple_values(self):
        detector = navigator_detector(["de", "en-US", "en", "it"])
        assert detector() == ["de", "en-US", "en", "it"]

    def test_returns_copy(self):
        langs = ["en", "fr"]
        detector = navigator_detector(langs)
        result = detector()
        result.append("de")
        assert detector() == ["en", "fr"]
