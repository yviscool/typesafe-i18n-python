# typesafe-i18n-python

Type-safe internationalization for Python. Get compile-time errors when you use wrong keys, wrong arguments, or wrong types.

## Features

- Type-safe translations with compile-time checking
- YAML translation files
- Automatic type stub generation
- CLDR plural rules (32+ languages)
- Formatter chains
- Switch-case syntax
- Custom formatters
- Namespace support
- Missing key detection
- Watch mode
- Framework adapters (Django, Flask, FastAPI, Jinja2)

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
    'typesafe_i18n.adapters.django.DjangoI18nMiddleware',
    ...
]

# views.py
from typesafe_i18n.adapters.django import t

def my_view(request):
    return HttpResponse(t(request, "hello", name="World"))
```

### Flask

```python
from flask import Flask
from typesafe_i18n.adapters.flask import FlaskI18n

app = Flask(__name__)
i18n = FlaskI18n(app, translations_dir="translations")

@app.route("/")
def index():
    return i18n.t("hello", name="World")
```

### FastAPI

```python
from fastapi import FastAPI, Depends
from typesafe_i18n.adapters.fastapi import get_i18n, configure

app = FastAPI()
configure(translations_dir="translations")

@app.get("/")
async def index(i18n = Depends(get_i18n)):
    return {"message": i18n.t("hello", name="World")}
```

### Jinja2

```python
from jinja2 import Environment
from typesafe_i18n.adapters.jinja2 import I18nExtension
from typesafe_i18n.runtime import I18n

env = Environment(extensions=[I18nExtension])
env.globals["i18n"] = I18n("translations", "en")

# In templates:
# {{ t("hello", name="World") }}
# {{ "hello" | t(name="World") }}
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

## Namespaces

Organize translations in subdirectories:

```
translations/
  en.yaml
  en/
    settings/
      en.yaml
    profile/
      en.yaml
```

Access with dot notation:
```python
i18n.t("settings.title")
i18n.t("profile.name")
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
