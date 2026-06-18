from typesafe_i18n.runtime import I18n

i18n = I18n("translations", "en")

print(i18n.t("hello", name="World"))
print(i18n.t("items", count=1))
print(i18n.t("items", count=5))
print(i18n.t("age_info", name="Alice", age=30))
print(i18n.t("simple"))

i18n.set_locale("zh")
print(i18n.t("hello", name="世界"))
print(i18n.t("items", count=3))
