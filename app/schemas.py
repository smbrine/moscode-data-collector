import re

from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
)


class Form(BaseModel):
    pass


class FormSend(Form):
    name: str = ""
    phone: int | None = None
    email: str | None = None
    message: str = ""

    @field_validator("phone", mode="before")
    def validate_phone(cls, v):  # pylint: disable=E0213
        if not v:
            return None
        phone = str(v)
        testing_phone = re.sub(r"[() +-]", "", phone)

        beginning_regex = re.compile(r"^[78]\d*$")

        if len(testing_phone) != 11:
            return None

        return phone if bool(beginning_regex.match(testing_phone)) else None

    @field_validator("email", mode="before")
    def validate_email(cls, v):  # pylint: disable=E0213
        email_mask = r"^(?=[a-zA-Z0-9._+-]{2,}@)([a-zA-Z0-9_+-]+(?:\.[a-zA-Z0-9_+-]+)*)@(?=[a-zA-Z0-9.-]{2,}\.)([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*)\.([a-zA-Z]{2,})$"  # pylint: disable=C0301
        print(v)
        if not v:
            return None
        if re.match(email_mask, v):
            print(v)
            return v
        return None

    @field_validator("name")
    def validate_name(cls, v):  # pylint: disable=E0213
        if v:
            if 2 > len(v) > 50:
                raise ValueError("Incorrect client name")
        return v

    @model_validator(mode="before")
    def check_phone_or_email(cls, values):  # pylint: disable=E0213
        phone, email = values.get("phone"), values.get("email")
        if not (phone or email):
            raise ValueError("Either phone or email must be provided")
        return values
