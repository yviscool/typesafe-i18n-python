# typesafe-i18n-python

Type-safe internationalization for Python. Get compile-time errors when you use wrong keys, wrong arguments, or wrong types.

## Features

- Type-safe translations with compile-time checking
- YAML, JSON, TOML translation files
- Automatic type stub generation
- CLDR plural rules (32+ languages)
- Formatter chains
- Switch-case syntax
- Custom formatters
- Namespace support with fallback
- Fallback locale
- Async loading
- Locale detection (Accept-Language, cookie, env, query string)
- Missing key detection
- Watch mode
- Framework adapters (Django, Flask, FastAPI)
- Config file (`.typesafe-i18n.json`)

## Installation

```bash
pip install typesafe-i18n
```

## Quick Start

### 1. Create translation files

```yaml
# translations/en.yaml
hello: "Hello {name:string}!"
items: "{count:number} {{item|items}}"
welcome: "Welcome {name:string}, you have {count:number} messages"
```

### 2. Generate type stubs

```bash
typesafe-i18n generate
```

### 3. Use in your code

```python
from typesafe_i18n.runtime import I18n

i18n = I18n("translations", "en")
print(i18n.t("hello", name="World"))     # "Hello World!"
print(i18n.t("items", count=1))          # "1 item"
print(i18n.t("items", count=5))          # "5 items"
```

## Translation Syntax

### Simple text
```yaml
greeting: "Hello World"
```

### Named parameters
```yaml
hello: "Hello {name}!"
```

### Typed parameters
```yaml
count: "{count:number} items"
info: "{name:string} is {age:number} years old"
```

### Optional parameters
```yaml
greeting: "Hello {name?}!"
```

### Plural forms
```yaml
items: "{count} {{item|items}}"
messages: "{count} new {{message|messages}}"
```

Supports CLDR plural categories: `{{zero|one|two|few|many|other}}`

### Formatters
```yaml
upper: "Hello {name:string|upper}!"
trimmed: "{name:string|trim|upper}"
```

### Formatter chains
```yaml
formatted: "{name:string|trim|lower|upper}"
```

### Switch-case
```yaml
gender: "{gender|{male:He,female:She,*:They}} replied"
```

### Combined
```yaml
status: "{status:string|lower|{active:OK,inactive:Off}}"
```

## Namespaces

Organize translations into separate files per locale:

```
translations/
  en.yaml              # main translations
  en/
    settings.yaml      # "settings" namespace
    account.yaml       # "account" namespace
  zh.yaml
  zh/
    settings.yaml
    account.yaml
```

Load and use namespaces with the `:` prefix:

```python
from typesafe_i18n.runtime import I18n

i18n = I18n("translations", "en")
i18n.load_namespace("settings")
i18n.load_namespace("account")

i18n.t("settings:title")           # "Settings"
i18n.t("account:greeting", name="Alice")  # "Welcome Alice!"
i18n.t("hello")                    # still works for main translations
```

### Async namespace loading

```python
await i18n.load_namespace_async("settings")
```

### Namespace fallback

When a namespace key is not found in the current locale, it automatically falls back to the fallback locale's namespace:

```python
i18n = I18n("translations", "zh")
i18n.set_fallback_locale("en")

# If zh/account.yaml doesn't exist but en/account.yaml does:
i18n.t("account:greeting", name="Alice")  # "Welcome Alice!" (from en)
```

## Fallback Locale

Set a fallback locale for missing translations:

```python
i18n = I18n("translations", "zh")
i18n.set_fallback_locale("en")

i18n.t("hello", name="World")    # "你好 World!" (from zh)
i18n.t("items", count=5)         # "5 items" (from en, missing in zh)
i18n.t("nonexistent")            # "nonexistent" (missing in both)
```

Fallback also works with nested keys and namespaces.

## Async Loading

Load translations asynchronously (useful for web frameworks):

```python
from typesafe_i18n.async_loader import load_locale_async, load_namespace_async

data = await load_locale_async("translations", "en")
data = await load_namespace_async("translations", "en", "settings")
```

## Config File

Create `.typesafe-i18n.json` in your project root to configure defaults:

```json
{
  "baseLocale": "zh",
  "translationsPath": "./i18n",
  "outputPath": "./src/generated"
}
```

All CLI commands read from this config. Explicit CLI arguments take precedence:

```bash
# Uses config values
typesafe-i18n generate

# CLI args override config
typesafe-i18n generate -d other_translations -l en
```

## Locale Detection

Detect the user's locale from various sources:

