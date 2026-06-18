from typing import Literal, overload, NewType

LocalizedString = NewType("LocalizedString", str)

@overload
def t(key: Literal["age_info"], *, age: int | float, name: str) -> LocalizedString: ...

@overload
def t(key: Literal["greeting"], *, time: str) -> LocalizedString: ...

@overload
def t(key: Literal["hello"], *, name: str) -> LocalizedString: ...

@overload
def t(key: Literal["items"], *, count: int | float) -> LocalizedString: ...

@overload
def t(key: Literal["messages"], *, count: int | float) -> LocalizedString: ...

@overload
def t(key: Literal["simple"]) -> LocalizedString: ...

@overload
def t(key: Literal["welcome"], *, name: str) -> LocalizedString: ...

@overload
def t(key: str, **kwargs: object) -> str: ...
