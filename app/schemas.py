from pydantic import BaseModel, field_validator


class Form(BaseModel):
    pass


class FormSend(Form):
    name: str = ""
    phone: int
    message: str = ""

    @field_validator("phone")
    def validate_phone(cls, v):  # pylint: disable=E0213
        phone = str(v)
        if not phone.startswith("7") or len(phone) != 11:
            if not any(
                [
                    phone.startswith("79"),
                    phone.startswith("74"),
                    phone.startswith("78"),
                ]
            ):
                raise ValueError("Incorrect phone number")
        return v

    @field_validator("name")
    def validate_name(cls, v):  # pylint: disable=E0213
        if v:
            if len(v) < 2:
                raise ValueError("Incorrect client name")
            return v
        return v