```python
from typesafe_i18n.detectors import (
    detect_locale,
    init_accept_language_header_detector,
    init_cookie_detector,
    init_env_detector,
    init_query_string_detector,
    navigator_detector,
)

# From Accept-Language header
detector = init_accept_language_header_detector("zh-CN,en;q=0.9")
locales = detector()  # ["zh-CN", "en"]

# From cookie
detector = init_cookie_detector("lang=zh; theme=dark")
locales = detector()  # ["zh"]

# From environment variable
detector = init_env_detector("LANG")
locales = detector()

# From query string
detector = init_query_string_detector("?lang=zh&page=1")
locales = detector()  # ["zh"]

# From browser navigator.languages
detector = navigator_detector(["zh-CN", "en-US", "en"])
locales = detector()

# Auto-detect with fallback
locale = detect_locale("en", ["en", "zh", "fr"], detector)
```

## Built-in Formatters

```python
from typesafe_i18n.formatters import (
    date, time, number, currency,
    replace, identity, ignore,
    uppercase, lowercase,
)

i18n.set_formatters({
    "upper": uppercase,
    "lower": lowercase,
    "date": date("en", {"year": "numeric", "month": "long", "day": "numeric"}),
    "time": time("en", {"hour": "2-digit", "minute": "2-digit"}),
    "num": number("en", {"maximumFractionDigits": 2}),
    "usd": currency("en", "USD"),
    "trim": replace(r"^\s+|\s+$", ""),
})
```

## CLI Commands

### Generate type stubs
```bash
typesafe-i18n generate
typesafe-i18n generate -d translations -o _generated -l en
```

### Watch mode
```bash
typesafe-i18n generate --watch
```

### Validate translations
```bash
typesafe-i18n validate
typesafe-i18n validate -d translations -l en
```

### Extract keys from source
```bash
typesafe-i18n extract src/
typesafe-i18n extract src/ -d translations -l en
```

### Export to JSON
```bash
typesafe-i18n export
typesafe-i18n export -o translations.json -l en
```

### Import from JSON
```bash
typesafe-i18n import translations.json
```

## Framework Adapters

### Django

```python
# settings.py
MIDDLEWARE = [
    'typesafe_i18n.contrib.django.I18nMiddleware',
    ...
]

I18N_TRANSLATIONS_DIR = "translations"
I18N_DEFAULT_LOCALE = "en"

# views.py
from typesafe_i18n.contrib.django import t

def my_view(request):
    return HttpResponse(t(request, "hello", name="World"))
```

### Flask

```python
from flask import Flask
from typesafe_i18n.contrib.flask import TypesafeI18n

app = Flask(__name__)
app.config["I18N_TRANSLATIONS_DIR"] = "translations"
app.config["I18N_DEFAULT_LOCALE"] = "en"

i18n = TypesafeI18n(app)

@app.route("/")
def index():
    from typesafe_i18n.contrib.flask import t
    return t("hello", name="World")
```

### FastAPI

```python
from fastapi import FastAPI, Depends, Request
from typesafe_i18n.contrib.fastapi import configure, get_i18n

app = FastAPI()
configure(translations_dir="translations", default_locale="en")

@app.get("/")
async def index(request: Request, i18n = Depends(get_i18n)):
    return {"message": i18n.t("hello", name="World")}
```

## Custom Formatters

```python
from typesafe_i18n.runtime import I18n

i18n = I18n("translations", "en")
i18n.set_formatters({
    "upper": lambda v: v.upper(),
    "lower": lambda v: v.lower(),
    "trim": lambda v: v.strip(),
    "currency": lambda v: f"${v:,.2f}",
})
```

## Type Safety

The generated type stubs provide compile-time checking:

```python
# _generated/types.pyi
from typing import Literal, overload, NewType

LocalizedString = NewType("LocalizedString", str)

@overload
def t(key: Literal["hello"], *, name: str) -> LocalizedString: ...

@overload
def t(key: Literal["items"], *, count: int | float) -> LocalizedString: ...

@overload
def t(key: str, **kwargs: object) -> str: ...
```

With mypy/pyright:
```python
t("hello", name="World")     # OK
t("hello")                   # Error: missing 'name'
t("hello", name=42)          # Error: wrong type
t("nonexistent")             # Error: key not in Literal
```

## Plural Rules

Supports CLDR plural rules for 32+ languages:

- English, Chinese, Arabic, Polish, Russian, Czech
- French, Spanish, German, Italian, Portuguese
- Japanese, Korean, Vietnamese, Thai, Turkish
- Dutch, Swedish, Danish, Norwegian, Finnish
- Hungarian, Greek, Hebrew, Hindi, Indonesian, Malay
- Lithuanian, Latvian, Romanian, Welsh, Breton

## License

MIT
