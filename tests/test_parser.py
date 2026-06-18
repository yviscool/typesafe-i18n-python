from typesafe_i18n.parser import (
    ArgPart,
    PluralPart,
    TextPart,
    extract_custom_types,
    extract_params,
    has_plural,
    parse_translation,
    validate_template,
)


class TestParseTranslation:
    def test_simple_text(self):
        parts = parse_translation("Hello World")
        assert len(parts) == 1
        assert isinstance(parts[0], TextPart)
        assert parts[0].text == "Hello World"

    def test_simple_arg(self):
        parts = parse_translation("Hello {name}!")
        assert len(parts) == 3
        assert parts[1].name == "name"
        assert parts[1].type is None
        assert parts[1].optional is False

    def test_typed_arg(self):
        parts = parse_translation("{count:number} items")
        assert parts[0].type == "number"

    def test_string_type(self):
        parts = parse_translation("{name:string}")
        assert parts[0].type == "string"

    def test_boolean_type(self):
        parts = parse_translation("{enabled:boolean}")
        assert parts[0].type == "boolean"

    def test_optional_arg(self):
        parts = parse_translation("{name?}")
        assert parts[0].optional is True

    def test_optional_typed_arg(self):
        parts = parse_translation("{name?:string}")
        assert parts[0].name == "name"
        assert parts[0].type == "string"
        assert parts[0].optional is True

    def test_positional_arg(self):
        parts = parse_translation("{0} items")
        assert parts[0].name == "0"

    def test_single_formatter(self):
        parts = parse_translation("{name|upper}")
        assert parts[0].name == "name"
        assert parts[0].formatters == ("upper",)

    def test_multiple_formatters(self):
        parts = parse_translation("{name|trim|upper}")
        assert parts[0].formatters == ("trim", "upper")

    def test_typed_with_formatter(self):
        parts = parse_translation("{count:number|currency}")
        assert parts[0].name == "count"
        assert parts[0].type == "number"
        assert parts[0].formatters == ("currency",)

    def test_switch_case(self):
        parts = parse_translation('{gender|{male:他,female:她,*:他们}}')
        assert parts[0].name == "gender"
        assert parts[0].switch is not None
        assert parts[0].switch.cases == {"male": "他", "female": "她"}
        assert parts[0].switch.default == "他们"

    def test_switch_case_no_default(self):
        parts = parse_translation('{status|{active:OK,inactive:Off}}')
        assert parts[0].switch.cases == {"active": "OK", "inactive": "Off"}
        assert parts[0].switch.default == ""

    def test_formatter_then_switch(self):
        parts = parse_translation('{gender|lower|{male:他,female:她}}')
        assert parts[0].formatters == ("lower",)
        assert parts[0].switch is not None
        assert parts[0].switch.cases == {"male": "他", "female": "她"}

    def test_plural_simple(self):
        parts = parse_translation("{count} {{item|items}}")
        assert len(parts) == 3
        assert isinstance(parts[2], PluralPart)
        assert parts[2].key == "count"
        assert parts[2].forms == ("item", "items")

    def test_plural_three_forms(self):
        parts = parse_translation("{{zero|one|other}}")
        assert parts[0].forms == ("zero", "one", "other")

    def test_plural_six_forms(self):
        parts = parse_translation("{{zero|one|two|few|many|other}}")
        assert parts[0].forms == ("zero", "one", "two", "few", "many", "other")

    def test_multiple_args(self):
        parts = parse_translation("{name} is {age} years old")
        args = [p for p in parts if isinstance(p, ArgPart)]
        assert len(args) == 2

    def test_complex_template(self):
        template = "{name:string|upper} has {count:number} new {{message|messages}}"
        parts = parse_translation(template)
        args = [p for p in parts if isinstance(p, ArgPart)]
        plurals = [p for p in parts if isinstance(p, PluralPart)]
        assert len(args) == 2
        assert len(plurals) == 1
        assert args[0].name == "name"
        assert args[0].type == "string"
        assert args[0].formatters == ("upper",)

    def test_empty_string(self):
        parts = parse_translation("")
        assert parts == []

    def test_adjacent_args(self):
        parts = parse_translation("{a}{b}")
        assert len(parts) == 2

    def test_text_before_and_after_plural(self):
        parts = parse_translation("I have {{apple|apples}}")
        assert parts[0].text == "I have "


class TestExtractParams:
    def test_no_params(self):
        assert extract_params("Hello World") == {}

    def test_single_param(self):
        assert extract_params("Hello {name}!") == {"name": None}

    def test_typed_param(self):
        assert extract_params("{count:number} items") == {"count": "number"}

    def test_multiple_params(self):
        params = extract_params("{name} is {age} years old")
        assert params == {"name": None, "age": None}

    def test_param_with_formatter(self):
        params = extract_params("{name|upper}")
        assert params == {"name": None}


class TestHasPlural:
    def test_no_plural(self):
        assert has_plural("Hello {name}") is False

    def test_has_plural(self):
        assert has_plural("{count} {{item|items}}") is True


class TestExtractCustomTypes:
    def test_no_custom_types(self):
        assert extract_custom_types("{name:string}") == set()

    def test_custom_type(self):
        assert extract_custom_types("{0:Sum}") == {"Sum"}

    def test_multiple_custom_types(self):
        result = extract_custom_types("{0:Sum} and {1:Product}")
        assert result == {"Sum", "Product"}


class TestValidateTemplate:
    def test_valid_template(self):
        assert validate_template("Hello {name}!", "test") == []

    def test_unmatched_open_brace(self):
        errors = validate_template("Hello {name", "test")
        assert len(errors) == 1
        assert "unmatched" in errors[0].lower()

    def test_unmatched_close_brace(self):
        errors = validate_template("Hello name}!", "test")
        assert len(errors) == 1
        assert "unmatched" in errors[0].lower()

    def test_nested_braces_valid(self):
        assert validate_template("{gender|{male:He,female:She}}", "test") == []
